"""Priority-based async task queue backed by a QThread worker.

This module provides a generic priority-based task queue system that runs in a
separate thread to prevent blocking the Qt main event loop. It includes
context tracking and cancellation support for handling state transitions such
as user navigation between different items.
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Any, Callable

from qtpy.QtCore import Qt, QThread, Signal, Slot

log = logging.getLogger(__name__)


@dataclass
@total_ordering
class AsyncTask:
    """Represents a task to be executed by the async task queue.

    This class holds all the information needed to execute an asynchronous
    operation, including the work function, callback, priority, and context
    tracking for cancellation support.

    Attributes:
        name: Descriptive name for the task (e.g., "fetch_activity_data").
        function: Callable that performs the work.
        callback: Function to call with the result when task completes.
        priority: Priority level (lower numbers = higher priority).
            0 = Critical (UI blocking operations)
            1 = High (User-initiated operations)
            5 = Normal (Background fetches)
            10 = Low (Prefetching)
        context_id: Identifier for the context this task belongs to.
            When context changes, tasks with old context_id can be
            cancelled.
        cancellable: If True, task can be cancelled when context changes.

    Example:
        task = AsyncTask(
            name="fetch_activities",
            function=lambda: fetch_data(context),
            callback=on_data_ready,
            priority=1,
            context_id="project:item_id",
            cancellable=True
        )
    """

    name: str
    function: Callable[[], Any]
    callback: Callable[[Any], None]
    priority: int = 5
    context_id: str = ""
    cancellable: bool = True

    # Internal state
    _counter: int = field(default=0, init=False, compare=True)
    _cancelled: bool = field(default=False, init=False, repr=False)

    def cancel(self) -> None:
        """Mark this task as cancelled.

        Only affects the task if cancellable is True.
        """
        if self.cancellable:
            self._cancelled = True

    def is_cancelled(self) -> bool:
        """Check if this task has been cancelled.

        Returns:
            True if the task has been cancelled, False otherwise.
        """
        return self._cancelled

    def __lt__(self, other: AsyncTask) -> bool:
        """Compare tasks by priority, then by counter for FIFO ordering.

        Args:
            other: Another AsyncTask to compare with.

        Returns:
            True if this task should be processed before the other task.
        """
        if self.priority != other.priority:
            return self.priority < other.priority
        return self._counter < other._counter

    def __eq__(self, other: object) -> bool:
        """Check equality based on priority and counter.

        Args:
            other: Object to compare with.

        Returns:
            True if tasks have equal priority and counter.
        """
        if not isinstance(other, AsyncTask):
            return NotImplemented
        return (self.priority, self._counter) == (
            other.priority,
            other._counter,
        )


class AsyncTaskQueue(QThread):
    """Worker thread that processes async tasks from a priority queue.

    This worker runs in a separate thread and processes tasks from a
    priority queue. It supports pausing, resuming, context switching,
    and graceful shutdown. Tasks are processed cooperatively, allowing
    cancellation checks between task executions.

    Signals:
        task_completed: Emitted when a task finishes (task_name, result).
        task_failed: Emitted when a task raises exception (task_name, err).
        task_cancelled: Emitted when task is cancelled (task_name, ctx_id).
        queue_empty: Emitted when all tasks are processed.

    Example:
        queue = AsyncTaskQueue()
        queue.task_completed.connect(handle_completion)
        queue.start()

        task = AsyncTask(...)
        queue.enqueue(task)

        # Later...
        queue.stop()
    """

    # Qt Signals
    task_completed = Signal(str, object)  # (task_name, result)
    task_failed = Signal(str, str)  # (task_name, error_message)
    task_cancelled = Signal(str, str)  # (task_name, context_id)
    queue_empty = Signal()
    # No-arg ping signal: tells the main thread to drain _callback_queue.
    # Never passes Python objects through Qt's cross-thread signal system.
    invoke_callback = Signal()

    def __init__(self, parent: Any = None) -> None:
        """Initialize the async task queue.

        Args:
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()
        # Thread-safe Python queue for ferrying (callback, result) pairs.
        # Using Python's own ref-counting rather than Qt's marshaling avoids
        # PySide6 issues with Python-callable arguments in QueuedConnection.
        self._callback_queue: queue.SimpleQueue = queue.SimpleQueue()
        self._running: bool = False
        self._paused: threading.Event = threading.Event()
        self._paused.set()  # Start unpaused
        self._task_counter: int = 0
        self._counter_lock: threading.Lock = threading.Lock()
        self._current_context: str = ""
        self._context_lock: threading.Lock = threading.Lock()

        # Connect the no-arg ping to the drain slot on the main thread.
        self.invoke_callback.connect(
            self._drain_callback_queue,
            Qt.QueuedConnection,
        )

    @Slot()
    def _drain_callback_queue(self) -> None:
        """Drain all pending (callback, result) pairs on the main thread.

        Called via a QueuedConnection so it always runs on the Qt main
        thread regardless of which thread emitted invoke_callback.
        """
        while True:
            try:
                callback, result = self._callback_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(result)
            except Exception as e:
                log.exception("Callback execution failed: %s", e)

    def run(self) -> None:
        """Main worker loop - runs in separate thread.

        This method runs in the worker thread context and continuously
        processes tasks from the queue until stopped. It checks the
        pause state before each task and handles queue.Empty exceptions
        gracefully.
        """
        self._running = True
        log.debug("Task queue worker started")

        while self._running:
            # Wait if paused
            self._paused.wait()

            try:
                # Get task with timeout to check _running periodically
                priority, task = self._task_queue.get(timeout=0.5)

                # Process the task
                self._process_task(task)

                # Mark task as done
                self._task_queue.task_done()

                # Check if queue is empty
                if self._task_queue.empty():
                    self.queue_empty.emit()

            except queue.Empty:
                # Timeout is expected - allows checking _running flag
                continue
            except Exception as e:
                log.exception("Unexpected error in worker loop: %s", e)

        log.debug("Task queue worker stopped")

    def _invoke_callback_safely(
        self, callback: Callable, result: Any, task_name: str
    ) -> None:
        """Invoke callback safely with unified error handling.

        Pushes (callback, result) onto a Python SimpleQueue so that
        Python callables never travel through Qt's cross-thread
        signal marshaling (which is unreliable for arbitrary callables
        in PySide6).  A no-arg ping signal then wakes the main thread.

        Args:
            callback: The callback function to invoke.
            result: The result to pass to the callback.
            task_name: Name of the task (for logging).
        """
        try:
            self._callback_queue.put_nowait((callback, result))
            self.invoke_callback.emit()
        except Exception as e:
            log.exception(
                "Error invoking callback for %s: %s",
                task_name,
                e,
            )

    def _process_task(self, task: AsyncTask) -> None:
        """Execute a single task with cancellation and context checks.

        This method validates the task's context before execution and
        handles all exceptions to prevent the worker thread from
        crashing.

        Args:
            task: The task to process.
        """
        # Check if task is cancelled before processing
        if task.is_cancelled():
            log.debug("Skipping cancelled task: %s", task.name)
            self.task_cancelled.emit(task.name, task.context_id)
            return

        # Check if context is still current
        with self._context_lock:
            current = self._current_context

        if (
            task.context_id
            and current
            and task.context_id != current
            and task.cancellable
        ):
            log.debug(
                "Skipping task %s (context changed: %s -> %s)",
                task.name,
                task.context_id,
                current,
            )
            self.task_cancelled.emit(task.name, task.context_id)
            return

        # Process task normally
        log.debug(
            "Processing task: %s (context=%s)", task.name, task.context_id
        )

        try:
            result = task.function()

            # Double-check cancellation after execution
            if task.is_cancelled():
                log.debug(
                    "Task %s completed but was cancelled, discarding result",
                    task.name,
                )
                return

            if task.callback:
                self._invoke_callback_safely(task.callback, result, task.name)

            self.task_completed.emit(task.name, result)
            log.debug("Task completed successfully: %s", task.name)

        except Exception as e:
            log.exception("Task %s failed: %s", task.name, e)

            if task.callback:
                self._invoke_callback_safely(task.callback, None, task.name)

            self.task_failed.emit(task.name, str(e))

    def enqueue(self, task: AsyncTask) -> None:
        """Add a task to the queue (thread-safe).

        Assigns a monotonically increasing counter to the task to ensure
        FIFO ordering within the same priority level.

        Args:
            task: The task to enqueue.
        """
        # Assign a counter value for FIFO ordering within priority
        with self._counter_lock:
            task._counter = self._task_counter
            self._task_counter += 1

        # Add to priority queue
        self._task_queue.put((task.priority, task))
        log.debug(
            "Enqueued task: %s (priority=%d, queue_size=%d)",
            task.name,
            task.priority,
            self._task_queue.qsize(),
        )

    def pause(self) -> None:
        """Pause task processing.

        The worker will finish the current task and then wait until
        resumed. Tasks can still be enqueued while paused.
        """
        self._paused.clear()
        log.debug("Task queue paused")

    def resume(self) -> None:
        """Resume task processing.

        Tasks will begin processing again from where they were paused.
        """
        self._paused.set()
        log.debug("Task queue resumed")

    def stop(self) -> None:
        """Stop the worker thread gracefully.

        This will finish the current task and then exit the worker loop.
        Waits up to 5 seconds for the thread to finish.

        Any pending (callback, result) pairs left in ``_callback_queue``
        are discarded so that stale model callbacks from a previous test
        (or a discarded context) cannot fire after teardown.
        """
        log.debug("Stopping task queue worker")
        self._running = False
        self._paused.set()  # Unpause if paused

        # Wait for thread to finish (timeout after 5 seconds)
        if not self.wait(5000):
            log.warning("Task queue worker did not stop within timeout")

        # Discard any pending callbacks.  Any invoke_callback ping events
        # already in the Qt event queue will call _drain_callback_queue,
        # which will safely find an empty queue and return immediately.
        while True:
            try:
                self._callback_queue.get_nowait()
            except queue.Empty:
                break

    def is_paused(self) -> bool:
        """Check if the worker is currently paused.

        Returns:
            True if paused, False otherwise.
        """
        return not self._paused.is_set()

    def queue_size(self) -> int:
        """Get the current number of tasks in the queue.

        Returns:
            Number of pending tasks.
        """
        return self._task_queue.qsize()

    def set_current_context(self, context_id: str) -> None:
        """Set the current active context.

        When the context changes, tasks for different contexts may be
        cancelled or deprioritized. This method automatically cancels
        tasks belonging to the old context.

        Args:
            context_id: The new context identifier.
        """
        with self._context_lock:
            old_context = self._current_context
            self._current_context = context_id

            if old_context and old_context != context_id:
                log.debug(
                    "Context changed: %s -> %s",
                    old_context,
                    context_id,
                )
                self._cancel_context_tasks(old_context)

    def _filter_queue(
        self, predicate: Callable[[AsyncTask, str], tuple[bool, bool]]
    ) -> int:
        """Filter queue items based on predicate function.

        Drains queue, applies predicate to each task, and rebuilds queue
        with filtered items. This is a generic helper for both cancel
        and clear operations.

        Args:
            predicate: Function that takes (task, context_id) and returns
                (keep_in_queue, emit_cancelled_signal).

        Returns:
            Number of tasks affected (cancelled or removed).
        """
        affected_count = 0
        items_to_keep = []

        while True:
            try:
                priority, task = self._task_queue.get_nowait()
                keep, emit_signal = predicate(task, task.context_id)

                if keep:
                    items_to_keep.append((priority, task))
                else:
                    affected_count += 1
                    if emit_signal:
                        self.task_cancelled.emit(task.name, task.context_id)

            except queue.Empty:
                break

        # Rebuild queue with remaining items
        for item in items_to_keep:
            self._task_queue.put(item)

        return affected_count

    def _cancel_context_tasks(self, context_id: str) -> None:
        """Cancel all pending tasks for a specific context.

        Note: This only marks tasks as cancelled. They are actually
        skipped during processing in _process_task().

        Args:
            context_id: Context identifier to cancel tasks for.
        """

        def should_cancel(task: AsyncTask, ctx: str) -> tuple[bool, bool]:
            """Return (keep_in_queue, emit_signal)."""
            if task.context_id == context_id and task.cancellable:
                task.cancel()
                return (True, True)  # Keep but mark cancelled
            return (True, False)  # Keep, no signal

        cancelled_count = self._filter_queue(should_cancel)
        if cancelled_count > 0:
            log.debug(
                "Cancelled %d tasks for context: %s",
                cancelled_count,
                context_id,
            )

    def clear_context_tasks(self, context_id: str) -> int:
        """Completely remove tasks for a specific context from queue.

        More aggressive than cancel - actually removes from queue rather
        than just marking as cancelled.

        Args:
            context_id: Context identifier to clear.

        Returns:
            Number of tasks removed.
        """

        def should_remove(task: AsyncTask, ctx: str) -> tuple[bool, bool]:
            """Return (keep_in_queue, emit_signal)."""
            if task.context_id == context_id and task.cancellable:
                return (False, True)  # Remove and signal
            return (True, False)  # Keep, no signal

        removed_count = self._filter_queue(should_remove)
        if removed_count > 0:
            log.debug(
                "Removed %d tasks for context: %s",
                removed_count,
                context_id,
            )

        return removed_count


# ---------------------------------------------------------------------------
# Module-level shared singleton
# ---------------------------------------------------------------------------

_shared_queue: AsyncTaskQueue | None = None


def get_task_queue() -> AsyncTaskQueue:
    """Return the shared AsyncTaskQueue, creating and starting it on first use.

    The queue is a module-level singleton so all components (table models,
    tree models, etc.) share one worker thread.

    On first creation the queue is automatically connected to
    ``QApplication.aboutToQuit`` so it stops cleanly when the application
    exits — no manual :func:`shutdown_task_queue` call is required.

    Returns:
        The running shared :class:`AsyncTaskQueue` instance.
    """
    global _shared_queue
    if _shared_queue is None:
        from qtpy.QtWidgets import QApplication  # local import avoids circular

        _shared_queue = AsyncTaskQueue()
        _shared_queue.start()
        log.debug("Shared task queue started")

        app = QApplication.instance()
        if app is not None:
            # Guard: connect at most once to avoid accumulating
            # connections during test runs where the queue is
            # repeatedly created and destroyed.
            try:
                app.aboutToQuit.disconnect(shutdown_task_queue)
            except RuntimeError:
                pass  # was not connected yet
            app.aboutToQuit.connect(shutdown_task_queue)
        else:
            log.warning(
                "get_task_queue() called before QApplication exists; "
                "automatic shutdown will not be registered."
            )

    return _shared_queue


def shutdown_task_queue() -> None:
    """Stop and discard the shared :class:`AsyncTaskQueue`.

    Called automatically when the ``QApplication`` emits ``aboutToQuit``
    (wired by :func:`get_task_queue` on first use).  Safe to call
    manually before that if an early teardown is needed; subsequent calls
    are no-ops.  After this call :func:`get_task_queue` will create a
    fresh queue on next access.
    """
    global _shared_queue
    if _shared_queue is not None:
        _shared_queue.stop()
        _shared_queue = None
        log.debug("Shared task queue stopped")

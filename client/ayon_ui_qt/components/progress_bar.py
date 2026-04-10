from __future__ import annotations

from qtpy.QtCore import Signal  # type: ignore
from qtpy.QtWidgets import QProgressBar, QSizePolicy, QWidget

from .. import get_ayon_style
from .layouts import AYVBoxLayout


class AYProgressBar(QWidget):
    """Reusable progress widget for determinate and indeterminate work.

    Emits `progress_changed` with current and total values when progress
    is updated, and `completed` when progress reaches completion.
    """

    progress_changed = Signal(int, int)
    completed = Signal()

    def __init__(
        self,
        total: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the progress bar widget.

        Args:
            total (int, optional): The total value for the progress
                bar. Defaults to 0.
            parent (QWidget | None, optional): The parent widget. Defaults
                to None.
        """
        super().__init__(parent)
        self.setStyle(get_ayon_style())

        self._total = 0
        self._current = 0

        layout = AYVBoxLayout(self, margin=0, spacing=0)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyle(get_ayon_style())
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.progress_bar)
        self.set_total(total)

    @property
    def total(self) -> int:
        """Get the total value of the progress bar.

        Returns:
            int: The total value of the progress bar.
        """
        return self._total

    @property
    def current(self) -> int:
        """Get the current value of the progress bar.

        Returns:
            int: The current value of the progress bar.
        """
        return self._current

    def percentage(self) -> float:
        """Get the current progress as a percentage.

        Returns:
            float: The current progress as a percentage.
        """
        if self._total <= 0:
            return 0.0
        return (self._current / self._total) * 100.0

    def is_indeterminate(self) -> bool:
        """Check if the progress bar is in indeterminate mode.

        Returns:
            bool: True if the progress bar is indeterminate, False otherwise.
        """

        return self._total <= 0

    def set_total(self, total: int) -> None:
        """Set the total value of the progress bar.

        Args:
            total (int): The total value for the progress bar.
        """
        self._total = max(0, total)
        if self._total == 0:
            self.progress_bar.setRange(0, 0)
        else:
            self._current = min(self._current, self._total)
            self.progress_bar.setRange(0, self._total)
            self.progress_bar.setValue(self._current)

    def set_progress(
        self,
        value: int,
        total: int | None = None,
    ) -> None:
        """Set the current progress value, and optionally update
        total value for the progress bar.

        Args:
            value (int): The current progress value.
            total (int | None, optional): The total value for
                the progress bar. Defaults to None.
        """
        if total is not None:
            self.set_total(total)

        self._current = max(0, value)
        if not self.is_indeterminate():
            self._current = min(self._current, self._total)
            self.progress_bar.setValue(self._current)

        self.progress_changed.emit(self._current, self._total)
        if not self.is_indeterminate() and self._current >= self._total:
            self.completed.emit()

    def update_progress(self, value: int) -> None:
        """Update the current progress value.

        Args:
            value (int): The current progress value.
        """
        self.set_progress(value)

    def reset(self) -> None:
        """Reset the progress bar to its initial state."""
        self._current = 0
        if not self.is_indeterminate():
            self.progress_bar.setValue(0)

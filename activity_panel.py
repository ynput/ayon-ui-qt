"""Activity panel similar to AYON's front-end."""

from __future__ import annotations

import logging
from typing import Optional

from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.text_box import AYTextBox
from ayon_ui_qt.data_models import (
    ActivityData,
    CommentModel,
    ProjectData,
    VersionData,
)
from ayon_ui_qt.utils import (
    get_test_activity_data,
    get_test_project_data,
    get_test_version_data,
)
from qtpy.QtCore import QObject, Signal, Slot, QTimer  # type: ignore
from qtpy.QtWidgets import QWidget

from activity_stream import AYActivityStream
from detail_panel import AYDetailPanel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity panel")


class ActivityPanelSignals(QObject):
    """All signals emitted by the activity panel."""

    # Signal emitted when comment button is clicked, passes markdown content
    ui_comment_submitted = Signal(str, str)  # type: ignore
    ui_comment_edited = Signal(CommentModel)  # type: ignore
    ui_comment_deleted = Signal(CommentModel)  # type: ignore
    ui_assignee_changed = Signal(str)  # type: ignore
    ui_version_status_changed = Signal(str)  # type: ignore

    # Auto-refresh related signals
    ui_activity_refresh_requested = Signal()  # type: ignore
    ui_refresh_paused = Signal(bool)  # type: ignore


class ActivityPanel(AYContainer):
    """Activity panel widget for displaying and managing activity streams.

    This panel combines an activity stream view, detail panel for filtering,
    and a text editor for submitting comments. It provides signals for
    various user interactions like commenting, editing, and status changes.

    Attributes:
        signals: ActivityPanelSignals instance for emitting panel events.
    """

    signals = ActivityPanelSignals()

    def __init__(  # noqa: D107
        self,
        parent: Optional[QWidget] = None,
        activities: ActivityData | None = None,
        category: AYActivityStream.Categories = "all",
    ) -> None:
        self._project = ProjectData.not_set()
        self._version_data: VersionData = VersionData.not_set()
        self._activities = activities or ActivityData()
        self._category: AYActivityStream.Categories = category

        # Initialize auto-refresh attributes
        self._refresh_timer: QTimer | None = None
        self._is_refreshing: bool = False
        self._pause_refresh: bool = False
        self.log = logger  # Use the module logger

        super().__init__(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_margin=8,
            layout_spacing=8,
            parent=parent,
        )

        self._build()

        self.stream.update_stream(self._category, self._activities)
        # Set up auto-refresh by default
        self.setup_auto_refresh()

    def __del__(self) -> None:
        """Clean up resources when panel is destroyed."""
        self._cleanup_refresh_timer()

    def _build(self) -> None:
        """Build and configure the panel's UI components."""
        # add header
        self.details = AYDetailPanel(self)
        self.add_widget(self.details, stretch=0)

        # add scrolling layout displaying activities
        self.stream = AYActivityStream(self, category=self._category)
        self.add_widget(self.stream, stretch=10)

        # add comment editor
        self.editor = AYTextBox(num_lines=4, show_categories=True)
        self.add_widget(self.editor, stretch=0)

        # connect signals
        self.editor.signals.comment_submitted.connect(
            self.signals.ui_comment_submitted.emit
        )
        self.editor.signals.comment_submitted.connect(
            self.stream.on_comment_submitted
        )
        self.details.signals.version_status_changed.connect(
            self.signals.ui_version_status_changed.emit
        )
        self.stream.signals.comment_deleted.connect(
            self.signals.ui_comment_deleted.emit
        )
        self.stream.signals.comment_edited.connect(
            self.signals.ui_comment_edited.emit
        )

        # Connect detail panel refresh signal if it exists
        if hasattr(self.details, "signals") and hasattr(
            self.details.signals, "refresh_requested"
        ):
            self.details.signals.refresh_requested.connect(
                self.signals.ui_activity_refresh_requested.emit
            )

    def _check_and_refresh(self) -> None:
        """Check if activities have changed and refresh if needed.

        Compares the current activities hash with the last known hash to
        determine if a refresh is necessary. Skips refresh if already
        refreshing, paused, or the activity widget is not visible.
        """
        try:
            self._is_refreshing = True
            self.log.debug(
                "ActivityPanel: Emitting ui_activity_refresh_requested signal"
            )
            # Request activities via signal
            self.signals.ui_activity_refresh_requested.emit()

        except RuntimeError:
            self.log.exception("Error during auto-refresh")

        finally:
            self._is_refreshing = False

    def setup_auto_refresh(self, interval: int = 2000) -> None:
        """Set up automatic refresh for the activity stream.

        Args:
            interval: Refresh interval in milliseconds.
        """
        if self._refresh_timer is not None:
            return
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._check_and_refresh)
        self._refresh_timer.start(interval)

    def _cleanup_refresh_timer(self) -> None:
        """Clean up the refresh timer."""
        if self._refresh_timer is not None:
            try:
                self._refresh_timer.stop()
            except RuntimeError:
                pass
            else:
                self._refresh_timer.deleteLater()
            self._refresh_timer = None

    @Slot(bool)
    def on_ctlr_playback_state_changed(self, is_playing: bool) -> None:
        """Handle playback state changes from controller."""
        self.log.debug(
            "ActivityPanel: Playback state changed to: %s", is_playing
        )
        if is_playing:
            self._cleanup_refresh_timer()
        else:
            self.setup_auto_refresh()

    @Slot(ActivityData)
    def on_ctlr_activities_changed(self, data: ActivityData) -> None:
        """Handle activities data change event.

        Args:
            data: Dictionary containing the new activities payload.
        """
        self.stream.update_stream(self._category, data)

    @Slot(ProjectData)
    def on_ctlr_project_changed(self, data: ProjectData) -> None:
        """Handle project change event."""
        self._project = data
        self.stream.on_project_changed(data)
        self.details.on_ctlr_project_changed(data)
        self.editor.on_ctlr_project_changed(data)

    @Slot(VersionData)
    def on_ctlr_version_data_changed(self, data: VersionData) -> None:
        """Handle version data change event."""
        self._version_data = data
        self.stream.on_version_data_changed(data)
        self.details.on_ctlr_version_data_changed(data)

    @Slot(VersionData)
    def on_ctlr_version_status_changed(self, status: str) -> None:
        """Handle version status change event."""
        if not self._version_data:
            return
        self._version_data.status = status
        self.details.on_ctlr_version_status_changed(status)


#  TEST =======================================================================


if __name__ == "__main__":
    from ayon_ui_qt.tester import Style, test

    def _build() -> QWidget:
        project_data = get_test_project_data()
        version_data = get_test_version_data()
        activity_data = get_test_activity_data()

        # create ui
        w = ActivityPanel(category="all")

        # send data
        w.on_ctlr_project_changed(project_data)
        w.on_ctlr_version_data_changed(version_data)
        w.on_ctlr_activities_changed(activity_data)

        # setup signals
        w.signals.ui_comment_submitted.connect(
            lambda md, cat: print(
                f"ActivityPanel.signals.comment_submitted: [{cat}] {md!r}"
            )  # noqa: T201
        )
        w.signals.ui_version_status_changed.connect(
            lambda stat: print(
                f"ActivityPanel.signals.status_changed: {stat!r}"
            )  # noqa: T201
        )
        w.signals.ui_comment_deleted.connect(
            lambda x: print(f"comment_deleted: {x}")  # noqa: T201
        )
        w.signals.ui_comment_edited.connect(
            lambda x: print(f"comment_edited: {x}")  # noqa: T201
        )
        w.signals.ui_activity_refresh_requested.connect(
            lambda: print("ActivityPanel: refresh_requested")  # noqa: T201
        )
        w.signals.ui_refresh_paused.connect(
            lambda paused: print(f"ActivityPanel: refresh_paused={paused}")  # noqa: T201
        )

        # test signals
        w.signals.ui_version_status_changed.emit("In progress")

        return w

    test(_build, style=Style.Widget)

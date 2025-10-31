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
from qtpy.QtCore import QObject, Signal, Slot  # type: ignore
from qtpy.QtWidgets import QWidget

from activity_stream import AYActivityStream
from detail_panel import AYDetailPanel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity panel")


class ActivityPanelSignals(QObject):
    """All signals emitted by the activity panel."""

    # Signal emitted when comment button is clicked, passes markdown content
    ui_comment_submitted = Signal(str)  # type: ignore
    ui_comment_edited = Signal(CommentModel)  # type: ignore
    ui_comment_deleted = Signal(CommentModel)  # type: ignore
    ui_assignee_changed = Signal(str)  # type: ignore
    ui_status_changed = Signal(str)  # type: ignore


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
        self._activities = activities or ActivityData()
        self._category: AYActivityStream.Categories = category

        super().__init__(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_margin=8,
            layout_spacing=8,
            parent=parent,
        )

        self._build()

        self.stream.update_stream(self._category, self._activities)

    def _build(self) -> None:
        """Build and configure the panel's UI components."""
        # add header
        self.details = AYDetailPanel(self)
        self.addWidget(self.details, stretch=0)

        # add scrolling layout displaying activities
        self.stream = AYActivityStream(self, category=self._category)
        self.addWidget(self.stream, stretch=10)

        # add comment editor
        self.editor = AYTextBox(num_lines=3)
        self.addWidget(self.editor, stretch=0)

        # connect signals
        self.editor.signals.comment_submitted.connect(
            self.signals.ui_comment_submitted.emit
        )
        self.details.signals.status_changed.connect(
            self.signals.ui_status_changed.emit
        )
        self.stream.signals.comment_deleted.connect(
            self.signals.ui_comment_deleted.emit
        )
        self.stream.signals.comment_edited.connect(
            self.signals.ui_comment_edited.emit
        )

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

    @Slot(VersionData)
    def on_ctlr_version_changed(self, data: VersionData) -> None:
        """Handle project change event."""
        self._version_data = data
        self.stream.on_version_data_changed(data)
        self.details.on_ctlr_version_data_changed(data)


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
        w.on_ctlr_version_changed(version_data)
        w.on_ctlr_activities_changed(activity_data)

        # setup signals
        w.signals.ui_comment_submitted.connect(
            lambda x: print(f"ActivityPanel.signals.comment_submitted: {x!r}")  # noqa: T201
        )
        w.signals.ui_status_changed.connect(
            lambda x: print(f"ActivityPanel.signals.status_changed: {x!r}")  # noqa: T201
        )
        w.signals.ui_comment_deleted.connect(
            lambda x: print(f"comment_deleted: {x}")  # noqa: T201
        )
        w.signals.ui_comment_edited.connect(
            lambda x: print(f"comment_edited: {x}")  # noqa: T201
        )

        # test signals
        w.signals.ui_status_changed.emit("In progress")

        return w

    test(_build, style=Style.Widget)

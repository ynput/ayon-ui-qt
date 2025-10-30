"""Activity panel similar to AYON's front-end."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.text_box import AYTextBox
from ayon_ui_qt.utils import preprocess_payload
from qtpy.QtCore import QObject, Signal, Slot  # type: ignore
from qtpy.QtWidgets import QWidget

from activity_stream import AYActivityStream
from detail_panel import AYDetailPanel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity panel")


class ActivityPanelSignals(QObject):
    """All signals emitted by the activity panel."""

    # Signal emitted when comment button is clicked, passes markdown content
    ui_comment_submitted = Signal(str)  # type: ignore  # noqa: PGH003
    ui_comment_edited = Signal(object)  # type: ignore  # noqa: PGH003
    ui_comment_deleted = Signal(object)  # type: ignore  # noqa: PGH003
    ui_priority_changed = Signal(str)  # type: ignore  # noqa: PGH003
    ui_assignee_changed = Signal(str)  # type: ignore  # noqa: PGH003
    ui_status_changed = Signal(str)  # type: ignore  # noqa: PGH003


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
        activities: Optional[list] = None,
        category: AYActivityStream.Categories = "all",
    ) -> None:
        self._project = {}
        self._activities = activities
        self._category: AYActivityStream.Categories = category

        super().__init__(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_margin=8,
            layout_spacing=8,
            parent=parent,
        )

        self._build()

        # signals
        self.stream.signals.view_changed.connect(
            lambda x: self.update_stream(x, self._activities)
        )

        self.update_stream(self._category, self._activities)

    def _build(self) -> None:
        """Build and configure the panel's UI components."""
        # add header
        self.details = AYDetailPanel(self)
        self.addWidget(self.details, stretch=0)

        # add scrolling layout displaying activities
        self.stream = AYActivityStream(
            self, activities=self._activities, category=self._category
        )
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
        self.details.signals.priority_changed.connect(
            self.signals.ui_priority_changed.emit
        )
        self.stream.signals.comment_deleted.connect(
            self.signals.ui_comment_deleted.emit
        )
        self.stream.signals.comment_edited.connect(
            self.signals.ui_comment_edited.emit
        )

    def update_stream(
        self,
        category: AYActivityStream.Categories,
        activities: Optional[list] = None,
    ) -> None:
        """Update the activity stream with new category or activities.

        Args:
            category: The category to filter activities by.
            activities: Optional list of activities to display.
        """
        self._category = category
        if activities and activities != self._activities:
            self._activities = activities
        if self._activities:
            self.stream.update_stream(category, self._activities)

    @Slot(object)
    def on_ctlr_activities_changed(self, data: list) -> None:
        """Handle activities data change event.

        Args:
            data: Dictionary containing the new activities payload.
        """
        self.update_stream(self._category, data)

    @Slot(object)
    def on_ctlr_project_changed(self, data: dict) -> None:
        """Handle project change event."""
        self._project = data
        self.stream.on_project_changed(data)
        self.details.on_project_change(data)


#  TEST =======================================================================


if __name__ == "__main__":
    import json

    from ayon_ui_qt.tester import Style, test

    def _build() -> QWidget:
        file_dir = Path(__file__).parent

        # read project data
        project_file = file_dir.joinpath(
            "ayon_ui_qt",
            "resources",
            "fake-project-data.json",
        )
        with open(project_file, "r") as fr:  # noqa: PLW1514, UP015
            project_data = json.load(fr)
        print(f"[test]  read: {project_file}")  # noqa: T201

        # read activity data
        activities_file = file_dir.joinpath(
            "ayon_ui_qt",
            "resources",
            "sample_activities.json",
        )
        with open(activities_file, "r") as fr:  # noqa: PLW1514, UP015
            activity_data = json.load(fr)
        print(f"[test]  read: {activities_file}")  # noqa: T201
        activity_data = preprocess_payload(activity_data, project_data)

        # create ui
        w = ActivityPanel(category="all")

        # send data
        w.on_ctlr_project_changed(project_data)
        w.on_ctlr_activities_changed(activity_data)

        # setup signals
        w.signals.ui_comment_submitted.connect(
            lambda x: print(f"ActivityPanel.signals.comment_submitted: {x!r}")  # noqa: T201
        )
        w.signals.ui_status_changed.connect(
            lambda x: print(f"ActivityPanel.signals.status_changed: {x!r}")  # noqa: T201
        )
        w.signals.ui_priority_changed.connect(
            lambda x: print(f"ActivityPanel.signals.priority_changed: {x!r}")  # noqa: T201
        )
        w.signals.ui_status_changed.connect(w.details.on_status_changed)
        w.signals.ui_priority_changed.connect(w.details.on_priority_changed)
        w.signals.ui_comment_deleted.connect(
            lambda x: print(f"comment_deleted: {x}")
        )
        w.signals.ui_comment_edited.connect(
            lambda x: print(f"comment_edited: {x}")
        )

        # test signals
        w.signals.ui_priority_changed.emit("Normal")
        w.signals.ui_status_changed.emit("In progress")

        return w

    test(_build, style=Style.Widget)

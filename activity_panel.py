"""Activity panel similar to AYON's front-end."""

from __future__ import annotations

import logging
import os
from typing import Literal, Optional

from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.text_box import AYTextBox
from ayon_ui_qt.utils import preprocess_payload
from qtpy import QtCore, QtWidgets

from activity_stream import AYActivityStream
from detail_panel import AYDetailPanel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity panel")


class ActivityPanelSignals(QtCore.QObject):
    """All signals emitted by the activity panel."""

    # Signal emitted when comment button is clicked, passes markdown content
    comment_submitted = QtCore.Signal(str)  # type: ignore  # noqa: PGH003
    comment_edited = QtCore.Signal(int, str)  # type: ignore  # noqa: PGH003
    comment_deleted = QtCore.Signal(int, str)  # type: ignore  # noqa: PGH003
    priority_changed = QtCore.Signal(str)  # type: ignore  # noqa: PGH003
    assignee_changed = QtCore.Signal(str)  # type: ignore  # noqa: PGH003
    status_changed = QtCore.Signal(str)  # type: ignore  # noqa: PGH003


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
        parent: Optional[QtWidgets.QWidget] = None,
        activities: Optional[list] = None,
        category: Literal[
            "all", "comment", "publish", "checklist"
        ] = "comment",
    ) -> None:
        self._activities = activities
        self._category = category

        super().__init__(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_margin=8,
            layout_spacing=8,
            parent=parent,
        )

        self._build()

        # signals
        self.details.signals.view_changed.connect(
            lambda x: self.update_stream(x, self._activities)
        )

        self.update_stream(self._category, self._activities)

    def _build(self) -> None:
        """Build and configure the panel's UI components."""
        # add header
        self.details = AYDetailPanel(self)
        self.addWidget(self.details, stretch=0)
        # add tab layout with hidden tabs
        self.stream = AYActivityStream(
            self, activities=self._activities, category=self._category
        )
        self.addWidget(self.stream, stretch=10)
        # add comment editor
        self.editor = AYTextBox(num_lines=3)
        self.addWidget(self.editor, stretch=0)
        # connect signals
        self.editor.signals.comment_submitted.connect(
            self.signals.comment_submitted.emit
        )

    def update_stream(
        self, category: str, activities: Optional[list] = None
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

    def on_activities_changed(self, data: dict) -> None:
        """Handle activities data change event.

        Args:
            data: Dictionary containing the new activities payload.
        """
        activities = preprocess_payload(data)
        self.update_stream(self._category, activities)


#  TEST =======================================================================


if __name__ == "__main__":
    import json

    from ayon_ui_qt.tester import Style, test

    def _build() -> QtWidgets.QWidget:
        data_file = os.path.join(
            os.path.dirname(__file__),
            "ayon_ui_qt",
            "resources",
            "GetActivities-recieved-data.json",
        )
        with open(data_file, "r") as fr:  # noqa: PLW1514, UP015
            payload = json.load(fr)

        data = preprocess_payload(payload)

        w = ActivityPanel(activities=data, category="comment")
        w.signals.comment_submitted.connect(
            lambda x: print(f"ActivityPanel.signals.comment_submitted: {x!r}")  # noqa: T201
        )

        return w

    test(_build, style=Style.Widget)

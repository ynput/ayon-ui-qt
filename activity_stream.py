"""Activity stream UI."""

from __future__ import annotations

import logging
import os
from typing import Literal

from ayon_ui_qt.components.comment import AYComment, AYPublish, AYStatusChange
from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.utils import clear_layout, preprocess_payload
from qtpy import QtWidgets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity stream")


class AYActivityStream(AYContainer):
    """Activity stream widget for displaying and managing activity events.

    This widget extends AYContainer to provide a scrollable container for
    displaying activity events (comments, etc.) organized by category.

    Attributes:
        _activities (dict): Dictionary of activity data.
        _category (str): Current activity category being displayed.
        scroll_area (QtWidgets.QScrollArea): Scrollable area for activities.
        scroll_ctnr (AYContainer): Container holding activity widgets.
    """

    def __init__(
        self,
        *args,  # noqa: ANN002
        category: Literal[
            "all", "comment", "publish", "checklist"
        ] = "comment",
        activities: list | None = None,
        **kwargs,  # noqa: ANN003
    ):
        """Initialize the activity stream widget.

        Args:
            *args: Variable length argument list passed to parent class.
            category (str): Initial activity category. Defaults to "comment".
            activities (dict): Dictionary of activity data. Defaults to {}.
            **kwargs: Arbitrary keyword arguments. Supports:
                Additional kwargs are passed to parent AYContainer.
        """
        self._project = {}
        self._activities = activities or []
        self._category = kwargs.pop("category", "comment")

        super().__init__(
            *args,
            layout=AYContainer.Layout.VBox,
            variant="low",
            **kwargs,
        )

        self._build()

    def _build_stream(self) -> QtWidgets.QScrollArea:
        """Build and configure the scrollable activity stream container.

        Creates a QScrollArea with a vertical box layout container for
        displaying activity widgets.

        Returns:
            QtWidgets.QScrollArea: Configured scroll area containing the
                activity container.
        """
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_ctnr = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_spacing=20,
        )

        self.scroll_area.setWidget(self.scroll_ctnr)
        self.scroll_area.setWidgetResizable(True)

        return self.scroll_area

    def _build(self) -> None:
        """Build the activity stream widget layout.

        Adds the scrollable stream to the main container.
        """
        self.add_widget(self._build_stream())

    def update_stream(self, category: str, activities: list) -> None:
        """Update the activity stream with new activities.

        Clears the current stream and populates it with activities matching
        the specified category.

        Args:
            category (str): The activity category to filter by.
            activities (list): List of activity event objects to display.
                Each event should have a 'type' attribute matching the
                category.
        """
        self._category = category
        clear_layout(self.scroll_ctnr)
        for event in activities or []:
            if category not in {"all", event.type}:
                continue
            if event.type == "comment":
                self.scroll_ctnr.add_widget(AYComment(self, data=event))
            elif event.type == "publish":
                self.scroll_ctnr.add_widget(
                    AYPublish(self, data=event), stretch=0
                )
            elif event.type == "status":
                self.scroll_ctnr.add_widget(
                    AYStatusChange(self, data=event), stretch=0
                )
        self.scroll_ctnr.addStretch(100)

    def on_project_changed(self, data):
        """store new project data and clear the activity stream."""
        self._project = data
        self.update_stream(self._category, [])


#  TEST ======================================================================


if __name__ == "__main__":
    import json

    from ayon_ui_qt.tester import test, Style
    from ayon_ui_qt.utils import preprocess_payload

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

        return AYActivityStream(activities=data)

    test(_build, style=Style.Widget)

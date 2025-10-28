"""Activity stream UI."""

from __future__ import annotations

import logging
import os
from typing import Literal, get_args

from qtpy.QtCore import QObject, Signal  # type: ignore
from qtpy.QtWidgets import QButtonGroup, QScrollArea, QWidget

from ayon_ui_qt.data_models import CommentModel
from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.comment import AYComment, AYPublish, AYStatusChange
from ayon_ui_qt.components.container import AYContainer, AYHBoxLayout
from ayon_ui_qt.utils import clear_layout, preprocess_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity stream")


class ActivityStreamSignals(QObject):
    # Node signals
    view_changed = Signal(str)  # type: ignore # category
    comment_deleted = Signal(object)
    comment_edited = Signal(object)


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

    signals = ActivityStreamSignals()
    Categories = Literal["all", "comment", "version.publish", "checklist"]

    def __init__(
        self,
        *args,  # noqa: ANN002
        category: Categories = "all",
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
        self._category = category

        super().__init__(
            *args,
            layout=AYContainer.Layout.VBox,
            variant="low",
            **kwargs,
        )

        self._build()

    def _build_buttons(self):
        self.feed_all = AYButton(
            icon="forum",
            variant="surface",
            checkable=True,
            tooltip="All activity",
        )
        self.feed_com = AYButton(
            icon="chat", variant="surface", checkable=True, tooltip="Comments"
        )
        self.feed_pub = AYButton(
            icon="layers",
            variant="surface",
            checkable=True,
            tooltip="Published versions",
        )
        self.feed_chk = AYButton(
            icon="checklist",
            variant="surface",
            checkable=True,
            tooltip="Checklists",
        )
        self.feed_det = AYButton(
            "Details",
            parent=self,
            variant="surface",
            checkable=True,
        )

        self.feed_all.clicked.connect(
            lambda: self.signals.view_changed.emit("all")
        )
        self.feed_com.clicked.connect(
            lambda: self.signals.view_changed.emit("comment")
        )
        self.feed_pub.clicked.connect(
            lambda: self.signals.view_changed.emit("version.publish")
        )
        self.feed_chk.clicked.connect(
            lambda: self.signals.view_changed.emit("checklist")
        )
        self.feed_det.clicked.connect(
            lambda: self.signals.view_changed.emit("details")
        )

        self.button_grp = QButtonGroup(self)
        self.button_grp.setExclusive(True)
        self.button_grp.addButton(self.feed_all)
        self.button_grp.addButton(self.feed_com)
        self.button_grp.addButton(self.feed_pub)
        self.button_grp.addButton(self.feed_chk)
        self.button_grp.addButton(self.feed_det)

        feed_lyt = AYHBoxLayout(None)
        feed_lyt.addWidget(self.feed_all)
        feed_lyt.addWidget(self.feed_com)
        feed_lyt.addWidget(self.feed_pub)
        feed_lyt.addWidget(self.feed_chk)
        feed_lyt.addStretch()
        feed_lyt.addWidget(self.feed_det)

        self.feed_all.setChecked(self._category == "all")
        self.feed_com.setChecked(self._category == "comment")
        self.feed_pub.setChecked(self._category == "version.publish")
        self.feed_det.setChecked(self._category == "details")

        return feed_lyt

    def _build_stream(self) -> QScrollArea:
        """Build and configure the scrollable activity stream container.

        Creates a QScrollArea with a vertical box layout container for
        displaying activity widgets.

        Returns:
            QtWidgets.QScrollArea: Configured scroll area containing the
                activity container.
        """
        self.scroll_area = QScrollArea()
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
        self.add_layout(self._build_buttons(), stretch=0)
        self.add_widget(self._build_stream(), stretch=100)

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
                comment = AYComment(self, data=event)
                self.scroll_ctnr.add_widget(comment)
                # connect signals
                comment.comment_deleted.connect(
                    self._on_comment_deleted
                )
                comment.comment_edited.connect(
                    self.signals.comment_edited.emit
                )
            elif event.type == "version.publish":
                self.scroll_ctnr.add_widget(
                    AYPublish(self, data=event), stretch=0
                )
            elif event.type == "status.change":
                self.scroll_ctnr.add_widget(
                    AYStatusChange(self, data=event), stretch=0
                )
        self.scroll_ctnr.addStretch(100)
        self._activities = activities

    def _on_comment_deleted(self, data: CommentModel):
        """Delete widget, delete comment from activities and emit signal."""
        for i in range(self.scroll_ctnr._layout.count()):
            item = self.scroll_ctnr._layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if not isinstance(w, AYComment):
                continue
            if data == w._data:
                w.setParent(None)
                w.deleteLater()
                self._activities.remove(data)
                break
        self.signals.comment_deleted.emit(data)

    def on_project_changed(self, data):
        """store new project data and clear the activity stream."""
        self._project = data
        self.update_stream(self._category, [])


#  TEST ======================================================================


if __name__ == "__main__":
    import json

    from ayon_ui_qt.tester import Style, test
    from ayon_ui_qt.utils import preprocess_payload

    def _build() -> QWidget:
        data_file = os.path.join(
            os.path.dirname(__file__),
            "ayon_ui_qt",
            "resources",
            "sample_activities.json",
        )
        with open(data_file, "r") as fr:  # noqa: PLW1514, UP015
            activity_data = json.load(fr)

        data_file = os.path.join(
            os.path.dirname(__file__),
            "ayon_ui_qt",
            "resources",
            "fake-project-data.json",
        )
        with open(data_file, "r") as fr:  # noqa: PLW1514, UP015
            project_data = json.load(fr)

        data = preprocess_payload(activity_data, project_data)

        return AYActivityStream(activities=data)

    test(_build, style=Style.Widget)

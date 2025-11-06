"""Activity stream UI."""

from __future__ import annotations

import logging
from typing import Literal
import datetime

from ayon_ui_qt import style_widget_and_siblings
from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.comment import AYComment, AYPublish, AYStatusChange
from ayon_ui_qt.components.container import AYContainer, AYHBoxLayout
from ayon_ui_qt.components.label import AYLabel
from ayon_ui_qt.data_models import (
    ActivityData,
    CommentModel,
    ProjectData,
    StatusChangeModel,
    VersionData,
    VersionPublishModel,
)
from ayon_ui_qt.utils import (
    clear_layout,
    get_test_activity_data,
    get_test_project_data,
    get_test_version_data,
)
from qtpy.QtCore import QObject, Signal, Slot  # type: ignore
from qtpy.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QScrollArea,
    QWidget,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity stream")


def time_stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class ActivityStreamSignals(QObject):
    """Signals for the activity stream widget."""

    # Node signals
    comment_deleted = Signal(CommentModel)
    comment_edited = Signal(CommentModel)


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
        self._project = ProjectData.not_set()
        self._version = VersionData.not_set()
        self._activities = ActivityData()
        self._category = category

        super().__init__(
            *args,
            layout=AYContainer.Layout.VBox,
            variant="low",
            **kwargs,
        )

        self._build()
        self.update_stream(self._category, self._activities)

    def _build_buttons(self) -> AYHBoxLayout:
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

        self.feed_all.clicked.connect(lambda: self._on_view_changed("all"))
        self.feed_com.clicked.connect(lambda: self._on_view_changed("comment"))
        self.feed_pub.clicked.connect(
            lambda: self._on_view_changed("version.publish")
        )
        self.feed_chk.clicked.connect(
            lambda: self._on_view_changed("checklist")
        )
        self.feed_det.clicked.connect(lambda: self._on_view_changed("details"))

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

    def _clear_stream(self) -> None:
        self.update_stream(self._category, ActivityData())

    def update_stream(self, category: str, activities: ActivityData) -> None:
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

        if category == "details":
            form = QFormLayout(horizontalSpacing=64, verticalSpacing=8)
            form.addRow(AYLabel("Attributes", dim=True))
            for attr, val in self._version.attrib.items():
                form.addRow(
                    AYLabel(attr, dim=True, rel_text_size=-1),
                    AYLabel(str(val) if val else "", rel_text_size=-1),
                )
            self.scroll_ctnr.add_layout(form)
            return

        for event in activities.activity_list:
            if category not in {"all", event.type}:
                continue
            if isinstance(event, CommentModel):
                comment = AYComment(
                    self, data=event, user_list=self._project.users
                )
                self.scroll_ctnr.add_widget(comment)
                # connect signals
                comment.comment_deleted.connect(self._on_comment_deleted)
                comment.comment_edited.connect(
                    self.signals.comment_edited.emit
                )
            elif isinstance(event, VersionPublishModel):
                self.scroll_ctnr.add_widget(
                    AYPublish(self, data=event), stretch=0
                )
            elif isinstance(event, StatusChangeModel):
                self.scroll_ctnr.add_widget(
                    AYStatusChange(self, data=event), stretch=0
                )
        self.scroll_ctnr.addStretch(100)
        self._activities = activities
        style_widget_and_siblings(self)

    def on_comment_submitted(self, markdown: str, category: str) -> None:
        keys = [c.name for c in self._project.comment_category]
        cat = self._project.comment_category[keys.index(category)]

        if not self._project.current_user:
            raise ValueError("current_user MUST be provided !")

        m = CommentModel(
            user_full_name=self._project.current_user.full_name,
            user_name=self._project.current_user.name,
            user_src="",
            comment=markdown,
            category=category,
            category_color=cat.color,
            comment_date=time_stamp(),
        )
        idx = self.scroll_ctnr.count() - 1
        w = AYComment(self, data=m, user_list=self._project.users)
        self.scroll_ctnr.insert_widget(idx, w)
        self._activities.activity_list.append(m)
        style_widget_and_siblings(self)

    @Slot(str)
    def _on_view_changed(self, category: Categories) -> None:
        self.update_stream(category, self._activities)

    @Slot(CommentModel)
    def _on_comment_deleted(self, data: CommentModel) -> None:
        """Delete widget, delete comment from activities and emit signal."""
        for i in range(self.scroll_ctnr.count()):
            item = self.scroll_ctnr.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if not isinstance(w, AYComment):
                continue
            if data == w._data:
                w.setParent(None)
                w.deleteLater()
                self._activities.activity_list.remove(data)
                break
        self.signals.comment_deleted.emit(data)

    @Slot(ProjectData)
    def on_project_changed(self, data: ProjectData) -> None:
        """Store new project data and clear the activity stream."""
        if self._project and self._project.project_name != data.project_name:
            self._clear_stream()
        self._project = data

    @Slot(VersionData)
    def on_version_data_changed(self, data: VersionData) -> None:
        """Store new version data and clear the activity stream."""
        # display attributes
        if self._version and self._version.id != data.id:
            self._clear_stream()
        self._version = data


#  TEST ======================================================================


if __name__ == "__main__":
    from ayon_ui_qt.tester import Style, test

    def _build() -> QWidget:
        project_data = get_test_project_data()
        version_data = get_test_version_data()
        data = get_test_activity_data()

        w = AYActivityStream()

        w.on_project_changed(project_data)
        w.on_version_data_changed(version_data)
        w.update_stream("all", data)

        w.signals.comment_deleted.connect(
            lambda x: print(f"comment_deleted: {x}")  # noqa: T201
        )
        w.signals.comment_edited.connect(
            lambda x: print(f"comment_edited: {x}")  # noqa: T201
        )

        return w

    test(_build, style=Style.Widget)

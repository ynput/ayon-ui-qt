import os
from typing import Optional

from qtpy import QtCore, QtWidgets

from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.container import AYContainer, AYFrame
from ayon_ui_qt.components.entity_path import AYEntityPath
from ayon_ui_qt.components.entity_thumbnail import AYEntityThumbnail
from ayon_ui_qt.components.label import AYLabel
from ayon_ui_qt.components.layouts import (
    AYGridLayout,
    AYHBoxLayout,
    AYVBoxLayout,
)


class DetailSignals(QtCore.QObject):
    # Node signals
    view_changed = QtCore.Signal(str)  # type: ignore # category


class AYDetailPanel(AYContainer):
    signals = DetailSignals()

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(
            layout=AYContainer.Layout.VBox,
            variant="low",
            parent=parent,
        )
        self._build()

    def _build_thumbnail(self):
        self.entity_thumbnail = AYEntityThumbnail(self)
        self.entity_name = AYLabel("entity")
        self.entity_tag = AYButton(parent=self, variant="text", icon="sell")
        self.task_info = AYLabel("Task - Render")

        thumb_lyt = AYHBoxLayout()
        thumb_lyt.addWidget(self.entity_thumbnail)
        thumb_info_lyt = AYVBoxLayout(margin=0)
        name_tag_lyt = AYHBoxLayout(margin=0)
        name_tag_lyt.addWidget(self.entity_name)
        name_tag_lyt.addWidget(self.entity_tag)
        thumb_info_lyt.addLayout(name_tag_lyt)
        thumb_info_lyt.addWidget(self.task_info)
        thumb_lyt.addLayout(thumb_info_lyt)
        thumb_lyt.addStretch()
        return thumb_lyt

    def _build_status(self):
        # FIXME
        return AYHBoxLayout()

    def _build_assignee(self):
        # FIXME
        return AYHBoxLayout()

    def _build_webactions(self):
        # FIXME
        return AYHBoxLayout()

    def _build_priority(self):
        # FIXME
        return AYHBoxLayout()

    def _build_streams(self):
        self.feed_all = AYButton(icon="forum", variant="surface")
        self.feed_com = AYButton(icon="chat", variant="surface")
        self.feed_pub = AYButton(icon="layers", variant="surface")
        self.feed_chk = AYButton(icon="checklist", variant="surface")

        self.feed_all.clicked.connect(
            lambda: self.signals.view_changed.emit("all")
        )
        self.feed_com.clicked.connect(
            lambda: self.signals.view_changed.emit("comment")
        )
        self.feed_pub.clicked.connect(
            lambda: self.signals.view_changed.emit("publish")
        )
        self.feed_chk.clicked.connect(
            lambda: self.signals.view_changed.emit("checklist")
        )

        feed_lyt = AYHBoxLayout(None)
        feed_lyt.addWidget(self.feed_all)
        feed_lyt.addWidget(self.feed_com)
        feed_lyt.addWidget(self.feed_pub)
        feed_lyt.addWidget(self.feed_chk)
        feed_lyt.addStretch()
        return feed_lyt

    def _build_attrs(self):
        self.attrs = AYButton("Details", parent=self, variant="surface")
        self.attrs.clicked.connect(
            lambda: self.signals.view_changed.emit("view_attributes")
        )

        lyt = AYHBoxLayout()
        lyt.addSpacerItem(
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
        )
        lyt.addWidget(self.attrs)
        return lyt

    def _build(self):
        self.entity_path = AYEntityPath(self)
        self.thumbnail = self._build_thumbnail()
        self.status = self._build_status()
        self.assignee = self._build_assignee()
        self.webactions = self._build_webactions()
        self.priority = self._build_priority()
        self.streams = self._build_streams()
        self.attrs = self._build_attrs()

        grid_lyt = AYGridLayout()
        grid_lyt.addLayout(self.thumbnail, 0, 0)
        grid_lyt.addLayout(self.status, 1, 0)
        grid_lyt.addLayout(self.assignee, 1, 1)
        grid_lyt.addLayout(self.webactions, 2, 0)
        grid_lyt.addLayout(self.priority, 2, 1)
        grid_lyt.addLayout(self.streams, 3, 0)
        grid_lyt.addLayout(self.attrs, 3, 1)

        self.addWidget(self.entity_path)
        self.addLayout(grid_lyt)


# TEST =======================================================================


if __name__ == "__main__":
    from ayon_ui_qt.tester import test

    def _build():
        w = AYDetailPanel()
        w.signals.view_changed.connect(lambda x: print(f"view_changed: {x}"))
        return w

    os.environ["QT_SCALE_FACTOR"] = "1"
    test(_build)

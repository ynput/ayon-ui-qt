import os
from typing import Optional

from qtpy.QtWidgets import QButtonGroup, QWidget
from qtpy.QtCore import QObject, Signal  # type: ignore

from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.entity_path import AYEntityPath
from ayon_ui_qt.components.entity_thumbnail import AYEntityThumbnail
from ayon_ui_qt.components.label import AYLabel
from ayon_ui_qt.components.layouts import (
    AYGridLayout,
    AYHBoxLayout,
    AYVBoxLayout,
)


class AYDetailPanel(AYContainer):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
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

    def _build(self):
        self.entity_path = AYEntityPath(self)
        self.thumbnail = self._build_thumbnail()
        self.status = self._build_status()
        self.assignee = self._build_assignee()
        self.webactions = self._build_webactions()
        self.priority = self._build_priority()

        grid_lyt = AYGridLayout(spacing=0, margin=0)
        grid_lyt.addLayout(self.thumbnail, 0, 0)
        grid_lyt.addLayout(self.status, 1, 0)
        grid_lyt.addLayout(self.assignee, 1, 1)
        grid_lyt.addLayout(self.webactions, 2, 0)
        grid_lyt.addLayout(self.priority, 2, 1)

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

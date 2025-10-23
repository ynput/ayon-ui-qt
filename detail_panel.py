"""Detail panel UI."""

from __future__ import annotations

import os

from qtpy.QtCore import QObject, Qt, Signal  # type: ignore
from qtpy.QtWidgets import QWidget

from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.combo_box import AYComboBox
from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.entity_path import AYEntityPath
from ayon_ui_qt.components.entity_thumbnail import AYEntityThumbnail
from ayon_ui_qt.components.label import AYLabel
from ayon_ui_qt.components.layouts import (
    AYGridLayout,
    AYHBoxLayout,
    AYVBoxLayout,
)

MISSING_STATUSES = [
    {
        "name": "No Project",
        "original_name": "No Project",
        "shortName": "NPR",
        "state": "no_project",
        "icon": "question_mark",
        "color": "#9B7C76",
    },
]

PRIORITIES = [
    {
        "text": "Urgent",
        "short_text": "Urgent",
        "icon": "keyboard_double_arrow_up",
        "color": "#ff8585",
    },
    {
        "text": "High",
        "short_text": "High",
        "icon": "keyboard_arrow_up",
        "color": "#ffad66",
    },
    {
        "text": "Normal",
        "short_text": "Normal",
        "icon": "check_indeterminate_small",
        "color": "#9ac0e7",
    },
    {
        "text": "Low",
        "short_text": "Low",
        "icon": "keyboard_arrow_down",
        "color": "#9fa7b1",
    },
]


class DetailPanelSignals(QObject):
    status_changed = Signal(str)
    priority_changed = Signal(str)


class AYDetailPanel(AYContainer):
    """A detail panel widget displaying entity information and controls.

    This panel shows entity thumbnails, metadata, status, assignees, and
    provides buttons for viewing different feed streams and attributes.

    Attributes:
        signals: DetailSignals instance for emitting view change events.
        entity_thumbnail: Widget displaying the entity thumbnail.
        entity_name: Label showing the entity name.
        entity_tag: Button displaying the entity tag.
        task_info: Label showing task information.
        feed_all: Button for viewing all feed items.
        feed_com: Button for viewing comments.
        feed_pub: Button for viewing published items.
        feed_chk: Button for viewing checklist items.
        attrs: Button for viewing entity attributes.
        entity_path: Widget displaying the entity path.
        thumbnail: Layout containing thumbnail and entity info.
        status: Layout for status information.
        assignee: Layout for assignee information.
        webactions: Layout for web actions.
        priority: Layout for priority information.
        streams: Layout for feed stream buttons.
    """

    signals = DetailPanelSignals()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the detail panel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(
            layout=AYContainer.Layout.VBox,
            variant="low",
            parent=parent,
        )
        self._project = {}  # project data (anatomy, users, ect)
        self._build()

    def _build_thumbnail(self) -> AYHBoxLayout:
        """Build the thumbnail section layout.

        Creates a horizontal layout containing the entity thumbnail,
        entity name, tag, and task information.

        Returns:
            AYHBoxLayout: The constructed thumbnail layout.
        """
        self.entity_thumbnail = AYEntityThumbnail(self)
        self.entity_name = AYLabel("entity")
        self.entity_tag = AYButton(parent=self, variant="text", icon="sell")
        self.task_info = AYLabel("Task - Render")

        thumb_lyt = AYHBoxLayout(margin=0)
        thumb_lyt.addWidget(self.entity_thumbnail)
        thumb_info_lyt = AYVBoxLayout()
        name_tag_lyt = AYHBoxLayout()
        name_tag_lyt.addWidget(self.entity_name)
        name_tag_lyt.addWidget(self.entity_tag)
        thumb_info_lyt.addLayout(name_tag_lyt)
        thumb_info_lyt.addWidget(self.task_info)
        thumb_lyt.addLayout(thumb_info_lyt)
        thumb_lyt.addStretch()
        return thumb_lyt

    def _get_statuses(self) -> list[dict[str, str]]:
        """Get status items based on project anatomy data."""
        statuses = self._project.get("anatomy", {}).get(
            "statuses", MISSING_STATUSES
        )
        items = [
            {
                "text": s["name"],
                "short_text": s["shortName"],
                "icon": s["icon"],
                "color": s["color"],
            }
            for s in statuses
        ]
        return items

    def _get_priorities(self) -> list[dict[str, str]]:
        """Get priority items based on front-end data."""
        return PRIORITIES

    def _build_status(self) -> AYComboBox:
        """Build the status section layout.

        Returns:
            AYComboBox: A configured combo box.
        """
        items = self._get_statuses()
        return AYComboBox(items=items, inverted=True, height=30)

    def _build_assignee(self) -> AYHBoxLayout:
        """Build the assignee section layout.

        Returns:
            AYHBoxLayout: An empty horizontal layout for assignee.
        """
        # TODO(plp): implement me !
        return AYHBoxLayout(margin=0)

    def _build_webactions(self) -> AYHBoxLayout:
        """Build the web actions section layout.

        Returns:
            AYHBoxLayout: An empty horizontal layout for web actions.
        """
        # TODO(plp): implement me !
        return AYHBoxLayout(margin=0)

    def _build_priority(self) -> AYComboBox:
        """Build the priority section layout.

        Returns:
            AYComboBox: A combo box widget for selecting priority.
        """
        priorities = self._get_priorities()
        return AYComboBox(items=priorities, height=30)

    def _build(self) -> None:
        """Build the complete detail panel layout.

        Constructs all sub-sections (thumbnail, status, assignee, etc.)
        and arranges them in a grid layout within the main container.
        """
        self.entity_path = AYEntityPath(self)
        self.thumbnail = self._build_thumbnail()
        self.status = self._build_status()
        self.assignee = self._build_assignee()
        self.webactions = self._build_webactions()
        self.priority = self._build_priority()

        grid_lyt = AYGridLayout(spacing=4, margin=4)
        grid_lyt.addLayout(self.thumbnail, 0, 0)
        grid_lyt.addWidget(
            self.status, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft
        )
        grid_lyt.addLayout(self.assignee, 1, 1)
        grid_lyt.addLayout(self.webactions, 2, 0)
        grid_lyt.addWidget(
            self.priority, 2, 1, alignment=Qt.AlignmentFlag.AlignRight
        )

        self.addWidget(self.entity_path)
        self.addLayout(grid_lyt)

        # connect signals
        self.status.currentTextChanged.connect(
            self.signals.status_changed.emit
        )
        self.priority.currentTextChanged.connect(
            self.signals.priority_changed.emit
        )

    def _update_status_items(self):
        self.status.update_items(self._get_statuses())
        self.status.setCurrentIndex(0)

    def on_project_change(self, data: dict) -> None:
        self._project = data
        self._update_status_items()


# TEST =======================================================================


if __name__ == "__main__":
    from ayon_ui_qt.tester import test

    def _build() -> AYDetailPanel:
        w = AYDetailPanel()
        w.signals.status_changed.connect(
            lambda x: print(f"status_changed: {x}")
        )  # noqa: T201
        return w

    os.environ["QT_SCALE_FACTOR"] = "1"
    test(_build)

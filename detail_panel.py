"""Detail panel UI."""

from __future__ import annotations


from qtpy.QtCore import QObject, Qt, Signal, Slot  # type: ignore
from qtpy.QtWidgets import QWidget

from ayon_ui_qt import style_widget_and_siblings
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
from ayon_ui_qt.data_models import ProjectData, VersionData
from ayon_ui_qt.utils import get_test_project_data, get_test_version_data

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


def block_signals(attr: str):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            obj: QObject = getattr(self, attr)
            obj.blockSignals(True)
            result = func(self, *args, **kwargs)
            obj.blockSignals(False)
            return result

        return wrapper

    return decorator


class DetailPanelSignals(QObject):
    version_status_changed = Signal(str)


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
            variant=AYContainer.Variants.Low,
            parent=parent,
        )
        self._project: ProjectData = ProjectData.not_set()
        self._version_data: VersionData = VersionData.not_set()
        self._build()

        # # Apply styling to this widget and its children
        # style_widget_and_siblings(self)

    def _build_thumbnail(self) -> AYHBoxLayout:
        """Build the thumbnail section layout.

        Creates a horizontal layout containing the entity thumbnail,
        entity name, tag, and task information.

        Returns:
            AYHBoxLayout: The constructed thumbnail layout.
        """
        self.entity_thumbnail = AYEntityThumbnail(parent=self)
        self.product_name = AYLabel("product name")
        self.entity_tag = AYButton(
            parent=self, variant=AYButton.Variants.Text, icon="sell"
        )
        self.task_info = AYLabel("Task - Render")

        thumb_lyt = AYHBoxLayout(margin=0)
        thumb_lyt.addWidget(self.entity_thumbnail)
        thumb_info_lyt = AYVBoxLayout()
        name_tag_lyt = AYHBoxLayout()
        name_tag_lyt.addWidget(self.product_name)
        name_tag_lyt.addWidget(self.entity_tag)
        thumb_info_lyt.addLayout(name_tag_lyt)
        thumb_info_lyt.addWidget(self.task_info)
        thumb_lyt.addLayout(thumb_info_lyt)
        thumb_lyt.addStretch()
        return thumb_lyt

    def _get_statuses(self) -> list[dict[str, str]]:
        """Get status items based on project anatomy data."""
        statuses = self._project.anatomy.get("statuses", MISSING_STATUSES)
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
        """Get priority items. These seem to be constants."""
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

        grid_lyt = AYGridLayout(spacing=4, margin=4)
        grid_lyt.addLayout(self.thumbnail, 0, 0)
        grid_lyt.addWidget(
            self.status, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft
        )
        grid_lyt.addLayout(self.assignee, 1, 1)
        grid_lyt.addLayout(self.webactions, 2, 0)

        self.add_widget(self.entity_path)
        self.add_layout(grid_lyt)

        # connect signals
        self.status.currentTextChanged.connect(
            self.signals.version_status_changed.emit
        )

    @block_signals("status")
    def _update_status_items(self):
        self.status.update_items(self._get_statuses())
        self.status.setCurrentIndex(0)

    @block_signals("status")
    def _update_status(self):
        current_status = self._version_data.status
        print(f"current_status = {current_status}")
        if current_status:
            self.status.setCurrentText(current_status)

    @block_signals("entity_path")
    def _update_entity_path(self):
        path = "%s/%s/%s" % (
            self._project.project_name,
            self._version_data.folder_path,
            self._version_data.task_name,
        )
        self.entity_path.entity_path = path

    def _update_product_name(self):
        self.product_name.setText(
            self._version_data.product_name or "Not available"
        )

    @Slot(ProjectData)
    def on_ctlr_project_changed(self, data: ProjectData) -> None:
        """Project was updated by the controler."""
        self._project = data
        self._update_status_items()

    @Slot(str)
    def on_ctlr_version_status_changed(self, new_status: str):
        """Status was updated by the controler."""
        self._version_data.status = new_status
        self._update_status()

    @Slot(VersionData)
    def on_ctlr_version_data_changed(self, data: VersionData):
        """version data was updated by the controler."""
        self._version_data = data
        self._update_status()
        # self._update_priority()
        self._update_entity_path()
        self._update_product_name()


# TEST =======================================================================


if __name__ == "__main__":
    from ayon_ui_qt.tester import test

    def _build() -> AYDetailPanel:
        version_data = get_test_version_data()
        project_data = get_test_project_data()

        w = AYDetailPanel()

        w.on_ctlr_project_changed(project_data)
        w.on_ctlr_version_data_changed(version_data)

        w.signals.version_status_changed.connect(
            lambda x: print(f"status_changed: {x}")
        )  # noqa: T201
        return w

    test(_build)

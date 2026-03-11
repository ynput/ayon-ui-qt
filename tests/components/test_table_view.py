"""Visual regression tests for AYTableView."""

from __future__ import annotations

from qtpy.QtWidgets import QWidget

from widget_test import WidgetTest
from ayon_ui_qt.components.table_view import AYTableView
from ayon_ui_qt.components.table_model import PaginatedTableModel, TableColumn
from ayon_ui_qt.components.container import AYContainer


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_COLUMNS = [
    TableColumn(key="name",    label="Name",    width=160, sortable=True),
    TableColumn(key="task",    label="Task",    width=120, sortable=True),
    TableColumn(key="status",  label="Status",  width=100, sortable=True),
    TableColumn(key="assignee",label="Assignee",width=120, sortable=False),
]

_ROWS = [
    {"name": "hero_model_v003",  "task": "Modeling",    "status": "Approved",        "assignee": "Alice"},
    {"name": "hero_rig_v001",    "task": "Rigging",     "status": "In progress",     "assignee": "Bob"},
    {"name": "hero_lookdev_v002","task": "Lookdev",     "status": "Pending review",  "assignee": "Carol"},
    {"name": "bg_arch_v005",     "task": "Modeling",    "status": "Approved",        "assignee": "Dave"},
    {"name": "bg_lookdev_v001",  "task": "Lookdev",     "status": "Not ready",       "assignee": "Alice"},
    {"name": "camera_anim_v010", "task": "Animation",   "status": "In progress",     "assignee": "Eve"},
    {"name": "crowd_anim_v002",  "task": "Animation",   "status": "On hold",         "assignee": "Bob"},
    {"name": "vfx_smoke_v004",   "task": "FX",          "status": "Approved",        "assignee": "Frank"},
]


def _make_fetch(rows):
    def fetch_page(page_number, page_size, sort_key=None, descending=False):
        start = page_number * page_size
        end = start + page_size
        return rows[start:end]
    return fetch_page


class TableViewTest(WidgetTest):
    """Tests AYTableView with paginated data and sorting."""

    size = (700, 320)
    tolerance = 0.0

    def build(self) -> QWidget:
        root = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=0,
        )

        model = PaginatedTableModel(
            fetch_page=_make_fetch(_ROWS),
            columns=_COLUMNS,
            page_size=50,
        )
        self._view = AYTableView(variant=AYTableView.Variants.Default)
        self._view.setModel(model)
        self._view.setMinimumHeight(240)

        root.add_widget(self._view, stretch=1)
        return root

    def select_first_row(self) -> None:
        """Select the first row to show the selection highlight."""
        idx = self._view.model().index(0, 0)
        self._view.setCurrentIndex(idx)

    def steps(self):
        return [self.select_first_row]

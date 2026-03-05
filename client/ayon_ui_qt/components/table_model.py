"""Paginated Qt table model with lazy loading support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from qtpy.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)

log = logging.getLogger(__name__)


@dataclass
class TableColumn:
    """Describes a single column in a PaginatedTableModel.

    Attributes:
        key: Dictionary key used to look up cell values in row data.
        label: Display text shown in the header.
        width: Preferred column width hint in pixels. 0 means auto.
    """

    key: str
    label: str
    width: int = 0


class PaginatedTableModel(QAbstractTableModel):
    """A Qt table model that lazily loads rows page-by-page via a callback.

    Rows are fetched on demand using Qt's canFetchMore / fetchMore
    mechanism.  Each call to fetchMore retrieves one page of data from
    the supplied ``fetch_page`` callable.

    Args:
        fetch_page: Callable that takes ``(page_number, page_size)`` and
            returns a list of row dicts.  Page numbers are 0-based.
        columns: Column definitions.  When ``None``, columns are inferred
            from the keys of the first fetched row.
        page_size: Number of rows per page.
        parent: Optional parent QObject.
    """

    WidgetFactoryRole: int = Qt.ItemDataRole.UserRole + 10

    def __init__(
        self,
        fetch_page: Callable[[int, int, str | None, bool], list[dict[str, Any]]],
        columns: list[TableColumn] | None = None,
        page_size: int = 50,
        parent: QObject | None = None,
    ) -> None:
        """Initialise the model and fetch the first page.

        Args:
            fetch_page: Callable ``(page, page_size) -> list[dict]``.
            columns: Explicit column definitions, or ``None`` to infer.
            page_size: Rows per page.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._fetch_page = fetch_page
        self._explicit_columns: list[TableColumn] | None = columns
        self._columns: list[TableColumn] = columns or []
        self._page_size: int = page_size
        self._rows: list[dict[str, Any]] = []
        self._current_page: int = 0
        self._has_more: bool = True
        self._is_fetching: bool = False
        self._sort_column: int = -1
        self._sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder

        self._fetch_next_page()

    # Properties --------------------------------------------------------------

    @property
    def columns(self) -> list[TableColumn]:
        """Return the current column definitions.

        Returns:
            List of TableColumn instances.
        """
        return list(self._columns)

    @property
    def page_count(self) -> int:
        """Return the number of pages fetched so far.

        Returns:
            Current page index (pages fetched = _current_page).
        """
        return self._current_page

    # QAbstractTableModel overrides -------------------------------------------

    def rowCount(  # noqa: N802
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        """Return the number of rows in the model.

        Args:
            parent: Parent index; returns 0 for valid parents (flat
                table).

        Returns:
            Number of loaded rows, or 0 if parent is valid.
        """
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(  # noqa: N802
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        """Return the number of columns in the model.

        Args:
            parent: Parent index; returns 0 for valid parents.

        Returns:
            Number of columns, or 0 if parent is valid.
        """
        if parent.isValid():
            return 0
        return len(self._columns)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return data for the given index and role.

        Args:
            index: Model index identifying the cell.
            role: Qt item data role.

        Returns:
            Cell value appropriate for the requested role, or ``None``.
        """
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self._rows):
            return None
        if col < 0 or col >= len(self._columns):
            return None

        row_dict = self._rows[row]
        col_key = self._columns[col].key

        if role == Qt.ItemDataRole.DisplayRole:
            value = row_dict.get(col_key)
            if value is None:
                return ""
            return str(value)

        if role == Qt.ItemDataRole.DecorationRole:
            icon_key = f"{col_key}__icon"
            return row_dict.get(icon_key)

        if role == self.WidgetFactoryRole:
            factory_key = f"{col_key}__widget_factory"
            return row_dict.get(factory_key)

        if role == Qt.ItemDataRole.UserRole:
            return row_dict

        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return header data for the given section and orientation.

        Args:
            section: Column (horizontal) or row (vertical) index.
            orientation: Header orientation.
            role: Qt item data role.

        Returns:
            Column label for horizontal DisplayRole, otherwise ``None``.
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            if 0 <= section < len(self._columns):
                return self._columns[section].label
        return None

    def canFetchMore(  # noqa: N802
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> bool:
        """Return whether more rows can be fetched.

        Args:
            parent: Parent index; only the root (invalid) index may
                fetch more.

        Returns:
            ``True`` when more pages are available.
        """
        if parent.isValid():
            return False
        return self._has_more

    def fetchMore(  # noqa: N802
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> None:
        """Fetch the next page of rows.

        Args:
            parent: Parent index (unused; rows are fetched for root).
        """
        self._fetch_next_page()

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        """Set the active sort column and order, then reload data.

        Args:
            column: Zero-based index of the column to sort by. If out of
                range, the call is ignored.
            order: Sort order (ascending or descending).
        """
        if column < 0 or column >= len(self._columns):
            return
        self._sort_column = column
        self._sort_order = order
        self.reset_data()  # refetch page 0 using new sort

    # Public interface --------------------------------------------------------

    def set_page(self, page: int) -> None:
        """Reset the model and begin fetching from the given page.

        Args:
            page: 0-based page number to start from.
        """
        self.beginResetModel()
        self._rows = []
        self._has_more = True
        self._current_page = page
        self._is_fetching = False
        self._columns = self._explicit_columns or []
        self.endResetModel()
        self._fetch_next_page()

    def set_page_size(self, size: int) -> None:
        """Update the page size and reset the model from page 0.

        Args:
            size: New page size (rows per page).
        """
        self._page_size = size
        self.reset_data()

    def reset_data(self) -> None:
        """Reset the model and re-fetch from page 0."""
        self.beginResetModel()
        self._rows = []
        self._has_more = True
        self._current_page = 0
        self._is_fetching = False
        self._columns = self._explicit_columns or []
        self.endResetModel()
        self._fetch_next_page()

    # Internal helpers --------------------------------------------------------

    def _fetch_next_page(self) -> None:
        """Fetch the next page from the data source and append rows.

        Calls ``self._fetch_page(current_page, page_size)``.  On error
        the exception is logged and fetching is stopped.  Sets
        ``_has_more`` to ``False`` when the result is empty or shorter
        than the page size.

        A re-entrancy guard (``_is_fetching``) prevents recursive calls
        triggered by ``endInsertRows()`` signalling the view, which
        would otherwise call ``fetchMore`` / ``_fetch_next_page`` again
        before the current invocation finishes.
        """
        if self._is_fetching:
            return
        self._is_fetching = True
        try:
            try:
                sort_key = None
                if 0 <= self._sort_column < len(self._columns):
                    sort_key = self._columns[self._sort_column].key

                results = self._fetch_page(
                    self._current_page,
                    self._page_size,
                    sort_key,
                    self._sort_order == Qt.SortOrder.DescendingOrder,
                )
            except Exception:
                log.exception(
                    "Error fetching page %d (page_size=%d)",
                    self._current_page,
                    self._page_size,
                )
                self._has_more = False
                return

            if not results:
                self._has_more = False
                return

            if not self._columns and self._explicit_columns is None:
                self._columns = self._infer_columns(results[0])

            first_new = len(self._rows)
            last_new = first_new + len(results) - 1
            self.beginInsertRows(QModelIndex(), first_new, last_new)
            self._rows.extend(results)
            self.endInsertRows()

            if len(results) < self._page_size:
                self._has_more = False

            self._current_page += 1
        finally:
            self._is_fetching = False

    @staticmethod
    def _infer_columns(row: dict[str, Any]) -> list[TableColumn]:
        """Infer column definitions from a sample row dictionary.

        Keys ending with ``__icon`` or ``__widget_factory`` are excluded.

        Args:
            row: A representative row dictionary.

        Returns:
            List of inferred TableColumn instances.
        """
        columns: list[TableColumn] = []
        for key in row:
            if key.endswith("__icon") or key.endswith("__widget_factory"):
                continue
            label = key.replace("_", " ").title()
            columns.append(TableColumn(key=key, label=label))
        return columns


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TABLE_TEST_DATA: list[dict[str, Any]] = [
    {
        "name": f"Asset {i:03d}",
        "status": ["Active", "Inactive", "Review"][i % 3],
        "type": ["Model", "Texture", "Rig", "Animation"][i % 4],
        "author": ["Alice", "Bob", "Charlie", "Diana"][i % 4],
        "version": f"v{(i % 10) + 1:03d}",
    }
    for i in range(200)
]


def make_test_fetch(
    data: list[dict[str, Any]],
) -> Callable[[int, int, str | None, bool], list[dict[str, Any]]]:
    """Create a fetch_page callback from static data.

    Args:
        data: The full dataset to paginate.

    Returns:
        A callable suitable for PaginatedTableModel.
    """

    def _fetch(
        page: int,
        page_size: int,
        sort_key: str | None,
        descending: bool,
    ) -> list[dict[str, Any]]:
        print(
            f"Fetching page {page} (page_size={page_size}, "
            f"sort_key={sort_key!r}, descending={descending})"
        )
        rows = data
        if sort_key:
            rows = sorted(
                data,
                key=lambda r: (
                    r.get(sort_key) is None,
                    str(r.get(sort_key, "")),
                ),
                reverse=descending,
            )
        start = page * page_size
        end = start + page_size
        return rows[start:end]

    return _fetch


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    fetch = make_test_fetch(TABLE_TEST_DATA)
    model = PaginatedTableModel(fetch_page=fetch, page_size=25)
    print(f"Rows: {model.rowCount()}, Columns: {model.columnCount()}")
    print(f"Columns: {[c.label for c in model.columns]}")
    print(f"Has more: {model.canFetchMore(model.index(0, 0).parent())}")

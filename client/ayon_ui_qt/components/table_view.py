"""AYTable component module.

A flat, paginated table built on QTreeView with AYON styling.
"""

from __future__ import annotations

import logging
from typing import Any

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import (
    QItemSelection,
    QModelIndex,
    QRect,
    Qt,
    Signal,  # type: ignore
)
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
)
from qtpy.QtWidgets import QHeaderView, QTreeView, QWidget

from .. import get_ayon_style
from ..ayon_style import StyleData, TableItemDelegate
from ..variants import AYTableVariants
from .scroll_area import AYScrollBar
from .table_model import PaginatedTableModel

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon

log = logging.getLogger(__name__)


class AYTableHeader(QHeaderView):
    """Custom QHeaderView that paints sections directly, bypassing QSS.

    Draws header sections using QPainter to avoid interference from
    QStyleSheetStyle when a QSS stylesheet is loaded at the app level.

    Args:
        orientation: Header orientation (Horizontal or Vertical).
        parent: Optional parent widget.
        style_model: Style data model; if None falls back to super().
        variant: Visual style variant name.
    """

    def __init__(
        self,
        orientation: Qt.Orientation,
        parent: QWidget | None = None,
        style_model: StyleData | None = None,
        variant: str = "default",
    ) -> None:
        super().__init__(orientation, parent)
        self._style_model = style_model
        self._variant_str = variant
        # self.setSortIndicatorShown(True)

    def paintSection(
        self,
        painter: QPainter,
        rect: QRect,
        logical_index: int,
    ) -> None:
        """Paint a single header section directly with QPainter.

        Falls back to the base implementation when no style model is
        available.

        Args:
            painter: The painter to draw with.
            rect: The bounding rectangle for this section.
            logical_index: The logical index of the section.
        """
        if self._style_model is None:
            super().paintSection(painter, rect, logical_index)
            return

        tbl_style = self._style_model.get_style("AYTable", self._variant_str)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setClipRect(rect)

        # draw cell
        painter.setBrush(
            QBrush(QColor(tbl_style.get("header-background-color", "#272d35")))
        )
        painter.setPen(
            QPen(
                QColor(tbl_style.get("header-border-color", "#41474d")),
                tbl_style.get("header-border-width", 1),
            )
        )
        painter.drawRect(rect)

        # Label text
        padding = tbl_style.get("header-padding", [4, 8])
        h_pad = int(padding[1]) if len(padding) > 1 else 8
        v_pad = int(padding[0])
        text_rect = rect.adjusted(h_pad, v_pad, -h_pad, -v_pad)

        text_color = QColor(tbl_style.get("header-color", "#c1c7ce"))
        painter.setPen(text_color)

        font = painter.font()
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)

        model = self.model()
        if model is not None:
            label = model.headerData(
                logical_index,
                self.orientation(),
                Qt.ItemDataRole.DisplayRole,
            )
            if label is not None:
                painter.drawText(
                    text_rect,
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    str(label),
                )

        # Sort indicator
        if (
            self.isSortIndicatorShown()
            and self.sortIndicatorSection() == logical_index
        ):
            order = self.sortIndicatorOrder()
            icon_name = tbl_style.get("header-sort-indicator-icon", None)
            if icon_name is not None:
                icon = get_icon(
                    icon_name,
                    color=tbl_style.get(
                        "header-sort-indicator-color", "#ffffff"
                    ),
                )
                size = tbl_style.get("header-sort-indicator-size", 16)
                margin = (rect.height() - size) / 2.0
                pixmap = icon.pixmap(size, size)
                target = rect.adjusted(
                    max(rect.width() - (size + h_pad), 0),
                    margin,
                    -h_pad,
                    -margin,
                )

                if order == Qt.SortOrder.AscendingOrder:
                    painter.save()
                    center = target.center()
                    painter.translate(center)
                    painter.rotate(180)
                    painter.translate(-center)
                    painter.drawPixmap(target, pixmap)
                    painter.restore()
                else:
                    painter.drawPixmap(target, pixmap)

            else:
                arrow = "▲" if order == Qt.SortOrder.AscendingOrder else "▼"
                painter.drawText(
                    text_rect,
                    Qt.AlignmentFlag.AlignVCenter
                    | Qt.AlignmentFlag.AlignRight,
                    arrow,
                )

        painter.restore()


class AYTable(QTreeView):
    """AYON-styled flat table view.

    Subclasses QTreeView in flat-table mode (no tree indentation or
    expand toggles). Uses AYONStyle for all painting, a custom item
    delegate that draws directly bypassing any parent QSS, and
    AYScrollBar instances for scrollbars.

    The header is visible and styled via TableHeaderDrawer.

    When a PaginatedTableModel is set, cells that provide a
    WidgetFactoryRole value get an embedded QWidget via
    setIndexWidget().

    Args:
        parent: Optional parent widget.
        variant: Visual style variant controlling colours.
    """

    Variants = AYTableVariants
    selection_changed = Signal(QItemSelection, QItemSelection)

    def __init__(
        self,
        parent: QWidget | None = None,
        variant: AYTableVariants = AYTableVariants.Default,
    ) -> None:
        self._variant_str: str = variant.value

        super().__init__(parent)

        style = get_ayon_style()
        self.setStyle(style)

        # Custom header — paints sections directly, bypassing QSS.
        header = AYTableHeader(
            Qt.Orientation.Horizontal,
            parent=self,
            style_model=style.model,
            variant=self._variant_str,
        )
        self.setHeader(header)

        # Self-contained: do not inherit parent background.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        self.viewport().setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, False
        )
        self._sync_viewport_palette()

        # Custom item delegate — paints cells directly.
        delegate = TableItemDelegate(
            parent=self,
            style_model=style.model,
            variant=self._variant_str,
        )
        self.setItemDelegate(delegate)

        # Styled scrollbars.
        vsb = AYScrollBar(Qt.Orientation.Vertical, self)
        self.setVerticalScrollBar(vsb)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        hsb = AYScrollBar(Qt.Orientation.Horizontal, self)
        self.setHorizontalScrollBar(hsb)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Flat table — no tree features.
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.setIndentation(0)

        # Header visible.
        self.setHeaderHidden(False)

        # Selection behaviour.
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)

        # No default frame — drawn manually in paintEvent.
        self.setFrameShape(QTreeView.Shape.NoFrame)

        # Alternating row colours disabled — delegate handles it.
        self.setAlternatingRowColors(False)

        # Track model connections for cleanup.
        self._model_connections: list[QtCore.QMetaObject.Connection] = []

    def _sync_viewport_palette(self) -> None:
        """Apply the variant background colour to the viewport."""
        style = get_ayon_style()
        tbl_style = style.model.get_style("AYTable", self._variant_str)
        bg = QColor(tbl_style.get("background-color", "#252a31"))
        p = self.viewport().palette()
        p.setColor(QPalette.ColorRole.Base, bg)
        p.setColor(QPalette.ColorRole.Window, bg)
        self.viewport().setPalette(p)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the outer container background before items.

        Args:
            event: The paint event.
        """
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        style = get_ayon_style()
        tbl_style = style.model.get_style("AYTable", self._variant_str)
        bg = QColor(tbl_style.get("background-color", "#252a31"))
        painter.fillRect(self.viewport().rect(), bg)
        painter.end()

        super().paintEvent(event)

    def setModel(self, model: QtCore.QAbstractItemModel | None) -> None:
        """Set the data model and configure header and widgets.

        Args:
            model: The data model to display.
        """
        # Disconnect previous model signals.
        for conn in self._model_connections:
            try:
                self.model().disconnect(conn)
            except (RuntimeError, TypeError):
                pass
        self._model_connections.clear()

        super().setModel(model)

        if model is None:
            return

        # Configure header from column width hints.
        self._configure_header(model)

        # Install embedded widgets for existing rows.
        self._install_widgets_for_range(0, model.rowCount() - 1)

        # Connect to rowsInserted for lazy-loaded rows.
        conn = model.rowsInserted.connect(self._on_rows_inserted)
        if conn is not None:
            self._model_connections.append(conn)

    def _configure_header(self, model: QtCore.QAbstractItemModel) -> None:
        """Set up header section sizes from model column hints.

        Args:
            model: The data model.
        """
        header = self.header()
        if header is None:
            return

        # Set header height from style.
        style = get_ayon_style()
        tbl_style = style.model.get_style("AYTable", self._variant_str)
        header_height = int(tbl_style.get("header-height", 36))
        header.setFixedHeight(header_height)

        # Disable header highlight on selection.
        header.setHighlightSections(False)

        col_count = model.columnCount()
        if col_count == 0:
            return

        # Check if model provides column width hints.
        has_hints = False
        if isinstance(model, PaginatedTableModel):
            for col_def in model.columns:
                if col_def.width > 0:
                    has_hints = True
                    break

        if has_hints and isinstance(model, PaginatedTableModel):
            for i, col_def in enumerate(model.columns):
                if i >= col_count:
                    break
                if col_def.width > 0:
                    header.resizeSection(i, col_def.width)
                    header.setSectionResizeMode(
                        i,
                        QHeaderView.ResizeMode.Interactive,
                    )
                else:
                    header.setSectionResizeMode(
                        i,
                        QHeaderView.ResizeMode.Stretch,
                    )
        else:
            # Default: stretch all columns equally.
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Enable sorting.
        self.setSortingEnabled(True)
        header.setSortIndicatorShown(True)

    def _on_rows_inserted(
        self,
        parent: QModelIndex,
        first: int,
        last: int,
    ) -> None:
        """Install embedded widgets for newly inserted rows.

        Args:
            parent: Parent index (unused for flat tables).
            first: First inserted row index.
            last: Last inserted row index.
        """
        self._install_widgets_for_range(first, last)

    def _install_widgets_for_range(
        self, first_row: int, last_row: int
    ) -> None:
        """Scan a row range and install embedded widgets.

        For each cell in the range, checks the WidgetFactoryRole.
        If a callable is returned, it is called with
        ``(model_index, self)`` and the resulting widget is set
        via ``setIndexWidget()``.

        Args:
            first_row: First row to scan (inclusive).
            last_row: Last row to scan (inclusive).
        """
        model = self.model()
        if model is None:
            return

        col_count = model.columnCount()
        for row in range(first_row, last_row + 1):
            for col in range(col_count):
                idx = model.index(row, col)
                factory = idx.data(PaginatedTableModel.WidgetFactoryRole)
                if factory is not None and callable(factory):
                    try:
                        widget = factory(idx, self)
                    except Exception:
                        log.exception(
                            "Widget factory failed for row=%d col=%d",
                            row,
                            col,
                        )
                        continue
                    if isinstance(widget, QWidget):
                        self.setIndexWidget(idx, widget)

    def selectionChanged(
        self,
        selected: QItemSelection,
        deselected: QItemSelection,
    ) -> None:
        """Override to emit a public signal on selection change.

        Args:
            selected: Newly selected items.
            deselected: Newly deselected items.
        """
        super().selectionChanged(selected, deselected)
        self.selection_changed.emit(selected, deselected)


# =============================================================================
# __main__ – visual test harness
# =============================================================================

if __name__ == "__main__":
    from typing import Callable

    from qtpy import QtWidgets

    from ..tester import Style, test
    from .layouts import AYVBoxLayout
    from .table_model import (
        TABLE_TEST_DATA,
        PaginatedTableModel,
        TableColumn,
        make_test_fetch,
    )

    def _make_button_factory(
        label: str,
    ) -> Callable[[QModelIndex, QWidget], QWidget]:
        """Create a widget factory that returns a small button.

        Args:
            label: Button text.

        Returns:
            A callable suitable for WidgetFactoryRole.
        """

        def _factory(index: QModelIndex, parent: QWidget) -> QWidget:
            from .buttons import AYButton

            btn = AYButton(
                label,
                variant=AYButton.Variants.Text,
                parent=parent,
            )
            btn.setFixedHeight(28)
            btn.clicked.connect(
                lambda: print(f"Button clicked: row={index.row()}")
            )
            return btn

        return _factory

    # Build test data with a widget column
    _WIDGET_TEST_DATA: list[dict[str, Any]] = []
    for i, row in enumerate(TABLE_TEST_DATA[:60]):
        new_row = dict(row)
        new_row["actions"] = ""
        new_row["actions__widget_factory"] = _make_button_factory("Open")
        _WIDGET_TEST_DATA.append(new_row)

    def _build() -> QtWidgets.QWidget:
        """Build test UI with one AYTable per variant."""
        container = QtWidgets.QWidget()
        root_lyt = AYVBoxLayout(container, margin=8, spacing=8)

        for variant in AYTable.Variants:
            label = QtWidgets.QLabel(f"variant: {variant.value}")
            label.setFixedHeight(20)
            root_lyt.addWidget(label)

            fetch = make_test_fetch(_WIDGET_TEST_DATA)
            columns = [
                TableColumn("name", "Name", width=150),
                TableColumn("status", "Status", width=80),
                TableColumn("type", "Type", width=100),
                TableColumn("author", "Author", width=100),
                TableColumn("version", "Version", width=70),
                TableColumn("actions", "Actions", width=80),
            ]
            model = PaginatedTableModel(
                fetch_page=fetch,
                columns=columns,
                page_size=20,
            )

            table = AYTable(variant=variant)
            table.setModel(model)
            table.setMinimumHeight(200)
            root_lyt.addWidget(table)

            table.selection_changed.connect(
                lambda sel, desel: print(
                    f"selection changed: {[i.data() for i in sel.indexes()]}"
                )
            )

        container.setMinimumWidth(700)
        return container

    test(_build, style=Style.AyonStyleOverCSS)

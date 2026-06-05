"""Item view drawers: ItemViewItemDrawer, TreeViewItemDelegate,
TableItemDelegate."""
from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QRect, Qt
from qtpy.QtGui import QBrush, QColor, QIcon, QPainter, QPen
from qtpy.QtWidgets import (
    QStyle,
    QStyleOption,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QWidget,
)

from ..components.style_mixin import StyleMixin
from ._utils import enum_to_str, get_icon

if TYPE_CHECKING:
    from ..style import AYONStyle, StyleData


class ItemViewItemDrawer:
    """Drawer for item view items using QStyledItemDelegate."""

    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def base_class(self):
        return {"QStyledItemDelegate": QStyledItemDelegate}

    def register_drawers(self):
        return {
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_ItemViewItem,
                "QStyledItemDelegate",
            ): self.draw_item_view_item,
        }

    def get_item_view_variant(self, widget: QWidget | None) -> str:
        """Extract item view variant from widget properties."""
        if widget is None:
            return "default"
        if hasattr(widget, "itemDelegate"):
            delegate = widget.itemDelegate()
            if hasattr(delegate, "_variant_str"):
                return delegate._variant_str
        return "default"

    def get_item_view_style(
        self,
        widget: QWidget | None,
        option: QStyleOptionViewItem,
    ) -> tuple[dict, str]:
        """Get the appropriate style dictionary for the widget's variant
        and state.

        Args:
            widget: The parent widget containing the item view.
            option: The style option containing state flags.

        Returns:
            A tuple of (style dictionary, state string).
        """
        variant = self.get_item_view_variant(widget)

        wstate = "base"
        is_checked = option.checkState == Qt.CheckState.Checked
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if is_checked:
            wstate = "checked"
        elif is_hovered:
            wstate = "hover"

        style = self.model.get_style("QStyledItemDelegate", variant, wstate)
        style.set_context(widget)

        return style, wstate

    def draw_item_view_item(
        self,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None,
    ) -> None:
        """Paint a filter item with checkbox indicator.

        Hover and checked states are handled independently:
        - Background color comes from hover state when hovered
        - Checkbox background and text color come from checked state
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # For QStyleOptionViewItem, we need to check different properties
        if not isinstance(option, QStyleOptionViewItem):
            painter.restore()
            return

        # Determine hover and checked states independently
        is_checked = option.checkState == Qt.CheckState.Checked
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        text = option.text

        # Get variant for style lookups
        variant = self.get_item_view_variant(widget)

        # Get all necessary styles in a single call
        styles = self.model.get_styles(
            "QStyledItemDelegate", variant, ["base", "hover", "checked"]
        )
        base_style = styles["base"]
        hover_style = styles["hover"]
        checked_style = styles["checked"]

        # Constants from base style data
        checkbox_size = base_style.get("checkbox-size", 16)
        checkbox_margin = base_style.get("checkbox-margin", 8)
        text_padding = base_style.get("text-padding", 12)
        border_radius = base_style.get("border-radius", 2)

        # Background: use hover style if hovered, regardless of checked state
        if is_hovered:
            bg_color = QColor(
                hover_style.get(
                    "background-color",
                    base_style.get("background-color", "transparent"),
                )
            )
        else:
            bg_color = QColor(
                base_style.get("background-color", "transparent")
            )

        # Text color: use checked style if checked, else base
        if is_checked:
            text_color = QColor(
                checked_style.get(
                    "color", base_style.get("color", "#8b9198")
                )
            )
        else:
            text_color = QColor(base_style.get("color", "#8b9198"))

        # Checkbox background: use checked style if checked, else base
        if is_checked:
            checkbox_bg_color = QColor(
                checked_style.get(
                    "checkbox-background-color",
                    base_style.get("checkbox-background-color", "#424a57"),
                )
            )
        else:
            checkbox_bg_color = QColor(
                base_style.get("checkbox-background-color", "#424a57")
            )

        # Draw background if hovered
        if is_hovered:
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(option.rect)

        # Calculate checkbox rect - positioned on right side
        cb_rect = QRect(
            option.rect.right() - checkbox_size - checkbox_margin,
            option.rect.center().y() - checkbox_size // 2,
            checkbox_size,
            checkbox_size,
        )

        # Draw checkbox background
        painter.setBrush(QBrush(checkbox_bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(cb_rect, border_radius, border_radius)

        # Draw X mark if checked
        if is_checked:
            icon = get_icon("close", color="#000000")
            icon_rect = cb_rect.adjusted(2, 2, -2, -2)
            icon.paint(painter, icon_rect)

        # Draw text
        painter.setPen(QPen(text_color))
        text_rect = option.rect.adjusted(
            text_padding,
            0,
            -(checkbox_size + checkbox_margin * 2),
            0,
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )

        painter.restore()


class TreeViewItemDelegate(StyleMixin, QtWidgets.QStyledItemDelegate):
    """Item delegate for AYTreeView that paints directly, bypassing QSS.

    Reads style data from the QTreeView style entry to draw item
    backgrounds (hover, selected) and text/icons.  The paint() method
    uses raw QPainter calls so that a parent-level QStyleSheet cannot
    intercept and override the colours.

    Args:
        parent: The parent widget (expected to be an AYTreeView instance).
        style_model: StyleData instance providing colour/dimension data.
        variant: The variant string used to look up the correct style.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        style_model: StyleData | None = None,
        variant: str = "default",
    ) -> None:
        super().__init__(parent)
        self._style_model = style_model
        self._variant_str = variant
        self._icon_cache: dict[str, QIcon] = {}

    def _tv_styles(self) -> dict[str, dict]:
        """Return *base*, *hover* and *selected* style dicts at once."""
        if self._style_model is None:
            return {"base": {}, "hover": {}, "selected": {}}
        return self._style_model.get_styles(
            "QTreeView",
            self._variant_str,
            ["base", "hover", "selected"],
        )

    def initStyleOption(
        self,
        option: QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Initialize the style option with the default implementation, then
        override any properties needed for our custom painting.

        Args:
            option: The style option to initialize.
            index: The model index of the item.
        """
        super().initStyleOption(option, index)
        option.font = self.font()
        option.fontMetrics = self.fontMetrics()

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QSize:
        """Return a fixed row height from the style data.

        Args:
            option: The style option for the item.
            index: The model index of the item.

        Returns:
            The size hint for the item.
        """
        if self._style_model:
            style = self._style_model.get_style(
                "QTreeView", self._variant_str
            )
            h = int(style.get("item-height", 28))
        else:
            h = 28
        return QtCore.QSize(option.rect.width(), h)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Paint a tree-view item directly, bypassing QStyle completely.

        Args:
            painter: The QPainter to use.
            option: The style option for the item.
            index: The model index of the item.
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        state = opt.state
        is_selected = bool(state & QStyle.StateFlag.State_Selected)
        is_hovered = bool(state & QStyle.StateFlag.State_MouseOver)

        styles = self._tv_styles()
        base_style = styles["base"]
        hover_style = styles["hover"]
        selected_style = styles["selected"]

        item_padding = base_style.get("item-padding", [4, 8])
        icon_text_spacing = int(base_style.get("icon-text-spacing", 6))

        # --- background ------------------------------------------------
        if is_selected:
            bg_color = QColor(
                selected_style.get(
                    "background-color",
                    base_style.get("background-color", "transparent"),
                )
            )
        elif is_hovered:
            bg_color = QColor(
                hover_style.get(
                    "background-color",
                    base_style.get("background-color", "transparent"),
                )
            )
        else:
            bg_color = QColor(
                base_style.get("background-color", "transparent")
            )

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(opt.rect)

        # --- text colour -----------------------------------------------
        if is_selected:
            text_color = QColor(
                selected_style.get(
                    "color",
                    base_style.get("color", "#f4f5f5"),
                )
            )
        else:
            text_color = QColor(base_style.get("color", "#f4f5f5"))

        # disabled dimming
        if not (state & QStyle.StateFlag.State_Enabled):
            text_color.setAlpha(
                int(
                    text_color.alpha()
                    * base_style.get("disabled-opacity", 0.5)
                )
            )

        # --- icon + text layout ----------------------------------------
        content_rect = QRect(opt.rect).adjusted(
            item_padding[1],
            item_padding[0],
            -item_padding[1],
            -item_padding[0],
        )
        content_left = content_rect.left()

        if not opt.icon.isNull():
            icon_size = opt.decorationSize
            icon_rect = QRect(
                content_left,
                opt.rect.center().y() - icon_size.height() // 2,
                icon_size.width(),
                icon_size.height(),
            )
            mode = (
                QIcon.Mode.Normal
                if state & QStyle.StateFlag.State_Enabled
                else QIcon.Mode.Disabled
            )
            opt.icon.paint(
                painter,
                icon_rect,
                Qt.AlignmentFlag.AlignCenter,
                mode,
            )
            content_left = icon_rect.right() + icon_text_spacing

        if opt.text:
            text_rect = QRect(opt.rect)
            text_rect.setLeft(content_left)
            text_rect.setRight(content_rect.right())
            painter.setPen(text_color)
            painter.setFont(opt.font)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                opt.text,
            )

        painter.restore()


class TableItemDelegate(StyleMixin, QtWidgets.QStyledItemDelegate):
    """Item delegate for AYTableView that paints cells directly,
    bypassing QSS.

    Reads style data from the AYTableView style entry to draw cell
    backgrounds (hover, selected) and text/icons.

    Columns that carry a ``widget_factory`` on their :class:`TableColumn`
    definition get a persistent editor via :meth:`createEditor`.  Qt calls
    :meth:`setEditorData` both when the editor is first opened and
    automatically whenever the model emits ``dataChanged`` for that index,
    so server-push updates reach live widgets without extra wiring.
    User edits are written back via :meth:`setModelData`.

    Args:
        parent: The parent widget (expected to be an AYTableView instance).
        style_model: StyleData instance providing colour/dimension data.
        variant: The variant string used to look up the correct style.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        style_model: StyleData | None = None,
        variant: str = "default",
    ) -> None:
        super().__init__(parent)
        self._style_model = style_model
        self._variant_str = variant

    def _table_styles(self) -> dict[str, dict]:
        """Return base, hover and selected style dicts at once."""
        if self._style_model is None:
            raise ValueError("TableItemDelegate requires a style model")
        return self._style_model.get_styles(
            "AYTableView",
            self._variant_str,
            ["base", "hover", "selected"],
        )

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QSize:
        """Return a fixed row height from the style data."""
        if self._style_model:
            style = self._style_model.get_style(
                "AYTableView", self._variant_str
            )
            h = int(style.get("item-height", 32))
        else:
            h = 32
        return QtCore.QSize(option.rect.width(), h)

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QWidget | None:
        """Return a widget for widget-factory columns; None otherwise.

        The returned widget is kept open permanently by the view via
        ``openPersistentEditor``.  Qt calls :meth:`setEditorData` once
        here and again automatically on every ``dataChanged`` emission
        for this index, so server-push updates reach the widget for free.

        Args:
            parent: Parent widget (viewport).
            option: Style option for the cell.
            index: Model index identifying the cell.

        Returns:
            A QWidget created by the column's ``widget_factory``, or
            ``None`` if the column has no factory.
        """
        from ..components.table_model import PaginatedTableModel

        src_model = index.model()
        if hasattr(src_model, "sourceModel"):
            src_model = src_model.sourceModel()
        if not isinstance(src_model, PaginatedTableModel):
            return None
        col = index.column()
        cols = src_model.columns
        if col < 0 or col >= len(cols):
            return None
        factory = cols[col].widget_factory
        if factory is None:
            return None
        return factory(index, parent)  # type: ignore[return-value]

    def setEditorData(
        self,
        editor: QWidget,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Push current model data into *editor* when the model changes.

        Called by Qt when the persistent editor is first opened and
        automatically whenever the model emits ``dataChanged`` for this
        index — server-push updates propagate to live widgets for free.

        This default implementation is a no-op suited to action widgets
        (e.g. buttons) that do not reflect model data.  Override or
        replace this method for data-reflecting widgets: read
        ``index.data(Qt.DisplayRole)`` (or a custom role) and push the
        value into *editor*.

        Args:
            editor: The persistent editor widget.
            index: Model index whose data changed.
        """

    def setModelData(
        self,
        editor: QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Write committed user input from *editor* back to *model*.

        Called by Qt when the user commits an edit (e.g. presses Enter
        or the editor loses focus).

        This default implementation is a no-op suited to action widgets
        that do not write back to the model.  For interactive widget
        columns, read the current value from *editor* and call
        ``model.setData(index, value, Qt.EditRole)`` to propagate the
        change upstream (e.g. to the server).

        Args:
            editor: The persistent editor widget.
            model: The data model.
            index: Model index to write to.
        """

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Paint a table cell directly, bypassing QStyle."""
        # Skip painting for cells covered by a persistent editor widget.
        from ..components.table_model import PaginatedTableModel

        src_model = index.model()
        if hasattr(src_model, "sourceModel"):
            src_model = src_model.sourceModel()
        if isinstance(src_model, PaginatedTableModel):
            col = index.column()
            cols = src_model.columns
            if 0 <= col < len(cols) and cols[col].widget_factory is not None:
                return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        state = opt.state
        is_selected = bool(state & QStyle.StateFlag.State_Selected)
        is_hovered = bool(state & QStyle.StateFlag.State_MouseOver)
        # State_MouseOver is only set for the cell directly under the cursor.
        # When hovering the branch-indicator column, other cells in the same
        # row don't receive it.  Fall back to a y-coordinate check so the
        # entire row highlights consistently.
        if not is_hovered and not is_selected:
            _view = self.parent()
            if type(_view).__name__ == "AYTableView" and hasattr(
                _view, "viewport"
            ):
                _cursor = _view.viewport().mapFromGlobal(QtGui.QCursor.pos())
                is_hovered = opt.rect.top() <= _cursor.y() < opt.rect.bottom()
        is_item = not bool(state & QStyle.StateFlag.State_Children)

        styles = self._table_styles()
        base_style = styles["base"]
        hover_style = styles["hover"]
        selected_style = styles["selected"]

        item_padding = base_style.get("item-padding", [4, 8])
        icon_text_spacing = int(base_style.get("icon-text-spacing", 6))

        # --- background ---
        if is_selected:
            bg_color = QColor(
                selected_style.get(
                    "background-color",
                    base_style.get("background-color", "transparent"),
                )
            )
        elif is_hovered:
            bg_color = QColor(
                hover_style.get(
                    "background-color",
                    base_style.get("background-color", "transparent"),
                )
            )
        else:
            bg_color = QColor(
                base_style.get(
                    "background-color-item" if is_item else "background-color",
                    "transparent",
                )
            )

        painter.setBrush(QBrush(bg_color))

        pen_width = base_style.get("border-width", 0)
        if pen_width > 0:
            pen_color = QColor(base_style.get("border-color", "#000000"))
            pen = QPen(pen_color)
            pen.setWidth(pen_width)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        column = index.column()
        if column == 1:
            painter.fillRect(opt.rect, bg_color)
            painter.drawPolyline(
                [
                    opt.rect.topLeft(),
                    opt.rect.topRight(),
                    opt.rect.bottomRight(),
                    opt.rect.bottomLeft(),
                ]
            )
        else:
            painter.drawRect(opt.rect)

        # --- text colour ---
        index_color = index.data(role=Qt.ItemDataRole.ForegroundRole)
        if is_selected:
            text_color = (
                index_color.color()
                if index_color
                else QColor(base_style.get("color", "#f4f5f5"))
            )
        else:
            text_color = (
                index_color.color()
                if index_color
                else QColor(base_style.get("color", "#f4f5f5"))
            )

        # disabled dimming
        if not (state & QStyle.StateFlag.State_Enabled):
            text_color.setAlpha(
                int(
                    text_color.alpha()
                    * base_style.get("disabled-opacity", 0.5)
                )
            )

        # --- icon + text layout ---
        content_rect = QRect(opt.rect).adjusted(
            item_padding[1],
            item_padding[0],
            -item_padding[1],
            -item_padding[0],
        )
        content_left = content_rect.left()

        if not opt.icon.isNull():
            icon_size = opt.decorationSize
            icon_rect = QRect(
                content_left,
                opt.rect.center().y() - icon_size.height() // 2,
                icon_size.width(),
                icon_size.height(),
            )
            mode = (
                QIcon.Mode.Normal
                if state & QStyle.StateFlag.State_Enabled
                else QIcon.Mode.Disabled
            )
            opt.icon.paint(
                painter,
                icon_rect,
                Qt.AlignmentFlag.AlignCenter,
                mode,
            )
            content_left = icon_rect.right() + icon_text_spacing

        if opt.text:
            text_rect = QRect(opt.rect)
            text_rect.setLeft(content_left)
            text_rect.setRight(content_rect.right())
            painter.setPen(text_color)
            painter.setFont(self.font())
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                opt.text,
            )

        painter.restore()

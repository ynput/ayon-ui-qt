"""ComboBox drawers: ComboBoxItemDelegate and ComboBoxDrawer."""
from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import QRect, Qt
from qtpy.QtGui import QBrush, QColor, QIcon, QPainter, QPalette
from qtpy.QtWidgets import (
    QComboBox,
    QHeaderView,
    QStyle,
    QStyleOption,
    QStyleOptionComboBox,
    QWidget,
)

from ..components.style_mixin import StyleMixin
from ._utils import do_nothing, enum_to_str, get_icon

if TYPE_CHECKING:
    from ..style import AYONStyle, StyleData


class ComboBoxItemDelegate(StyleMixin, QtWidgets.QStyledItemDelegate):
    def __init__(
        self,
        parent=None,
        padding: int = 4,
        icon_size: int = 16,
        style_model: StyleData | None = None,
    ) -> None:
        super().__init__(parent)
        self._padding = padding
        self._icon_size = icon_size
        self._icon_text_spacing = 8
        self._style_model = style_model
        self._icon_cache: dict[str, QIcon] = {}

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QSize:
        """Calculate size hint including padding."""

        # Calculate text dimensions
        font_metrics = option.fontMetrics
        text_size = font_metrics.size(0, option.text)

        # Calculate content dimensions
        content_width = text_size.width()
        content_height = max(text_size.height(), self._icon_size)

        # Add icon space if present
        if option.icon:
            content_width += self._icon_size + self._icon_text_spacing

        # Add padding to get total size
        total_width = content_width + self._padding + self._padding
        total_height = content_height + self._padding + self._padding

        # Ensure minimum height
        total_height = max(total_height, 32)

        return QtCore.QSize(total_width, total_height)

    def _get_icon(
        self, fg: QColor, bg: QColor, icon_name: str, invert: bool = True
    ) -> QIcon:
        """Get icon from cache or create new one."""
        key = f"{icon_name}-{fg.name()}-{bg.name()}-{invert}"
        if key not in self._icon_cache:
            self._icon_cache[key] = get_icon(
                icon_name,
                bg if invert else fg,
            )
        return self._icon_cache[key]

    def initStyleOption(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Initialize style option and apply any custom font from model."""
        super().initStyleOption(option, index)
        option.font = self.font()
        option.fontMetrics = self.fontMetrics()

    def paint(
        self,
        painter: QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Paint combo-box items directly, bypassing QStyle.

        This avoids QStyleSheetStyle intercepting drawPrimitive /
        drawControl calls when an app-level QSS is active.
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Build a copy of the option with text/palette configured
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        # --- resolve colours -----------------------------------
        fg_data = index.data(Qt.ItemDataRole.ForegroundRole)
        bg_data = index.data(Qt.ItemDataRole.BackgroundRole)

        cb = self.parent()

        # Menu background from the AYON style JSON
        if self._style_model:
            cb_style = self._style_model.get_style("QComboBox")
            cb_style.set_context(cb)
            menu_bg = QColor(cb_style.get("menu-background-color", "#1c2026"))
        else:
            menu_bg = opt.palette.color(
                QPalette.ColorGroup.Active,
                QPalette.ColorRole.Window,
            )

        highlight_color = opt.palette.color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Dark
        )

        state = opt.state
        is_selected = bool(state & QStyle.StateFlag.State_Selected)
        is_hovered = (
            bool(state & QStyle.StateFlag.State_MouseOver) and not is_selected
        )

        if fg_data and bg_data:
            fg = fg_data.color()
            bg = bg_data.color()

            if is_hovered:
                bg_color = highlight_color
                text_color = fg
            elif is_selected:
                bg_color = fg
                text_color = bg
                # Regenerate icon with the swapped text_color
                icon_name = (
                    index.data(cb.model().IconNameRole)
                    if hasattr(cb.model(), "IconNameRole")
                    else None
                )
                if icon_name:
                    opt.icon = self._get_icon(
                        text_color, bg_color, icon_name, False
                    )
            else:
                bg_color = menu_bg
                text_color = fg
        else:
            # Fallback for items without FG/BG data
            if is_hovered or is_selected:
                bg_color = highlight_color
                text_color = opt.palette.color(
                    QPalette.ColorRole.HighlightedText
                )
            else:
                bg_color = menu_bg
                text_color = opt.palette.color(QPalette.ColorRole.Text)

        # --- draw background -----------------------------------
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(opt.rect)

        # --- draw icon -----------------------------------------
        content_left = opt.rect.left() + self._padding
        if not opt.icon.isNull():
            icon_rect = QRect(
                content_left,
                opt.rect.center().y() - self._icon_size // 2,
                self._icon_size,
                self._icon_size,
            )
            mode = (
                QIcon.Mode.Normal
                if opt.state & QStyle.StateFlag.State_Enabled
                else QIcon.Mode.Disabled
            )
            icon_state = (
                QIcon.State.On
                if (is_hovered or is_selected)
                else QIcon.State.Off
            )
            opt.icon.paint(
                painter,
                icon_rect,
                Qt.AlignmentFlag.AlignCenter,
                mode,
                icon_state,
            )
            content_left = icon_rect.right() + self._icon_text_spacing

        # --- draw text -----------------------------------------
        if opt.text:
            text_rect = QRect(opt.rect)
            text_rect.setLeft(content_left)
            text_rect.setRight(text_rect.right() - self._padding)
            painter.setPen(text_color)
            painter.setFont(opt.font)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                opt.text,
            )

        painter.restore()


class ComboBoxDrawer:
    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def _super(self):
        """Return proxy for calling QCommonStyle methods on style_inst."""
        from ..style import AYONStyle as _AYONStyle

        return super(_AYONStyle, self.style_inst)

    @property
    def base_class(self):
        return {"QComboBox": QComboBox}

    def register_drawers(self):
        return {
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_ComboBoxLabel,
                "QComboBox",
            ): self.draw_label,
            enum_to_str(
                QStyle.ComplexControl,
                QStyle.ComplexControl.CC_ComboBox,
                "QComboBox",
            ): self.draw_box,
            enum_to_str(
                QStyle.PrimitiveElement,
                QStyle.PrimitiveElement.PE_PanelItemViewItem,
                "QFrame",
            ): self.draw_panel_item_view_item,
            enum_to_str(
                QStyle.PrimitiveElement,
                QStyle.PrimitiveElement.PE_FrameFocusRect,
                "QFrame",
            ): do_nothing,
        }

    def register_sizers(self):
        return {
            enum_to_str(
                QStyle.ContentsType,
                QStyle.ContentsType.CT_ComboBox,
                "QComboBox",
            ): self.combobox_size,
        }

    def get_fg_bg_colors(
        self,
        opt: QtWidgets.QStyleOptionComplex,
        w: QComboBox,
    ) -> tuple[QColor, QColor]:
        bg_color = opt.palette.color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Base
        )
        fg_color = opt.palette.color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText
        )

        inverted = getattr(w, "_inverted", False)
        current_index = w.currentIndex()
        if current_index >= 0:
            item_color = w.itemData(
                current_index, QtCore.Qt.ItemDataRole.ForegroundRole
            )
            if item_color is not None:
                item_color = item_color.color()
                fg_color = bg_color if inverted else item_color
                bg_color = item_color if inverted else bg_color

        return fg_color, bg_color

    def draw_box(
        self,
        opt: QtWidgets.QStyleOptionComplex,
        p: QPainter,
        w: QComboBox | None = None,
    ):
        if not isinstance(w, QComboBox):
            return

        _style = self.model.get_style(
            "QComboBox", variant=getattr(w, "_variant_str", None)
        )
        _style.set_context(w)
        style_bg_color = _style.get("background-color", None)
        opt.palette.setBrush(
            QPalette.ColorRole.Base,
            QColor(style_bg_color)
            if style_bg_color
            else self.model.base_palette.base(),
        )
        _radius = _style.get("border-radius", 0)

        if not w.isEditable():
            fg_color, bg_color = self.get_fg_bg_colors(opt, w)

            # Paint background with status color
            rect = opt.rect
            p.save()
            p.setBrush(QBrush(bg_color))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, _radius, _radius)
            p.restore()

            # set pen for text drawing
            p.setPen(fg_color)
        else:
            # editable combobox - IMPLEMENT ME
            self._super.drawComplexControl(
                QStyle.ComplexControl.CC_ComboBox, opt, p, w
            )

    def draw_label(
        self,
        opt: QStyleOptionComboBox,
        p: QPainter,
        w: QWidget,
    ):
        if not isinstance(w, QComboBox):
            return

        _style = self.model.get_style(
            "QComboBox", variant=getattr(w, "_variant_str", None)
        )
        _style.set_context(w)
        icon_padding = _style.get("icon-padding", [4, 4])
        text_padding = _style.get("text-padding", [1, 1])

        fg_color, bg_color = self.get_fg_bg_colors(opt, w)

        base_cls = self._super
        edit_rect = base_cls.subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            opt,
            QStyle.SubControl.SC_ComboBoxEditField,
            w,
        )
        p.save()
        p.setClipRect(edit_rect)
        if opt.currentIcon:
            mode = (
                QIcon.Mode.Normal
                if opt.state & QStyle.StateFlag.State_Enabled
                else QIcon.Mode.Disabled
            )
            pixmap = opt.currentIcon.pixmap(opt.iconSize, mode)
            icon_rect = QRect(edit_rect)
            icon_rect.setWidth(opt.iconSize.width() + icon_padding[0])
            icon_rect.setHeight(opt.iconSize.height() + icon_padding[1])
            icon_rect = QStyle.alignedRect(
                opt.direction,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                icon_rect.size(),
                edit_rect,
            )
            if opt.editable:
                p.fillRect(
                    icon_rect, opt.palette.brush(QPalette.ColorRole.Base)
                )
            base_cls.drawItemPixmap(
                p, icon_rect, Qt.AlignmentFlag.AlignCenter, pixmap
            )
            if opt.direction == Qt.LayoutDirection.RightToLeft:
                edit_rect.translate(
                    -icon_padding[0] - opt.iconSize.width(), 0
                )
            else:
                edit_rect.translate(opt.iconSize.width() + icon_padding[0], 0)

        if opt.currentText and not opt.editable:
            base_cls.drawItemText(
                p,
                edit_rect.adjusted(
                    text_padding[0],
                    -text_padding[1],
                    -text_padding[0],
                    text_padding[1],
                ),
                QStyle.visualAlignment(
                    opt.direction,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                ),
                opt.palette,
                bool(opt.state & QStyle.StateFlag.State_Enabled),
                opt.currentText,
            )

        p.restore()

    def draw_panel_item_view_item(
        self, option: QStyleOption, painter: QPainter, w: QWidget
    ):
        cb = w.model().parent()
        if cb and getattr(cb, "_inverted", False):
            idx = option.index
            if idx:
                fgc = (
                    w.model().data(idx, Qt.ItemDataRole.ForegroundRole).color()
                )
                option.backgroundBrush.setColor(fgc)
        else:
            stl = self.model.get_style("QComboBox")
            stl.set_context(w)
            option.backgroundBrush.setColor(
                QColor(stl["menu-background-color"])
            )
        self._super.drawPrimitive(  # type: ignore
            QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter, w
        )

    def combobox_size(
        self,
        contents_type: QStyle.ContentsType,
        option: QStyleOption | None,
        contents_size: QtCore.QSize,
        widget: QWidget | None,
    ) -> QtCore.QSize:
        from qtpy.QtCore import QSize

        if not option or not isinstance(option, QStyleOptionComboBox):
            return QSize()

        style = self.model.get_style("QComboBox")
        style.set_context(widget)

        text_width = cb_height = 0
        if isinstance(widget, QComboBox):
            for i in range(widget.count()):
                t_rect = option.fontMetrics.boundingRect(
                    widget.itemData(i, Qt.ItemDataRole.DisplayRole)
                )
                text_width = max(text_width, t_rect.width())
                cb_height = max(cb_height, t_rect.height())

        text_width += style["text-padding"][0] * 2
        cb_height += style["text-padding"][1] * 2

        icon_width = 0
        if option.currentIcon:
            icon_size = getattr(widget, "_icon_size", 0)
            if icon_size == 0:
                all_sizes = option.currentIcon.availableSizes()
                icon_size = max(all_sizes[0].width(), all_sizes[0].height())
            icon_width = icon_size + style["icon-padding"][0] * 2
            icon_height = icon_size + style["icon-padding"][1] * 2
            cb_height = max(cb_height, icon_height)
            if text_width:
                icon_width += style["text-padding"][0]

        final_size = QSize(
            text_width + icon_width,
            min(getattr(widget, "_height", cb_height), cb_height),
        )
        return final_size

"""MenuDrawer: custom painting for QMenu."""
from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import QRect, QRectF, QSize, Qt
from qtpy.QtGui import QBrush, QColor, QIcon, QPainter, QPen
from qtpy.QtWidgets import (
    QMenu,
    QStyle,
    QStyleOption,
    QStyleOptionMenuItem,
    QWidget,
)

from ._utils import do_nothing, enum_to_str, get_icon

if TYPE_CHECKING:
    from ..style import AYONStyle


class MenuDrawer:
    """Drawer for QMenu using native QPainter calls (no QSS).

    Paints the menu panel/border (PE_PanelMenu/PE_FrameMenu) and each
    item row (CE_MenuItem).
    """

    _WIDGET_CLS = "QMenu"

    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def base_class(self) -> dict:
        return {"QMenu": QMenu}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_drawers(self) -> dict:
        return {
            enum_to_str(
                QStyle.PrimitiveElement,
                QStyle.PrimitiveElement.PE_PanelMenu,
                "QMenu",
            ): self.draw_panel,
            enum_to_str(
                QStyle.PrimitiveElement,
                QStyle.PrimitiveElement.PE_FrameMenu,
                "QMenu",
            ): self.draw_frame,
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_MenuItem,
                "QMenu",
            ): self.draw_menu_item,
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_MenuEmptyArea,
                "QMenu",
            ): do_nothing,
        }

    def register_sizers(self) -> dict:
        return {
            enum_to_str(
                QStyle.ContentsType,
                QStyle.ContentsType.CT_MenuItem,
                "QMenu",
            ): self.menu_item_size,
        }

    def register_metrics(self) -> dict:
        pm = QStyle.PixelMetric
        metrics_map = {
            pm.PM_MenuPanelWidth: self.get_metric,
            pm.PM_MenuHMargin: self.get_metric,
            pm.PM_MenuVMargin: self.get_metric,
            pm.PM_SmallIconSize: self.get_metric,
            pm.PM_MenuButtonIndicator: self.get_metric,
        }
        return {
            enum_to_str(pm, k, "QMenu"): v for k, v in metrics_map.items()
        }

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _base_style(self, widget: QWidget | None = None):
        """Return the base style dict, context-bound to *widget*."""
        style = self.model.get_style(self._WIDGET_CLS, "default", "base")
        style.set_context(widget)
        return style

    def get_metric(
        self,
        metric: QStyle.PixelMetric,
        opt: QStyleOption | None = None,
        widget: QWidget | None = None,
    ) -> int:
        pm = QStyle.PixelMetric
        style = self._base_style(widget)
        if metric == pm.PM_MenuPanelWidth:
            return int(style.get("border-width", 1))
        if metric in (pm.PM_MenuHMargin, pm.PM_MenuVMargin):
            pp = style.get("panel-padding", [4, 4])
            if isinstance(pp, (list, tuple)):
                return int(pp[0] if metric == pm.PM_MenuHMargin else pp[1])
            return int(pp)
        if metric == pm.PM_SmallIconSize:
            return int(style.get("icon-size", 16))
        if metric == pm.PM_MenuButtonIndicator:
            return int(style.get("icon-size", 16))
        return 0

    # ------------------------------------------------------------------
    # Sizing
    # ------------------------------------------------------------------

    def menu_item_size(
        self,
        contents_type: QStyle.ContentsType,
        option: QStyleOption | None,
        contents_size: QSize,
        widget: QWidget | None = None,
    ) -> QSize:
        """Compute the bounding size of a single menu item row."""
        style = self._base_style(widget)
        pad_h, pad_v = 0, 0
        ip = style.get("item-padding", [6, 12])
        if isinstance(ip, (list, tuple)):
            pad_h, pad_v = int(ip[0]), int(ip[1])
        else:
            pad_h = pad_v = int(ip)

        if not isinstance(option, QStyleOptionMenuItem):
            return QSize(contents_size.width(), contents_size.height())

        sep_type = QStyleOptionMenuItem.MenuItemType.Separator
        if option.menuItemType == sep_type:
            sep_h = int(style.get("separator-height", 1))
            return QSize(contents_size.width(), sep_h + pad_v * 2)

        icon_size = int(style.get("icon-size", 16))
        item_spacing = int(style.get("item-spacing", 4))

        # Height: font height + vertical padding
        fm = option.fontMetrics
        text_h = fm.height() if fm else contents_size.height()
        row_h = max(text_h + pad_v * 2, icon_size + pad_v * 2)

        # Width: icon gutter + text + shortcut + arrow
        text = option.text or ""
        label, _, shortcut = text.partition("\t")
        text_w = fm.horizontalAdvance(label) if fm else contents_size.width()
        sc_w = getattr(
            option,
            "reservedShortcutWidth",
            getattr(option, "tabWidth", 0),
        )
        if shortcut and sc_w == 0 and fm:
            sc_w = fm.horizontalAdvance(shortcut)
        icon_gutter = icon_size + item_spacing if option.maxIconWidth else 0
        arrow_w = (
            icon_size
            if option.menuItemType
            == QStyleOptionMenuItem.MenuItemType.SubMenu
            else 0
        )
        total_w = (
            icon_gutter
            + pad_h
            + text_w
            + (pad_h + sc_w if sc_w else 0)
            + (pad_h + arrow_w if arrow_w else 0)
            + pad_h
        )
        return QSize(max(total_w, contents_size.width()), row_h)

    # ------------------------------------------------------------------
    # Primitive painting: panel & frame
    # ------------------------------------------------------------------

    def draw_panel(
        self,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        """Fill the menu background with the panel colour."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        style = self._base_style(widget)
        radius = int(style.get("border-radius", 6))
        painter.setBrush(QBrush(QColor(style["background-color"])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(option.rect, radius, radius)
        painter.restore()

    def draw_frame(
        self,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        """Stroke the menu border."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        style = self._base_style(widget)
        radius = int(style.get("border-radius", 6))
        bw = int(style.get("border-width", 1))
        pen = QPen(QColor(style["border-color"]))
        pen.setWidth(bw)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Inset by half the pen width so the stroke is fully inside the rect.
        inset = bw / 2.0
        inset_rect = QRectF(option.rect).adjusted(
            inset, inset, -inset, -inset
        )
        painter.drawRoundedRect(inset_rect, radius, radius)
        painter.restore()

    # ------------------------------------------------------------------
    # Control painting: individual item rows
    # ------------------------------------------------------------------

    def draw_menu_item(
        self,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        """Paint a single QMenu row (normal, separator, submenu)."""
        if not isinstance(option, QStyleOptionMenuItem):
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Handle separators and return
        sep_type = QStyleOptionMenuItem.MenuItemType.Separator
        if option.menuItemType == sep_type:
            self._draw_separator(option, painter, widget)
            painter.restore()
            return

        # Resolve state and fetch styles
        is_enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        styles = self.model.get_styles(
            self._WIDGET_CLS,
            "default",
            ["base", "hover", "disabled"],
        )
        base_style = styles["base"]
        base_style.set_context(widget)
        hover_style = styles["hover"]
        hover_style.set_context(widget)
        disabled_style = styles["disabled"]
        disabled_style.set_context(widget)

        ip = base_style.get("item-padding", [6, 12])
        if isinstance(ip, (list, tuple)):
            pad_h = int(ip[0])
        else:
            pad_h = int(ip)
        item_radius = int(base_style.get("item-radius", 4))
        icon_size = int(base_style.get("icon-size", 16))
        item_spacing = int(base_style.get("item-spacing", 4))

        rect = option.rect

        # --- Selection background ---
        if is_selected and is_enabled:
            bg = QColor(hover_style.get("background-color", "#424a57"))
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, item_radius, item_radius)

        opacity = 1.0
        if not is_enabled:
            opacity = float(disabled_style.get("opacity", 0.5))
        painter.setOpacity(opacity)

        # --- Left gutter (icon or check mark) ---
        icon_gutter = option.maxIconWidth or (icon_size + item_spacing)
        x = rect.left() + pad_h
        cy = rect.center().y()

        check_type = option.checkType
        not_checkable = QStyleOptionMenuItem.CheckType.NotCheckable
        if check_type != not_checkable and option.checked:
            check_color = base_style.get("color", "#f4f5f5")
            check_icon = get_icon("check", color=check_color)
            check_rect = QRect(
                x,
                cy - icon_size // 2,
                icon_size,
                icon_size,
            )
            check_icon.paint(painter, check_rect)
        elif not option.icon.isNull():
            icon_rect = QRect(
                x,
                cy - icon_size // 2,
                icon_size,
                icon_size,
            )
            mode = (
                QIcon.Mode.Disabled if not is_enabled else QIcon.Mode.Normal
            )
            option.icon.paint(
                painter, icon_rect, Qt.AlignmentFlag.AlignCenter, mode
            )

        x += icon_gutter

        # --- Text (label + shortcut) ---
        text = option.text or ""
        label, has_tab, shortcut = text.partition("\t")

        text_color = QColor(
            hover_style.get("color", "#f4f5f5")
            if is_selected and is_enabled
            else base_style.get("color", "#f4f5f5")
        )
        painter.setPen(QPen(text_color))

        sc_w = getattr(
            option,
            "reservedShortcutWidth",
            getattr(option, "tabWidth", 0),
        )
        is_submenu = (
            option.menuItemType == QStyleOptionMenuItem.MenuItemType.SubMenu
        )
        arrow_w = icon_size if is_submenu else 0

        right_margin = pad_h + (arrow_w + pad_h if arrow_w else 0)
        label_rect = QRect(
            x,
            rect.top(),
            rect.right() - x - right_margin - (sc_w + pad_h if sc_w else 0),
            rect.height(),
        )
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label,
        )

        if shortcut:
            sc_color = QColor(
                base_style.get(
                    "shortcut-color",
                    base_style.get("color", "#8b9198"),
                )
            )
            sc_color.setAlphaF(0.6)
            painter.setPen(QPen(sc_color))
            sc_rect = QRect(
                rect.right() - right_margin - sc_w,
                rect.top(),
                sc_w,
                rect.height(),
            )
            painter.drawText(
                sc_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                shortcut,
            )

        # --- Submenu arrow ---
        if is_submenu:
            arrow_color = base_style.get("color", "#f4f5f5")
            arrow_icon = get_icon("chevron_right", color=arrow_color)
            arrow_rect = QRect(
                rect.right() - pad_h - arrow_w,
                cy - icon_size // 2,
                icon_size,
                icon_size,
            )
            arrow_icon.paint(painter, arrow_rect)

        painter.restore()

    def _draw_separator(
        self,
        option: QStyleOptionMenuItem,
        painter: QPainter,
        widget: QWidget | None = None,
    ) -> None:
        """Draw a thin horizontal separator line."""
        style = self._base_style(widget)
        color = QColor(
            style.get(
                "separator-color", style.get("border-color", "#41474d")
            )
        )
        sep_h = int(style.get("separator-height", 1))

        cy = option.rect.center().y()
        y = cy - sep_h // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRect(
            option.rect.left(),
            y,
            option.rect.width(),
            sep_h,
        )

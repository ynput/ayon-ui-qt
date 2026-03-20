from __future__ import annotations

from qtpy import QtWidgets
from qtpy.QtCore import QRect, QSize, Qt
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
    QResizeEvent,
)

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon

from .. import get_ayon_style
from ..color_utils import compute_color_for_contrast
from ..variants import QLabelVariants


class AYLabel(QtWidgets.QLabel):
    Variants = QLabelVariants

    def __init__(
        self,
        *args,
        dim: bool = False,
        icon: str = "",
        icon_color: str = "",
        icon_size: int = 20,
        icon_text_spacing=6,
        icon_fill=False,
        text_color: str = "",
        rel_text_size: int = 0,
        bold: bool = False,
        tool_tip="",
        variant: Variants = Variants.Default,
        contrast_color: QColor | None = None,
        elide_mode: Qt.TextElideMode = Qt.TextElideMode.ElideNone,
        **kwargs,
    ):
        self._dim = dim
        self._icon = icon
        self._icon_color = icon_color
        self._icon_size = icon_size
        self._icon_fill = icon_fill
        self._icon_text_spacing = icon_text_spacing
        self._rel_text_size = rel_text_size
        self._text_color = text_color
        self._bold = bold
        self._variant_str: str = variant.value
        self._text_setup_done = False
        self._style_palette = None
        self._elide_mode = elide_mode
        self._elided_text: str = ""
        # reference bg color to compute contrast-adapted text color
        self._contrast_color = (
            contrast_color
            if isinstance(contrast_color, QColor) and contrast_color.isValid()
            else None
        )
        self._contrast_adapted = None

        super().__init__(*args, **kwargs)
        self._style = get_ayon_style()
        self.setStyle(self._style)

        # used to be in polish
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)

        self._text = self.text()
        self.setToolTip(tool_tip)

        self.set_icon()

    @property
    def contrast_color(self) -> QColor | None:
        return self._contrast_color

    def set_icon(self, icon: str | None = None, color: str = "") -> None:
        if icon is not None:
            self._icon = icon
        if color:
            self._icon_color = color
        if self._icon:
            icon_color = (
                self._icon_color
                or self.palette().color(self.foregroundRole()).name()
            )
            icn: QIcon = get_icon(
                self._icon,
                color=icon_color,
                fill=self._icon_fill,
            )
            self.setPixmap(icn.pixmap(QSize(self._icon_size, self._icon_size)))

    def _ensure_font_setup(self) -> None:
        """Initialize font configuration on first paint."""
        if self._text_setup_done:
            return

        self._text_setup_done = True
        self._font = self.font()

        if self._rel_text_size != 0:
            self._font.setPointSize(
                self._font.pointSize() + self._rel_text_size
            )

        weight = QFont.Weight.Bold if self._bold else QFont.Weight.Normal
        self._font.setWeight(weight)
        self.setFont(self._font)
        self._font_metrics = QFontMetrics(self._font)
        self._update_elided_text()

    def _update_elided_text(self) -> None:
        """Recompute the elided version of the stored text."""
        if (
            self._elide_mode == Qt.TextElideMode.ElideNone
            or not self._text_setup_done
        ):
            self._elided_text = self._text
            return
        available_w = self.contentsRect().width()
        if self._icon:
            spacing = self._icon_text_spacing
            available_w -= self._icon_size + spacing
        self._elided_text = self._font_metrics.elidedText(
            self._text, self._elide_mode, max(0, available_w)
        )

    def _resolve_color(self) -> QColor:
        """Get the effective foreground color (icon_color or palette)."""
        if self._icon_color:
            return QColor(self._icon_color)
        return self.palette().color(self.foregroundRole())

    def _to_qcolor(self, color: QColor | str | None) -> QColor | None:
        """Convert a color value to QColor, handling None and strings."""
        if color is None:
            return None
        if isinstance(color, QColor):
            return color
        return QColor(color)

    def _compute_contrast_text_color(
        self,
        bg_color: QColor | str | None,
        fg_color: QColor,
    ) -> QColor:
        """Compute text color with sufficient contrast against background."""
        if not bg_color:
            return fg_color
        qbg = self._to_qcolor(bg_color)
        return compute_color_for_contrast(
            qbg.toTuple(),
            fg_color.toTuple(),
            min_contrast_ratio=7.0,
        )

    def _apply_palette(self) -> None:
        """Configure palette based on dim/contrast settings."""
        # _style_palette is guaranteed to be set in paintEvent before this call
        assert self._style_palette is not None

        if self._dim:
            p = QPalette(self._style_palette)
            p.setColor(
                QPalette.ColorGroup.Active,
                self.foregroundRole(),
                self._style_palette.color(
                    QPalette.ColorGroup.Active,
                    QPalette.ColorRole.PlaceholderText,
                ),
            )
            self.setPalette(p)
            return

        if self._contrast_color:
            txt_color = self._compute_contrast_text_color(
                self._contrast_color,
                self._style_palette.color(self.foregroundRole()),
            )
            p = QPalette(self._style_palette)
            p.setColor(self.foregroundRole(), txt_color)
            self.setPalette(p)
        else:
            self.setPalette(self._style_palette)

    def _paint_filled(self, style_data: dict) -> None:
        """Render a filled-background label driven by style data."""
        style = self._style

        # Auto-size from text metrics
        if style_data.get("auto-size"):
            padding = style_data.get("auto-size-padding", [0, 0])
            t_rect = self._font_metrics.boundingRect(self.text())
            padx = int(self._font_metrics.averageCharWidth() * padding[0])
            pady = int(self._font_metrics.height() * padding[1])
            self.setFixedSize(
                t_rect.width() + padx,
                t_rect.height() + pady,
            )

        p = QPainter(self)
        self.initPainter(p)
        p.setFont(self._font)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill color from foreground
        fill_color = self._resolve_color()
        p.setBrush(QBrush(fill_color))
        p.setPen(Qt.PenStyle.NoPen)

        # Border radius: fraction of height or fixed
        radius_frac = style_data.get("border-radius-fraction")
        if radius_frac is not None:
            radius = self.rect().height() * radius_frac
        else:
            radius = style_data.get("border-radius", 0)

        p.drawRoundedRect(self.rect(), radius, radius)

        # Text color with contrast computation
        if style_data.get("contrast-text"):
            contrast_ref = self._contrast_color or self._icon_color
            txt_color = self._compute_contrast_text_color(
                contrast_ref,
                self.palette().color(self.foregroundRole()),
            )
            p.setPen(QPen(QBrush(txt_color), 1.0))

        style.drawItemText(
            p,
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            self.palette(),
            self.isEnabled(),
            self.text(),
            textRole=QPalette.ColorRole.NoRole,
        )
        p.end()

    def _paint_icon_and_text(self, style_data: dict) -> None:
        """Render label with both icon and text.

        The icon and text are treated as a single group and positioned
        within the widget rect according to the current alignment.

        The spacing between icon and text is resolved from the
        ``icon-text-spacing`` property in *style_data*, falling back to
        the value supplied at construction time.

        Args:
            style_data: Variant style properties resolved from the style
                JSON for the current ``QLabel`` variant.
        """
        style = self._style
        p = QPainter(self)
        p.setFont(self._font)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        text_rect = self._font_metrics.boundingRect(self._elided_text)
        text_rect.adjust(0, 0, 1, 0)  # +1 pixel for antialiasing

        icon_w = self._icon_size
        icon_h = self._icon_size
        spacing = int(
            style_data.get("icon-text-spacing", self._icon_text_spacing)
        )
        group_w = icon_w + spacing + text_rect.width()
        group_h = max(icon_h, text_rect.height())

        # Position the group using the current alignment
        widget_rect = self.contentsRect().normalized()
        alignment = self.alignment()

        if alignment & Qt.AlignmentFlag.AlignLeft:
            group_x = widget_rect.left()
        elif alignment & Qt.AlignmentFlag.AlignRight:
            group_x = widget_rect.right() - group_w
        else:  # Center (default)
            group_x = widget_rect.left() + (widget_rect.width() - group_w) // 2

        if alignment & Qt.AlignmentFlag.AlignTop:
            group_y = widget_rect.top()
        elif alignment & Qt.AlignmentFlag.AlignBottom:
            group_y = widget_rect.bottom() - group_h
        else:  # VCenter (default)
            group_y = widget_rect.top() + (widget_rect.height() - group_h) // 2

        # Draw icon at the left of the group
        icon_y = group_y + (group_h - icon_h) // 2
        icn_rct = QRect(group_x, icon_y, icon_w, icon_h)
        style.drawItemPixmap(
            p,
            icn_rct,
            Qt.AlignmentFlag.AlignCenter,
            self.pixmap(),
        )

        # Draw text at the right of the icon
        pal = self.palette()
        if not self._dim:
            pal.setColor(QPalette.ColorRole.Text, self._resolve_color())

        txt_x = group_x + icon_w + spacing
        txt_y = group_y + (group_h - text_rect.height()) // 2
        txt_rct = QRect(txt_x, txt_y, text_rect.width(), text_rect.height())
        style.drawItemText(
            p,
            txt_rct,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            pal,
            self.isEnabled(),
            self._elided_text,
            textRole=self.foregroundRole(),
        )

    def _paint_text_only(self) -> None:
        """Render text-only label."""
        p = QPainter(self)
        p.setFont(self._font)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._text_color:
            # p.setPen(QPen(QColor(self._text_color)))
            pal = self.palette()
            pal.setColor(self.foregroundRole(), QColor(self._text_color))
            self.setPalette(pal)

        self._style.drawItemText(
            p,
            self.contentsRect().normalized(),
            self.alignment(),
            self.palette(),
            self.isEnabled(),
            self._elided_text,
            textRole=self.foregroundRole(),
        )

    def _paint_background(self, style_data: dict) -> None:
        """Draw background if specified by style."""
        bg_color = style_data.get("background-color")
        if bg_color and bg_color != "transparent":
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            border_radius = style_data.get("border-radius", 0)
            border_width = style_data.get("border-width", 0)
            border_color = style_data.get("border-color", "#00000000")
            p.setBrush(QBrush(QColor(bg_color)))
            p.setPen(
                QPen(QColor(border_color), border_width)
                if border_width > 0
                else Qt.PenStyle.NoPen
            )
            p.drawRoundedRect(self.rect(), border_radius, border_radius)

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        if not self._style_palette:
            self._style_palette = self.palette()

        self._ensure_font_setup()
        self._apply_palette()

        # Resolve style from JSON (guard for non-AYONStyle environments)
        qt_style = self._style
        style_data = qt_style.model.get_style("QLabel", self._variant_str)

        # Filled-background rendering (driven by JSON properties)
        if style_data.get("fill-from-foreground"):
            self._paint_filled(style_data)
        else:
            self._paint_background(style_data)
            if self._text and self._icon:
                self._paint_icon_and_text(style_data)
            elif self._icon and not self._text:
                super().paintEvent(arg__1)
            else:
                self._paint_text_only()

    def sizeHint(self) -> QSize:
        """Compute a size hint driven by QLabel style data from the style JSON.

        For variants with ``auto-size`` (e.g. badge / pill), the size is
        derived from font-metrics and the ``auto-size-padding`` factor.
        For variants with an explicit ``padding`` list (e.g. entity-label),
        the size is padded accordingly.
        When an icon is present the icon dimensions are added.
        In all other cases the base ``QLabel.sizeHint()`` is returned.

        Returns:
            The recommended widget size.
        """
        self._ensure_font_setup()

        style_data: dict = self._style.model.get_style(
            "QLabel", self._variant_str
        )

        fm = self._font_metrics

        # --- text size --------------------------------------------------
        text = self._text or ""
        if text:
            t_rect = fm.boundingRect(text)
            text_w = t_rect.width()
            text_h = t_rect.height()
        else:
            text_w = 0
            text_h = fm.height()

        # --- icon size --------------------------------------------------
        icon_w = icon_h = 0
        if self._icon:
            icon_w = self._icon_size
            icon_h = self._icon_size

        # --- variant-specific sizing ------------------------------------
        if style_data.get("auto-size"):
            # badge / pill: padding is expressed as a fraction of the
            # character metrics (x-factor of avgCharWidth, y-factor of height)
            padding = style_data.get("auto-size-padding", [0.0, 0.0])
            pad_x = int(fm.averageCharWidth() * padding[0])
            pad_y = int(fm.height() * padding[1])

            content_w = max(text_w, icon_w)
            content_h = max(text_h, icon_h)

            return QSize(content_w + pad_x, content_h + pad_y)

        explicit_padding = style_data.get("padding")
        if explicit_padding and isinstance(explicit_padding, list):
            # [vertical, horizontal] convention (same as CSS padding shorthand)
            pad_v = int(explicit_padding[0])
            pad_h = int(explicit_padding[1])

            if icon_w and text_w:
                spacing = int(
                    style_data.get(
                        "icon-text-spacing", self._icon_text_spacing
                    )
                )
                content_w = icon_w + spacing + text_w
                content_h = max(text_h, icon_h)
            elif icon_w:
                content_w = icon_w
                content_h = icon_h
            else:
                content_w = text_w
                content_h = text_h

            return QSize(
                content_w + 2 * pad_h,
                content_h + 2 * pad_v,
            )

        # Fallback: let Qt compute the default size hint
        return super().sizeHint()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Recompute elided text when the widget is resized."""
        super().resizeEvent(event)
        self._update_elided_text()

    def setText(self, arg__1: str) -> None:
        super().setText(arg__1)
        self._text = self.text()
        self._update_elided_text()


if __name__ == "__main__":
    from ayon_ui_qt.tester import Style, test

    from .container import AYContainer

    def _build() -> QtWidgets.QWidget:
        w = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.High,
            margin=16,
            layout_margin=16,
            layout_spacing=16,
        )
        l1 = AYLabel("Text Only", tool_tip="Text only")
        l2 = AYLabel(icon="indeterminate_question_box", tool_tip="Icon only")
        l3 = AYLabel(
            "Approved",
            icon="check_circle",
            icon_color="#88ff88",
            tool_tip="Text & icon with custom color",
        )
        l4 = AYLabel(
            "Text & Icon",
            icon="favorite",
            tool_tip="Text & icon with default color and 6px margin",
            rel_text_size=4,
        )
        l4.setMargin(6)
        l5 = AYLabel(
            "Badge",
            icon_color="#cd8de2",
            variant=AYLabel.Variants.Badge,
            tool_tip="badge variant",
        )
        l6 = AYLabel(
            "Badge",
            icon_color="#cd8de2",
            variant=AYLabel.Variants.Badge,
            tool_tip="badge variant with smaller text",
            rel_text_size=-2,
        )
        l7 = AYLabel(
            "bad badge",
            icon_color="",
            variant=AYLabel.Variants.Badge,
            tool_tip="Badly configured badge",
        )
        w.add_widget(l1, stretch=0)
        w.add_widget(l2, stretch=0)
        w.add_widget(l3, stretch=0)
        w.add_widget(l4, stretch=0)
        w.add_widget(l5, stretch=0)
        w.add_widget(l6, stretch=0)
        w.add_widget(l7, stretch=0)

        for i in range(0, 6):
            v = i * 51
            c = QColor(v, v, v, 255)
            pc = i * 20
            badge = AYLabel(
                f"{pc}% grey",
                icon_color=c.name(),
                variant=AYLabel.Variants.Badge,
                tool_tip=f"{pc}% grey badge with text color adaptation",
                contrast_color=c,
                rel_text_size=-3,
            )
            w.add_widget(badge, stretch=0)

        l8 = AYLabel("colored text", text_color="#55aef7")
        w.add_widget(l8, stretch=0)

        w.addStretch()
        return w

    test(_build, style=Style.AyonStyleOverCSS)

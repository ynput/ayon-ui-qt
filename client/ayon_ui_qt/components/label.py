from __future__ import annotations

from qtpy import QtWidgets
from qtpy.QtCore import QRect, QSize, Qt
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontInfo,
    QFontMetrics,
    QIcon,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
)

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon  # type: ignore

from ..color_utils import compute_color_for_contrast
from ..style import StyleDict, get_ayon_style
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
        # style params
        self._variant_str: str = variant.value
        self._style_data = StyleDict()
        self._style_palette = QPalette()
        self._style_font = QFont()
        self._style_font_metrics: QFontMetrics | None = None

        # widget params
        self._dim = dim
        self._icon = icon
        self._icon_color = icon_color
        self._icon_size = icon_size
        self._icon_fill = icon_fill
        self._icon_text_spacing = icon_text_spacing
        self._rel_text_size = rel_text_size
        self._text_color = text_color
        self._bold = bold
        self._text_setup_done = False
        self._elide_mode = elide_mode
        # copy the text because setting an icon will blank it, as a label is
        # either text or pixmap.
        self._text: str = ""
        # reference bg color to compute contrast-adapted text color
        self._contrast_color = (
            contrast_color
            if isinstance(contrast_color, QColor) and contrast_color.isValid()
            else None
        )
        self._contrast_adapted = None

        super().__init__(*args, **kwargs)
        self._style = get_ayon_style()
        self._style_data = self._style.model.get_styles(
            "QLabel", variant=self._variant_str
        )
        self._style_data.set_context(self)
        self.setStyle(self._style)

        # used to be in polish
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)

        # set alignment from style data if specified.
        alignment = self._style_data["base"].get("alignment")
        if alignment is not None:
            if alignment == "center":
                self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elif alignment == "left":
                self.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            elif alignment == "right":
                self.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )

        self._text = self.text()  # call before setting icon to preserve text
        self.setToolTip(tool_tip)

        self.set_icon()

    @property
    def contrast_color(self) -> QColor | None:
        return self._contrast_color

    def set_palette(self, palette: QPalette) -> None:
        """Set the widget palette and trigger a repaint."""
        self._style_palette = palette
        self._configure_palette()
        self.update()

    def set_font(self, font: QFont) -> None:
        """Set the widget font and trigger a repaint."""
        self._style_font = font
        self._configure_font()
        self.update()

    # Private methods -------------------------------------------------------

    def set_icon(self, icon: str | None = None, color: str = "") -> None:
        if icon is not None:
            self._icon = icon
        if color:
            self._icon_color = color

        if self._icon:
            same_as_bg = (
                self._icon_color
                and self._style_data["base"].get("background-color", raw=True)
                == "@_icon_color"
            )
            icon_color = self._icon_color
            if not icon_color:
                icon_color = self.palette().color(self.foregroundRole()).name()
            elif same_as_bg:
                icon_color = self._style_data["base"].get("color")

            icn: QIcon = get_icon(
                self._icon,
                color=icon_color,
                fill=self._icon_fill,
            )
            self.setPixmap(icn.pixmap(QSize(self._icon_size, self._icon_size)))

    def _configure_font(self) -> None:
        """Initialize font configuration on first paint."""
        if self._text_setup_done:
            return

        self._text_setup_done = True
        self._font = self.font()

        if self._rel_text_size != 0:
            # _rel_text_size is in points but setting pixels is more reliable.
            # use QFontInfo in case PixelSize() or pointSize() returns -1
            px_size = QFontInfo(self._font).pixelSize()
            px_to_pt = px_size / QFontInfo(self._font).pointSize()
            self._font.setPixelSize(
                round(px_size + self._rel_text_size * px_to_pt)
            )

        weight = QFont.Weight.Bold if self._bold else QFont.Weight.Normal
        self._font.setWeight(weight)
        self.setFont(self._font)
        self._style_font_metrics = QFontMetrics(self._font)

    def _display_text(self) -> str:
        """Recompute the elided version of the stored text."""
        if (
            self._elide_mode == Qt.TextElideMode.ElideNone
            or not self._style_font_metrics
        ):
            return self._text
        available_w = self.contentsRect().width()
        if self._icon:
            spacing = self._icon_text_spacing
            available_w -= self._icon_size + spacing
        text = self._style_font_metrics.elidedText(
            self._text, self._elide_mode, max(0, available_w)
        )
        return text

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
            qbg.toTuple(),  # type: ignore
            fg_color.toTuple(),
            min_contrast_ratio=7.0,
        )

    def _configure_palette(self) -> None:
        """Configure palette based on dim/contrast settings."""
        # _style_palette is guaranteed to be set in paintEvent before this call
        assert self._style_palette is not None

        if self._dim:
            self._style_palette.setColor(
                QPalette.ColorGroup.Active,
                self.foregroundRole(),
                self._style_palette.color(
                    QPalette.ColorGroup.Active,
                    QPalette.ColorRole.PlaceholderText,
                ),
            )
            return

        if self._text_color:
            self._style_palette.setColor(
                self.foregroundRole(), QColor(self._text_color)
            )

        if self._style_data["base"].get("fill-from-foreground", False):
            # background-color is resolved from @_icon_color via style refs
            bg_val = self._style_data["base"].get("background-color", "")
            bg_color = (
                QColor(bg_val)
                if bg_val and bg_val != "transparent"
                else self._style_palette.color(self.foregroundRole())
            )
            self._style_palette.setColor(self.backgroundRole(), bg_color)
            if not self._contrast_color:
                self._contrast_color = bg_color

        if self._style_data["base"].get("contrast-text", False):
            contrast_ref = self._contrast_color or self._icon_color
            txt_color = self._compute_contrast_text_color(
                contrast_ref,
                self.palette().color(self.foregroundRole()),
            )
            self._style_palette.setColor(self.foregroundRole(), txt_color)

        if "disabled" in self._style_data:
            opacity = self._style_data["disabled"].get("opacity", 1.0)
            if opacity < 1.0:
                for role in QPalette.ColorRole:
                    color = self._style_palette.color(role)
                    if color == Qt.GlobalColor.transparent:
                        continue
                    color.setAlphaF(opacity)
                    self._style_palette.setColor(
                        QPalette.ColorGroup.Disabled, role, color
                    )

    def _paint_filled(self, state: str) -> None:
        """Render a filled-background label driven by style data."""
        assert isinstance(self._style_font_metrics, QFontMetrics)

        # Auto-size from text metrics
        if self._style_data[state].get("auto-size"):
            padding = self._style_data[state].get("auto-size-padding", [0, 0])
            t_rect = self._style_font_metrics.boundingRect(self.text())
            padx = int(
                self._style_font_metrics.averageCharWidth() * padding[0]
            )
            pady = int(self._style_font_metrics.height() * padding[1])
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

        # handle disabled opacity for both fill and text
        p.setOpacity(self._style_data[state].get("opacity", 1.0))

        # Border radius: fraction of height or fixed
        radius_frac = self._style_data[state].get("border-radius-fraction")
        if radius_frac is not None:
            radius = self.rect().height() * radius_frac
        else:
            radius = self._style_data[state].get("border-radius", 0)

        p.drawRoundedRect(self.rect(), radius, radius)

        # Text color with contrast computation
        if self._style_data[state].get("contrast-text"):
            contrast_ref = self._contrast_color or self._icon_color
            txt_color = self._compute_contrast_text_color(
                contrast_ref,
                self.palette().color(self.foregroundRole()),
            )
            p.setPen(QPen(QBrush(txt_color), 1.0))

        self._style.drawItemText(
            p,
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            self.palette(),
            self.isEnabled(),
            self.text(),
            textRole=QPalette.ColorRole.NoRole,
        )
        p.end()

    def _paint_icon_and_text(self, state: str) -> None:
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
        assert isinstance(self._style_font_metrics, QFontMetrics)

        p = QPainter(self)
        p.setFont(self._font)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        text_rect = self._style_font_metrics.boundingRect(self._display_text())
        text_rect.adjust(0, 0, 1, 0)  # +1 pixel for antialiasing

        icon_w = self._icon_size
        icon_h = self._icon_size
        spacing = int(
            self._style_data[state].get(
                "icon-text-spacing", self._icon_text_spacing
            )
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

        # handle disabled opacity for both icon and text
        p.save()
        p.setOpacity(self._style_data[state].get("opacity", 1.0))

        # Draw icon at the left of the group
        icon_y = group_y + (group_h - icon_h) // 2
        icn_rct = QRect(group_x, icon_y, icon_w, icon_h)
        self._style.drawItemPixmap(
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
        self._style.drawItemText(
            p,
            txt_rct,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            pal,
            self.isEnabled(),
            self._display_text(),
            textRole=self.foregroundRole(),
        )
        p.restore()

    def _paint_text_only(self, state: str) -> None:
        """Render text-only label."""
        p = QPainter(self)
        p.setFont(self._font)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        if self._text_color:
            pal.setColor(self.foregroundRole(), QColor(self._text_color))
            if "disabled" in self._style_data:
                t_color = QColor(self._text_color)
                t_color.setAlphaF(self._style_data[state].get("opacity", 1.0))
                pal.setColor(
                    QPalette.ColorGroup.Disabled,
                    self.foregroundRole(),
                    t_color,
                )
        p.save()
        p.setOpacity(self._style_data[state].get("opacity", 1.0))
        self._style.drawItemText(
            p,
            self.contentsRect().normalized(),
            self.alignment(),
            pal,
            self.isEnabled(),
            self._display_text(),
            textRole=self.foregroundRole(),
        )
        p.restore()

    def _paint_background(self, state: str) -> None:
        """Draw background if specified by style."""
        bg_color = self._style_data[state].get("background-color")
        if bg_color and bg_color != "transparent":
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            border_radius = self._style_data[state].get("border-radius", 0)
            border_width = self._style_data[state].get("border-width", 0)
            border_color = self._style_data[state].get(
                "border-color", "#00000000"
            )
            qbg_color = QColor(bg_color)
            qbg_color.setAlphaF(self._style_data[state].get("opacity", 1.0))
            p.setBrush(QBrush(QColor(qbg_color)))
            p.setPen(
                QPen(QColor(border_color), border_width)
                if border_width > 0
                else Qt.PenStyle.NoPen
            )
            p.drawRoundedRect(self.rect(), border_radius, border_radius)

    # QLabel overrides ----------------------------------------------------

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        """Override to support icon + text rendering."""
        state = "disabled" if not self.isEnabled() else "base"

        # Filled-background rendering (driven by JSON properties)
        if self._style_data["base"].get("fill-from-foreground"):
            self._paint_filled(state)
        else:
            self._paint_background(state)
            if self._text and self._icon:
                self._paint_icon_and_text(state)
            elif self._icon and not self._text:
                super().paintEvent(arg__1)
            else:
                self._paint_text_only(state)

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
        # self._configure_font()
        assert isinstance(self._style_font_metrics, QFontMetrics)

        fm = self._style_font_metrics

        # --- text size --------------------------------------------------
        if self._text:
            t_rect = fm.boundingRect(self._text)
            text_w = t_rect.width() + 1  # +1 pixel for antialiasing
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
        if self._style_data["base"].get("auto-size"):
            # badge / pill: padding is expressed as a fraction of the
            # character metrics (x-factor of avgCharWidth, y-factor of height)
            padding = self._style_data["base"].get(
                "auto-size-padding", [0.0, 0.0]
            )
            pad_x = int(fm.averageCharWidth() * padding[0])
            pad_y = int(fm.height() * padding[1])

            content_w = max(text_w, icon_w)
            content_h = max(text_h, icon_h)

            return QSize(content_w + pad_x, content_h + pad_y)

        explicit_padding = self._style_data["base"].get("padding", [0, 0])
        pad_h = int(explicit_padding[0])
        pad_v = int(explicit_padding[1])

        if icon_w and text_w:
            spacing = int(
                self._style_data["base"].get(
                    "icon-text-spacing", self._icon_text_spacing
                )
            )
            content_w = icon_w + spacing + text_w
            content_h = max(text_h, icon_h)
            # print(f"{self._text!r}: {content_w + 2 * pad_h} x {content_h + 2 * pad_v}")
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

    def setText(self, arg__1: str) -> None:
        super().setText(arg__1)
        self._text = self.text()

    def palette(self) -> QPalette:
        return QPalette(self._style_palette)

    def font(self) -> QFont:
        return self._style_font

    def fontMetrics(self) -> QFontMetrics:
        assert isinstance(self._style_font_metrics, QFontMetrics)
        return self._style_font_metrics


if __name__ == "__main__":
    import json
    from ayon_ui_qt.tester import Style, test

    from .container import AYContainer

    def _build() -> QtWidgets.QWidget:
        w = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant=AYContainer.Variants.High,
            margin=16,
            layout_margin=16,
            layout_spacing=16,
        )
        for enabled in (True, False):
            row = AYContainer(
                layout=AYContainer.Layout.HBox,
                variant=AYContainer.Variants.High,
                layout_spacing=16,
            )
            row.add_widget(
                QtWidgets.QLabel("Enabled:" if enabled else "Disabled:"),
                stretch=0,
            )
            l1 = AYLabel("Text Only", tool_tip="Text only")
            l2 = AYLabel(
                icon="indeterminate_question_box", tool_tip="Icon only"
            )
            l3 = AYLabel(
                "Approved",
                icon="check_circle",
                icon_color="#88ff88",
                tool_tip="Text & icon with custom color",
            )
            # print(f"i+t default: {json.dumps(l3._style_data, indent=4)}")
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
            # print(f"badge: {json.dumps(l5._style_data, indent=4)}")
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
            row.add_widget(l1, stretch=0)
            row.add_widget(l2, stretch=0)
            row.add_widget(l3, stretch=0)
            row.add_widget(l4, stretch=0)
            row.add_widget(l5, stretch=0)
            row.add_widget(l6, stretch=0)
            row.add_widget(l7, stretch=0)

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
                row.add_widget(badge, stretch=0)

            l8 = AYLabel("colored text", text_color="#55aef7")
            row.add_widget(l8, stretch=0)

            l10 = AYLabel(
                "Modeling",
                icon="3d",
                icon_size=16,
                variant=AYLabel.Variants.Entity_Label,
            )
            # print(f"Entity_Label: {json.dumps(l10._style_data, indent=4)}")
            row.add_widget(l10, stretch=0)
            l9 = AYLabel(
                "PRG",
                icon="play_circle",
                icon_color="#f7a355",
                icon_size=16,
                variant=AYLabel.Variants.Entity_Label_Filled,
            )
            # print(f"Entity_Label_Filled: {json.dumps(l9._style_data, indent=4)}")
            row.add_widget(l9, stretch=0)
            row.addStretch()

            row.setEnabled(enabled)
            w.add_widget(row)
        return w

    test(_build, style=Style.AyonStyleOverCSS)

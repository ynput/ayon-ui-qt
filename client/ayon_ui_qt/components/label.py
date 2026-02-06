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
        text_color: str = "",
        rel_text_size: int = 0,
        bold: bool = False,
        tool_tip="",
        variant: Variants = Variants.Default,
        contrast_color: QColor | None = None,
        **kwargs,
    ):
        self._dim = dim
        self._icon = icon
        self._icon_color = icon_color
        self._icon_size = icon_size
        self._icon_text_spacing = icon_text_spacing
        self._rel_text_size = rel_text_size
        self._text_color = text_color
        self._bold = bold
        self._variant_str: str = variant.value
        self._text_setup_done = False
        self._style_palette = None
        # reference bg color to compute contrast-adapted text color
        self._contrast_color = (
            contrast_color
            if isinstance(contrast_color, QColor) and contrast_color.isValid()
            else None
        )
        self._contrast_adapted = None

        super().__init__(*args, **kwargs)
        self.setStyle(get_ayon_style())

        # used to be in polish
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)

        self._text = self.text()
        self.setToolTip(tool_tip)

        self.set_icon()

    @property
    def contrast_color(self) -> QColor | None:
        return self._contrast_color

    def set_icon(self):
        if self._icon:
            icon_color = (
                self._icon_color
                or self.palette().color(self.foregroundRole()).name()
            )
            icn: QIcon = get_icon(self._icon, color=icon_color)
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

    def _paint_badge_or_pill(self) -> None:
        """Render badge or pill variant."""
        style = self.style()

        # Size based on text metrics
        t_rect = self._font_metrics.boundingRect(self.text())
        padx = int(self._font_metrics.averageCharWidth() * 1.5)
        pady = int(self._font_metrics.height() * 0.25)
        self.setFixedSize(t_rect.width() + padx, t_rect.height() + pady)

        p = QPainter(self)
        self.initPainter(p)
        p.setFont(self._font)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded background
        p.setBrush(QBrush(self._resolve_color()))
        p.setPen(Qt.PenStyle.NoPen)
        radius = self.rect().height() / (
            5.0 if self._variant_str == "badge" else 2.0
        )
        p.drawRoundedRect(self.rect(), radius, radius)

        # Draw text with contrast color
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

    def _paint_icon_and_text(self) -> None:
        """Render label with both icon and text."""
        style = self.style()
        p = QPainter(self)
        p.setFont(self._font)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        text_rect = self._font_metrics.boundingRect(self._text)
        text_rect.adjust(0, 0, 1, 0)  # +1 pixel for antialiasing
        m = self.margin()

        # Adjust contents for icon + spacing + text
        self.setContentsMargins(
            0, 0, self._icon_text_spacing + text_rect.width(), 0
        )
        cr = self.contentsRect().normalized()

        # Draw icon
        icn_rct = QRect(cr)
        icn_rct.adjust(0, 0, -m, 0)
        style.drawItemPixmap(
            p,
            icn_rct,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
            self.pixmap(),
        )

        # Draw text
        pal = self.palette()
        if not self._dim:
            pal.setColor(QPalette.ColorRole.Text, self._resolve_color())

        txt_rct = cr.adjusted(
            cr.width() + self._icon_text_spacing - m, 0, 0, 0
        )
        txt_rct.setWidth(text_rect.width())
        style.drawItemText(
            p,
            txt_rct,
            self.alignment(),
            pal,
            self.isEnabled(),
            self._text,
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

        self.style().drawItemText(
            p,
            self.contentsRect().normalized(),
            self.alignment(),
            self.palette(),
            self.isEnabled(),
            self._text,
            textRole=self.foregroundRole(),
        )

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        if not self._style_palette:
            self._style_palette = self.palette()

        self._ensure_font_setup()
        self._apply_palette()

        if self._variant_str in ("badge", "pill"):
            self._paint_badge_or_pill()
        elif self._text and self._icon:
            self._paint_icon_and_text()
        elif self._icon and not self._text:
            super().paintEvent(arg__1)
        else:
            self._paint_text_only()

    def setText(self, arg__1: str) -> None:
        super().setText(arg__1)
        self._text = self.text()


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

from typing import Literal

from qtpy import QtWidgets
from qtpy.QtCore import QRect, QSize, Qt
from qtpy.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPaintEvent,
    QPalette,
    QBrush,
    QPen,
)

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon


class AYLabel(QtWidgets.QLabel):
    Variant = Literal["", "badge", "pill"]

    def __init__(
        self,
        *args,
        dim: bool = False,
        icon: str = "",
        icon_color: str = "",
        icon_size: int = 20,
        icon_text_spacing=6,
        rel_text_size: int = 0,
        bold: bool = False,
        tool_tip="",
        variant="",
        **kwargs,
    ):
        self._dim = dim
        self._icon = icon
        self._icon_color = icon_color
        self._icon_size = icon_size
        self._icon_text_spacing = icon_text_spacing
        self._rel_text_size = rel_text_size
        self._bold = bold
        self._variant = variant
        self._text_setup_done = False
        self._style_palette = None

        super().__init__(*args, **kwargs)
        self._text = self.text()
        self.setToolTip(tool_tip)

        self.set_icon()

    def set_icon(self):
        if self._icon:
            icon_color = (
                self._icon_color
                or self.palette().color(self.foregroundRole()).name()
            )
            icn: QIcon = get_icon(self._icon, color=icon_color)
            self.setPixmap(icn.pixmap(QSize(self._icon_size, self._icon_size)))

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        if not self._style_palette:
            self._style_palette = self.palette()

        if not self._text_setup_done:
            self._text_setup_done = True
            font = self.font()
            if self._rel_text_size != 0:
                point_size = font.pointSize() + self._rel_text_size
                font.setPointSize(point_size)
            if self._bold:
                font.setWeight(QFont.Weight.Bold)
            else:
                font.setWeight(QFont.Weight.Normal)
            self.setFont(font)

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
        else:
            self.setPalette(self._style_palette)

        if self._variant in ("badge", "pill"):
            style = self.style()

            t_rect = self.fontMetrics().boundingRect(self.text())
            padx = int(self.fontMetrics().averageCharWidth() * 1.5)
            pady = int(self.fontMetrics().height() * 0.25)
            self.setFixedWidth(t_rect.width() + padx)
            self.setFixedHeight(t_rect.height() + pady)

            p = QPainter(self)
            self.initPainter(p)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            b = QBrush(QColor(self._icon_color))
            p.setBrush(b)
            p.setPen(Qt.PenStyle.NoPen)
            radius = self.rect().height() / (
                5.0 if self._variant == "badge" else 2.0
            )
            p.drawRoundedRect(self.rect(), radius, radius)

            style.drawItemText(
                p,
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                self.palette(),
                self.isEnabled(),
                self.text(),
                textRole=self.backgroundRole(),
            )

            return

        if self._text and self._icon:

            def _show_rect(painter, rect, color):
                painter.save()
                painter.setPen(QColor(color))
                painter.drawRoundedRect(rect, 4, 4)
                painter.restore()

            # draw it ourselves, using the style
            style = self.style()
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            text_rect = self.fontMetrics().boundingRect(self._text)
            text_rect.adjust(0, 0, 1, 0)  # +1 pixel for antialiasing
            m = self.margin()

            # adjust the global rect
            self.setContentsMargins(
                0, 0, self._icon_text_spacing + text_rect.width(), 0
            )
            cr = self.contentsRect().normalized()
            # _show_rect(p, cr, "#800")

            # icon rect to draw icon
            icn_rct = QRect(cr)
            icn_rct.adjust(0, 0, -m, 0)
            # _show_rect(p, icn_rct, "#080")
            style.drawItemPixmap(
                p,
                icn_rct,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                self.pixmap(),
            )

            # draw text
            pal = self.palette()
            if not self._dim:
                txt_color = (
                    self._icon_color
                    or self.palette().color(self.foregroundRole()).name()
                )
                pal.setColor(QPalette.ColorRole.Text, QColor(txt_color))
            txt_rct = cr.adjusted(
                cr.width() + self._icon_text_spacing - m, 0, 0, 0
            )
            txt_rct.setWidth(text_rect.width())
            # _show_rect(p, txt_rct, "#08f")
            style.drawItemText(
                p,
                txt_rct,
                self.alignment(),
                pal,
                self.isEnabled(),
                self._text,
                textRole=self.foregroundRole(),
            )
            return

        super().paintEvent(arg__1)


if __name__ == "__main__":
    from ayon_ui_qt.tester import Style, test

    from .container import AYContainer

    def _build() -> QtWidgets.QWidget:
        w = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="high",
            margin=16,
            layout_margin=16,
            layout_spacing=32,
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
        )
        l4.setMargin(6)
        l5 = AYLabel(
            "Badge",
            icon_color="#cd8de2",
            variant="badge",
            tool_tip="badge variant",
        )
        l6 = AYLabel(
            "Badge",
            icon_color="#cd8de2",
            variant="badge",
            tool_tip="badge variant",
            rel_text_size=-2,
        )
        l7 = AYLabel(
            "small pill",
            icon_color="#cd8de2",
            variant="pill",
            tool_tip="pill variant",
            rel_text_size=-2,
        )
        w.add_widget(l1, stretch=0)
        w.add_widget(l2, stretch=0)
        w.add_widget(l3, stretch=0)
        w.add_widget(l4, stretch=0)
        w.add_widget(l5, stretch=0)
        w.add_widget(l6, stretch=0)
        w.add_widget(l7, stretch=0)
        w.addStretch()
        return w

    test(_build, style=Style.Widget)

from qtpy import QtGui, QtWidgets
from qtpy.QtGui import QFont, QPalette

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon


class AYLabel(QtWidgets.QLabel):
    def __init__(
        self,
        *args,
        dim: bool = False,
        icon: str = "",
        icon_color: str = "",
        rel_text_size: int = 0,
        bold: bool = False,
        **kwargs,
    ):
        self._dim = dim
        self._icon = icon
        self._icon_color = icon_color if icon_color else "#ffffff"
        self._rel_text_size = rel_text_size
        self._bold = bold
        self._text_is_set = False
        self._style_palette = None

        super().__init__(*args, **kwargs)

        self.set_icon()

    def set_icon(self):
        if self._icon:
            icn = get_icon(self._icon, color=self._icon_color)
            self.setPixmap(icn.pixmap())

    def paintEvent(self, arg__1: QtGui.QPaintEvent) -> None:
        if not self._style_palette:
            self._style_palette = self.palette()

        if not self._text_is_set:
            self._text_is_set = True
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

        super().paintEvent(arg__1)

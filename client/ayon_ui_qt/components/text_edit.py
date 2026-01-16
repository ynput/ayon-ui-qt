"""text edit"""

from __future__ import annotations

from typing import Literal

from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QPaintEvent
from qtpy.QtWidgets import QStyle, QStyleOptionFrame, QTextEdit

from .. import get_ayon_style


class AYTextEdit(QTextEdit):
    """AYON styled text edit widget.

    Overrides Qt's stylesheet painting with AYONStyle custom rendering.

    Args:
        *args: Positional arguments passed to QTextEdit.
        **kwargs: Keyword arguments passed to QTextEdit.
    """

    def __init__(
        self,
        *args,
        variant: Literal[
            "", "low", "high", "debug-r", "debug-g", "debug-b"
        ] = "",
        **kwargs,
    ):
        self.variant = variant
        super().__init__(*args, **kwargs)
        self.setStyle(get_ayon_style())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        if self.testAttribute(Qt.WidgetAttribute.WA_StyleSheet):
            p = QPainter(self)
            option = QStyleOptionFrame()
            self.initStyleOption(option)
            return get_ayon_style().drawControl(
                QStyle.ControlElement.CE_ShapedFrame, option, p, self
            )
        super().paintEvent(arg__1)

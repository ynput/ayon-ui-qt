"""scroll area"""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QPaintEvent
from qtpy.QtWidgets import (
    QScrollArea,
    QScrollBar,
    QStyle,
    QStyleOptionSlider,
)

from .. import get_ayon_style


class AYScrollBar(QScrollBar):
    """AYON styled scroll bar widget.

    Overrides Qt's stylesheet painting with AYONStyle custom rendering.

    Args:
        *args: Positional arguments passed to QTextEdit.
        **kwargs: Keyword arguments passed to QTextEdit.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setStyle(get_ayon_style())

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        if self.testAttribute(Qt.WidgetAttribute.WA_StyleSheet):
            # from .. import get_ayon_style

            p = QPainter(self)
            option = QStyleOptionSlider()
            self.initStyleOption(option)
            option.subControls = QStyle.SubControl.SC_All
            get_ayon_style().drawComplexControl(
                QStyle.ComplexControl.CC_ScrollBar, option, p, self
            )
            return
        super().paintEvent(arg__1)


class AYScrollArea(QScrollArea):
    """AYON styled scroll area widget.

    Overrides Qt's stylesheet painting with AYONStyle custom rendering.

    Args:
        *args: Positional arguments passed to QTextEdit.
        **kwargs: Keyword arguments passed to QTextEdit.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyle(get_ayon_style())

        self.setVerticalScrollBar(AYScrollBar(Qt.Orientation.Vertical))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBar(AYScrollBar(Qt.Orientation.Horizontal))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

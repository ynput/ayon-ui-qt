"""checkbox"""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QPaintEvent
from qtpy.QtWidgets import QCheckBox, QStyle, QStyleOptionButton

from .. import get_ayon_style


class AYCheckBox(QCheckBox):
    """AYON styled checkbox widget.

    Overrides Qt's stylesheet painting with AYONStyle custom rendering.

    Args:
        *args: Positional arguments passed to QCheckBox.
        **kwargs: Keyword arguments passed to QCheckBox.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyle(get_ayon_style())

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        if self.testAttribute(Qt.WidgetAttribute.WA_StyleSheet):
            p = QPainter(self)
            option = QStyleOptionButton()
            self.initStyleOption(option)
            _style = get_ayon_style()
            _style.drawControl(
                QStyle.ControlElement.CE_CheckBox, option, p, self
            )
            return

        super().paintEvent(arg__1)


if __name__ == "__main__":
    from ..tester import test
    from .container import AYContainer

    def _build():
        container = AYContainer(layout_margin=10)
        cb1 = AYCheckBox("Regular Checkbox")
        container.add_widget(cb1)
        return container

    test(_build)

"""checkbox"""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QPaintEvent
from qtpy.QtWidgets import QCheckBox, QStyle, QStyleOptionButton

from .. import get_ayon_style
from ..variants import QCheckBoxVariants


class AYCheckBox(QCheckBox):
    """AYON styled checkbox widget.

    Overrides Qt's stylesheet painting with AYONStyle custom rendering.

    Args:
        *args: Positional arguments passed to QCheckBox.
        **kwargs: Keyword arguments passed to QCheckBox.
    """

    Variants = QCheckBoxVariants

    def __init__(
        self,
        *args,
        variant: Variants = Variants.Default,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._variant_str = variant.value
        self.setStyle(get_ayon_style())

    def paintEvent(self, arg__1: QPaintEvent) -> None:
        p = QPainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        _style = get_ayon_style()
        _style.drawControl(QStyle.ControlElement.CE_CheckBox, option, p, self)
        return


if __name__ == "__main__":
    from ..tester import test
    from .container import AYContainer

    def _build():
        container = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=20,
        )
        for variant in AYCheckBox.Variants:
            cb1 = AYCheckBox("Default Checkbox", variant=variant)
            container.add_widget(cb1)
        return container

    test(_build)

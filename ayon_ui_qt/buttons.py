from __future__ import annotations
import copy
import os
from typing import Literal, get_args

from qtpy import QtCore, QtGui, QtWidgets

try:
    from qtmaterialsymbols import get_icon
except ImportError:
    from vendor.qtmaterialsymbols import get_icon


ButtonVariant = Literal[
    "surface",
    "tonal",
    "filled",
    "tertiary",
    "text",
    "nav",
    "danger",
]


class AYButton(QtWidgets.QPushButton):
    def __init__(
        self,
        *args,
        variant: ButtonVariant = "surface",
        icon: str | None = None,
        icon_size: int = 24,
        tooltip: str = "",
        **kwargs,
    ):
        self._icon = icon
        self._variant = variant
        self._icon_color = QtGui.QColor(255, 255, 255)
        self._icon_size = icon_size
        self._tooltip = tooltip

        super().__init__(*args, **kwargs)

        if self._icon:
            self.set_icon(self._icon)

        if self._tooltip:
            self.setToolTip(self._tooltip)

    def set_icon(self, icon_name: str):
        self._icon = icon_name
        icn = get_icon(self._icon, color=self._icon_color)
        self.setIcon(icn)

    def get_variant(self) -> str:
        return self._variant

    def set_variant(self, value: str):
        self._variant = value

    def get_has_icon(self) -> bool:
        return self._icon is not None

    def set_has_icon(self, value):
        pass

    def get_icon_color(self):
        return self._icon_color

    def set_icon_color(self, value):
        val = copy.copy(value)
        if self._icon and self._icon_color != val:
            icn = get_icon(self._icon, color=val)
            self.setIcon(icn)
        self._icon_color = val

    # TO BE REMOVED: Properties used by the CSS implementation.
    variant = QtCore.Property(str, get_variant, set_variant)
    has_icon = QtCore.Property(bool, get_has_icon, set_has_icon)
    icon_color = QtCore.Property(QtGui.QColor, get_icon_color, set_icon_color)


# TEST =======================================================================


def _build_test():
    # Create and show the test widget
    widget = QtWidgets.QFrame()
    tl = QtWidgets.QVBoxLayout(widget)

    variants = [v for v in get_args(ButtonVariant)]

    l1 = QtWidgets.QHBoxLayout()
    for i, var in enumerate(variants):
        b = AYButton(f"{var} button", variant=var)
        l1.addWidget(b)

    l2 = QtWidgets.QHBoxLayout()
    for i, var in enumerate(variants):
        b = AYButton(f"{var} button", variant=var, icon="add")
        l2.addWidget(b)

    l3 = QtWidgets.QHBoxLayout()
    for i, var in enumerate(variants):
        b = AYButton(variant=var, icon="add")
        l3.addWidget(b)
    l3.addStretch(1)

    tl.addLayout(l1)
    tl.addLayout(l2)
    tl.addLayout(l3)

    return widget


if __name__ == "__main__":
    from ayon_ui_qt.tester import test

    os.environ["QT_SCALE_FACTOR"] = "1"
    test(_build_test, use_css=True)

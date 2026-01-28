from __future__ import annotations

from typing import Union
from enum import Enum

from qtpy import QtCore, QtGui, QtWidgets

from .. import get_ayon_style
from ..utils import color_blend
from ..variants import QFrameVariants


class AYFrame(QtWidgets.QFrame):
    Variants = QFrameVariants

    def __init__(
        self,
        *args,
        bg=False,
        variant: Variants = Variants.Default,
        margin=0,
        bg_tint="",
        **kwargs,
    ):
        # Convert enum to string if needed
        self._bg: bool = bg
        self._variant_str = variant.value
        self._bg_tint = bg_tint
        self._bg_color = None

        super().__init__(*args, **kwargs)
        self.setStyle(get_ayon_style())

        self.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self.setContentsMargins(margin, margin, margin, margin)

    def paintEvent(self, arg__1: QtGui.QPaintEvent) -> None:
        if self.testAttribute(QtCore.Qt.WidgetAttribute.WA_StyleSheet):
            p = QtGui.QPainter(self)
            option = QtWidgets.QStyleOptionFrame()
            self.initStyleOption(option)
            return get_ayon_style().drawControl(
                QtWidgets.QStyle.ControlElement.CE_ShapedFrame, option, p, self
            )
        super().paintEvent(arg__1)

    def get_bg_color(self, base_color: str):
        if not self._bg_color:
            self._bg_color = base_color
            if self._bg_tint:
                self._bg_color = color_blend(base_color, self._bg_tint, 0.1)
        return self._bg_color

    def get_bg(self) -> bool:
        return self._bg

    def set_bg(self, value):
        pass

    bg = QtCore.Property(bool, get_bg, set_bg)  # type: ignore

from typing import Literal

from qtpy import QtCore, QtWidgets
from ..utils import color_blend


class AYFrame(QtWidgets.QFrame):
    def __init__(
        self,
        *args,
        bg=False,
        variant: Literal["", "low", "high"] = "",
        margin=0,
        bg_tint="",
        **kwargs,
    ):
        self._bg: bool = bg
        self.variant = variant
        self._bg_tint = bg_tint
        self._bg_color = None

        super().__init__(*args, **kwargs)

        self.setContentsMargins(margin, margin, margin, margin)

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

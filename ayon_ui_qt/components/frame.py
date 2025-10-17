from typing import Literal

from qtpy import QtCore, QtWidgets


class AYFrame(QtWidgets.QFrame):
    def __init__(
        self,
        *args,
        bg=False,
        variant: Literal["", "low", "high"] = "",
        margin=0,
        **kwargs,
    ):
        self._bg: bool = bg
        self.variant = variant

        super().__init__(*args, **kwargs)

        self.setContentsMargins(margin, margin, margin, margin)

    def get_bg(self) -> bool:
        return self._bg

    def set_bg(self, value):
        pass

    bg = QtCore.Property(bool, get_bg, set_bg)  # type: ignore

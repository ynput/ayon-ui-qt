from __future__ import annotations

from enum import Enum
from typing import Literal

from qtpy.QtWidgets import QWidget, QLayout, QLayoutItem
from qtpy.QtCore import Qt

from .frame import AYFrame
from .layouts import AYGridLayout, AYHBoxLayout, AYVBoxLayout


class AYContainer(AYFrame):
    class Layout(Enum):
        HBox = 0
        VBox = 1
        Grid = 2

    def __init__(
        self,
        *args,
        layout: Layout = Layout.HBox,
        variant: Literal["", "low", "high"] = "",
        margin=0,
        layout_spacing=0,
        layout_margin=0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs, variant=variant, margin=margin)
        self.variant = variant
        if layout == AYContainer.Layout.HBox:
            self._layout = AYHBoxLayout(
                self, spacing=layout_spacing, margin=layout_margin
            )
        elif layout == AYContainer.Layout.VBox:
            self._layout = AYVBoxLayout(
                self, spacing=layout_spacing, margin=layout_margin
            )
        elif layout == AYContainer.Layout.Grid:
            self._layout = AYGridLayout(
                self, spacing=layout_spacing, margin=layout_margin
            )
        else:
            raise ValueError(f"Unknown Layout type : {layout}")

    def add_widget(
        self,
        w: QWidget,
        stretch: int = 0,
        row: int = 0,
        column: int = 0,
        alignment: Qt.AlignmentFlag = 0,  # type: ignore
    ):
        if isinstance(self._layout, (AYHBoxLayout, AYVBoxLayout)):
            self._layout.addWidget(w, stretch=stretch)
        elif isinstance(self._layout, AYGridLayout):
            self._layout.addWidget(w, row, column, alignment)
        else:
            raise ValueError(f"Unknown Layout type : {self._layout}")

    def add_layout(
        self,
        lyt: QLayout,
        stretch: int = 0,
        row: int = 0,
        column: int = 0,
        alignment: Qt.AlignmentFlag = 0,  # type: ignore
    ):
        if isinstance(self._layout, (AYHBoxLayout, AYVBoxLayout)):
            self._layout.addLayout(lyt, stretch=stretch)
        elif isinstance(self._layout, AYGridLayout):
            self._layout.addLayout(lyt, row, column, alignment)
        else:
            raise ValueError(f"Unknown Layout type : {self._layout}")

    def insert_widget(self, index: int, w: QWidget, stretch: int = 0):
        if isinstance(self._layout, (AYHBoxLayout, AYVBoxLayout)):
            if isinstance(w, QWidget):
                self._layout.insertWidget(index, w, stretch=stretch)
        elif isinstance(self._layout, AYGridLayout):
            raise ValueError(f"Not supported by QGridLayout : {self._layout}")

    def count(self) -> int:
        return self._layout.count()

    def addStretch(self, stretch: int = 0) -> None:
        if isinstance(self._layout, AYGridLayout):
            return
        self._layout.addStretch(stretch=stretch)

    def takeAt(self, index: int) -> QLayoutItem:
        return self._layout.takeAt(index)

    def itemAt(self, index: int) -> QLayoutItem:
        if isinstance(self._layout, AYGridLayout):
            raise NotImplementedError
        return self._layout.itemAt(index)


if __name__ == "__main__":
    from ayon_ui_qt.tester import Style, test

    def build():
        w = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_spacing=10,
            layout_margin=10,
        )
        w.add_widget(
            AYContainer(
                layout=AYContainer.Layout.VBox,
                variant="high",
                layout_margin=10,
            )
        )
        w.add_widget(
            AYContainer(
                layout=AYContainer.Layout.VBox,
                variant="high",
                layout_margin=10,
            )
        )
        w.add_widget(
            AYContainer(
                layout=AYContainer.Layout.VBox,
                variant="high",
                layout_margin=10,
            )
        )
        w.setMinimumWidth(200)
        w.setMinimumHeight(400)
        return w

    test(build, style=Style.Widget)

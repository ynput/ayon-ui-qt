"""Visual regression tests for AYButton."""

from __future__ import annotations

from qtpy.QtWidgets import QStyle, QStyleOptionButton, QWidget

from widget_test import WidgetTest
from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.container import AYContainer


class _HoverButton(AYButton):
    """AYButton subclass that can force the hover appearance for snapshot tests."""

    def __init__(self, *args, **kwargs):
        self._force_hover: bool = False  # must be set before super().__init__ calls setStyle
        super().__init__(*args, **kwargs)

    def set_force_hover(self, value: bool) -> None:
        self._force_hover = value
        self.update()

    def initStyleOption(self, option: QStyleOptionButton) -> None:
        super().initStyleOption(option)
        if self._force_hover:
            option.state |= QStyle.StateFlag.State_MouseOver


class ButtonTest(WidgetTest):
    """Tests all AYButton variants: text-only, icon+text, icon-only, checkable."""

    size = (900, 400)
    tolerance = 0.0

    def build(self) -> QWidget:
        root = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=12,
        )

        variants = list(AYButton.Variants)
        self._checkable_buttons: list[AYButton] = []
        self._row1_buttons: list[_HoverButton] = []

        # Row 1: text-only buttons (use _HoverButton so hover can be forced in steps)
        row1 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=8,
        )
        for var in variants:
            btn = _HoverButton(var.value, variant=var)
            row1.add_widget(btn)
            self._row1_buttons.append(btn)
        row1.addStretch(1)
        root.add_widget(row1)

        # Row 2: icon + text buttons
        row2 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=8,
        )
        for var in variants:
            btn = AYButton(var.value, variant=var, icon="add")
            row2.add_widget(btn)
        row2.addStretch(1)
        root.add_widget(row2)

        # Row 3: icon-only buttons
        row3 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=8,
        )
        for var in variants:
            btn = AYButton(variant=var, icon="home")
            row3.add_widget(btn)
        row3.addStretch(1)
        root.add_widget(row3)

        # Row 4: checkable buttons (toggled in steps)
        row4 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=8,
        )
        for var in variants:
            btn = AYButton(
                var.value,
                variant=var,
                icon="star",
                icon_on="star",
                checkable=True,
            )
            row4.add_widget(btn)
            self._checkable_buttons.append(btn)
        row4.addStretch(1)
        root.add_widget(row4)

        return root

    def check_all(self) -> None:
        for btn in self._checkable_buttons:
            btn.setChecked(True)

    def uncheck_all(self) -> None:
        for btn in self._checkable_buttons:
            btn.setChecked(False)

    def hover_row1(self) -> None:
        """Force the hover appearance on all text-only row-1 buttons."""
        for btn in self._row1_buttons:
            btn.set_force_hover(True)

    def unhover_row1(self) -> None:
        """Clear the forced hover state, restoring the normal appearance."""
        for btn in self._row1_buttons:
            btn.set_force_hover(False)

    def steps(self) -> list:
        return [self.check_all, self.uncheck_all, self.hover_row1, self.unhover_row1]

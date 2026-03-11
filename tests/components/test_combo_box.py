"""Visual regression tests for AYComboBox."""

from __future__ import annotations

from qtpy.QtWidgets import QWidget

from widget_test import WidgetTest
from ayon_ui_qt.components.combo_box import AYComboBox, ALL_STATUSES
from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.data_models import MenuSize


class ComboBoxTest(WidgetTest):
    """Tests AYComboBox across display modes (Full/Short/Icon) and variants."""

    size = (700, 200)
    tolerance = 0.0

    def build(self) -> QWidget:
        root = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=12,
        )

        # Row 1: Default variant – Full mode
        row1 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=8,
        )
        self._default_full = AYComboBox(
            items=ALL_STATUSES,
            size=MenuSize.Full,
            variant=AYComboBox.Variants.Default,
            placeholder="Select status…",
        )
        self._default_full.setCurrentIndex(2)  # In progress
        row1.add_widget(self._default_full)

        # Row 1: Low variant
        self._low_full = AYComboBox(
            items=ALL_STATUSES,
            size=MenuSize.Full,
            variant=AYComboBox.Variants.Low,
        )
        self._low_full.setCurrentIndex(3)  # Pending review
        row1.add_widget(self._low_full)
        row1.addStretch(1)
        root.add_widget(row1)

        # Row 2: Short + Icon modes
        row2 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=8,
        )
        self._short_combo = AYComboBox(
            items=ALL_STATUSES,
            size=MenuSize.Short,
        )
        self._short_combo.setCurrentIndex(4)  # Approved
        row2.add_widget(self._short_combo)

        self._icon_combo = AYComboBox(
            items=ALL_STATUSES,
            size=MenuSize.Icon,
        )
        self._icon_combo.setCurrentIndex(5)  # On hold
        row2.add_widget(self._icon_combo)
        row2.addStretch(1)
        root.add_widget(row2)

        return root

    def set_inverted(self) -> None:
        self._default_full.set_inverted(True)
        self._low_full.set_inverted(True)
        self._short_combo.set_inverted(True)
        self._icon_combo.set_inverted(True)

    def set_not_inverted(self) -> None:
        self._default_full.set_inverted(False)
        self._low_full.set_inverted(False)
        self._short_combo.set_inverted(False)
        self._icon_combo.set_inverted(False)

    def steps(self):
        return [self.set_inverted, self.set_not_inverted]

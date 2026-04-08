"""Visual regression tests for AYLabel."""

from __future__ import annotations

from qtpy.QtWidgets import QWidget

from widget_test import WidgetTest
from ayon_ui_qt.components.label import AYLabel
from ayon_ui_qt.components.container import AYContainer


class LabelTest(WidgetTest):
    """Tests AYLabel across all variants, dim/bold/icon states."""

    size = (600, 400)
    tolerance = 0.0

    def build(self) -> QWidget:
        root = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=10,
        )

        # Default variant - plain, dim, bold
        row_default = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=12,
        )
        row_default.add_widget(AYLabel("Default text"))
        row_default.add_widget(AYLabel("Dim text", dim=True))
        row_default.add_widget(AYLabel("Bold text", bold=True))
        row_default.add_widget(AYLabel("Larger text", rel_text_size=4))
        row_default.add_widget(AYLabel("Smaller text", rel_text_size=-2))
        row_default.addStretch(1)
        root.add_widget(row_default)

        # With icon
        row_icon = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=12,
        )
        row_icon.add_widget(AYLabel("", icon="home", icon_size=20))
        row_icon.add_widget(AYLabel("", icon="star", icon_size=24, icon_color="#f4c430"))
        row_icon.add_widget(AYLabel("", icon="check_circle", icon_size=24, icon_color="#00b894"))
        row_icon.addStretch(1)
        root.add_widget(row_icon)

        # All label variants
        for variant in AYLabel.Variants:
            row = AYContainer(
                layout=AYContainer.Layout.HBox,
                layout_margin=0,
                layout_spacing=12,
            )
            row.add_widget(AYLabel(f"{variant.name} label", variant=variant))
            row.add_widget(AYLabel(f"{variant.name} dim", variant=variant, dim=True))
            row.addStretch(1)
            root.add_widget(row)

        # Tag variant with a colored background container to show contrast
        colored_row = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            layout_margin=8,
            layout_spacing=8,
        )
        colored_row.add_widget(
            AYLabel("Tag on dark", variant=AYLabel.Variants.Tag)
        )
        colored_row.addStretch(1)
        root.add_widget(colored_row)

        return root

    def steps(self):
        return []

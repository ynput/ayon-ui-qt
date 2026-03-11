"""Visual regression tests for AYUserImage."""

from __future__ import annotations

from qtpy.QtWidgets import QWidget

from widget_test import WidgetTest
from ayon_ui_qt.components.user_image import AYUserImage
from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.label import AYLabel


class UserImageTest(WidgetTest):
    """Tests AYUserImage with initials, highlight, and outline variants."""

    size = (500, 160)
    tolerance = 0.0

    def build(self) -> QWidget:
        root = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=12,
        )

        row1 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=16,
        )
        row1.add_widget(AYLabel("highlight=False:"))
        row1.add_widget(AYUserImage(name="jd",   full_name="John Doe",   size=40, highlight=False))
        row1.add_widget(AYUserImage(name="ab",   full_name="Alice Brown", size=40, highlight=False))
        row1.add_widget(AYUserImage(name="?",    size=32, highlight=False))
        row1.addStretch(1)
        root.add_widget(row1)

        row2 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=16,
        )
        row2.add_widget(AYLabel("highlight=True:"))
        row2.add_widget(AYUserImage(name="jd",   full_name="John Doe",   size=40, highlight=True))
        row2.add_widget(AYUserImage(name="ab",   full_name="Alice Brown", size=40, highlight=True))
        row2.addStretch(1)
        root.add_widget(row2)

        row3 = AYContainer(
            layout=AYContainer.Layout.HBox,
            layout_margin=0,
            layout_spacing=16,
        )
        row3.add_widget(AYLabel("outline=False:"))
        row3.add_widget(AYUserImage(name="jd", full_name="John Doe", size=40, outline=False))
        row3.add_widget(AYUserImage(name="ab", size=40, outline=False, highlight=True))
        row3.addStretch(1)
        root.add_widget(row3)

        return root

    def steps(self):
        return []

from __future__ import annotations

import os

from qtpy import QtCore, QtGui, QtWidgets

from .. import get_ayon_style, get_ayon_style_data
from ..color_utils import compute_color_for_contrast
from ..variants import QPushButtonVariants

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon


class AYButton(QtWidgets.QPushButton):
    Variants = QPushButtonVariants

    def __init__(
        self,
        *args,
        variant: Variants = Variants.Surface,
        icon: str | None = None,
        icon_size: int = 24,
        icon_color: str | None = None,
        checkable=False,
        tooltip: str = "",
        name_id: str = "",
        contrast_color: QtGui.QColor | None = QtGui.QColor(),
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setStyle(get_ayon_style())
        self.setCheckable(checkable)

        # Convert enum to string if needed
        style_dict = get_ayon_style_data("QPushButton", variant.value)

        self._icon = icon
        self._variant_str = variant.value
        self._icon_color = QtGui.QColor(
            icon_color or style_dict.get("color", "#ffffff")
        )
        # Adjust the icon color to have enough contrast with the background
        self._contrast_color = contrast_color
        if (
            isinstance(contrast_color, QtGui.QColor)
            and contrast_color.isValid()
        ):
            self._icon_color = compute_color_for_contrast(
                contrast_color.toTuple(),
                self._icon_color.toTuple(),
                min_contrast_ratio=7,
            )
        # compute a readable icon hover color
        self._icon_hover_color = self._icon_color
        icon_hover_bg = style_dict.get("hover", {}).get("background-color")
        if isinstance(icon_hover_bg, str):
            self._icon_hover_color = compute_color_for_contrast(
                QtGui.QColor(icon_hover_bg).toTuple(),
                self._icon_color.toTuple(),
                min_contrast_ratio=7,
            )

        self._icon_size = icon_size
        self._tooltip = tooltip

        if self._icon:
            self.set_icon(self._icon)

        if self._tooltip:
            self.setToolTip(self._tooltip)

        self._name_id = ""
        if name_id:
            self.setObjectName(name_id)
            self._name_id = name_id

    @property
    def contrast_color(self):
        return self._contrast_color

    def sizeHint(self) -> QtCore.QSize:
        if self.testAttribute(QtCore.Qt.WidgetAttribute.WA_StyleSheet):
            option = QtWidgets.QStyleOptionButton()
            self.initStyleOption(option)
            return get_ayon_style().sizeFromContents(
                QtWidgets.QStyle.ContentsType.CT_PushButton,
                option,
                self.rect().size(),
                self,
            )
        return super().sizeHint()

    def paintEvent(self, arg__1: QtGui.QPaintEvent) -> None:
        if self.testAttribute(QtCore.Qt.WidgetAttribute.WA_StyleSheet):
            p = QtGui.QPainter(self)
            option = QtWidgets.QStyleOptionButton()
            self.initStyleOption(option)
            # override rect set by stylesheet
            size = self.sizeHint()
            self.setFixedSize(size)
            option.rect = QtCore.QRect(0, 0, size.width(), size.height())
            # draw
            return get_ayon_style().drawControl(
                QtWidgets.QStyle.ControlElement.CE_PushButton, option, p, self
            )
        super().paintEvent(arg__1)

    def set_icon(self, icon_name: str):
        self._icon = icon_name
        # icon conventions
        #   State.Off: checkable off
        #   State.On: checkable on
        #   State.Active: hover
        icn = get_icon(
            icon_name_off=self._icon,
            color_off=self._icon_color,
            icon_name_on=self._icon,
            color_on=self._icon_hover_color,
        )
        self.setIcon(icn)


# TEST =======================================================================


if __name__ == "__main__":
    from ..tester import Style, test
    from .container import AYContainer

    def _build_test():
        # Create and show the test widget
        widget = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant=AYContainer.Variants.High,
            layout_spacing=10,
            layout_margin=10,
        )

        variants = [v for v in QPushButtonVariants]

        l1 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            parent=widget,
            layout_spacing=10,
            layout_margin=10,
        )
        for i, var in enumerate(variants):
            b = AYButton(
                f"{var.value} button",
                variant=var,
                tooltip=f"{var.value}",
            )
            l1.add_widget(b)

        l2 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            parent=widget,
            layout_spacing=10,
            layout_margin=10,
        )
        for i, var in enumerate(variants):
            b = AYButton(
                f"{var.value} button",
                variant=var,
                icon="add",
                tooltip=f"{var.value}",
            )
            l2.add_widget(b)

        l3 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            parent=widget,
            layout_spacing=10,
            layout_margin=10,
        )
        for i, var in enumerate(variants):
            b = AYButton(
                variant=var,
                icon="home",
                tooltip=f"{var.value}",
            )
            l3.add_widget(b)
        l3.addStretch(1)

        widget.add_widget(l1)
        widget.add_widget(l2)
        widget.add_widget(l3)

        return widget

    os.environ["QT_SCALE_FACTOR"] = "1"
    test(_build_test, style=Style.AyonStyleOverCSS)

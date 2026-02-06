"""AYLineEdit component module."""

from __future__ import annotations

from qtpy.QtCore import Qt, QRectF
from qtpy.QtGui import QPainter, QPaintEvent, QColor, QPalette, QPen
from qtpy.QtWidgets import (
    QLineEdit,
    QStyle,
    QStyleOptionFrame,
    QStyleOptionFocusRect,
    QWidget,
)

from .. import get_ayon_style
from ..variants import QLineEditVariants
from .frame import AYFrame


class AYLineEdit(QLineEdit):
    """Custom styled line edit component.

    Inherits from QLineEdit and uses the AYON style system for rendering.
    Supports variants and overrides paintEvent to bypass stylesheets.

    Args:
        parent: Parent widget.
        placeholder: Placeholder text to display when empty.
        variant: Visual style variant.
        name_id: Object name for identification.
    """

    Variants = QLineEditVariants

    def __init__(
        self,
        parent: QWidget | None = None,
        placeholder: str = "",
        variant: QLineEditVariants = QLineEditVariants.Default,
        name_id: str = "",
    ) -> None:
        super().__init__(parent)
        self.setStyle(get_ayon_style())

        self._variant_str = variant.value

        if placeholder:
            self.setPlaceholderText(placeholder)

        if name_id:
            self.setObjectName(name_id)

        # Enable focus tracking
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Override paint event to use custom styling.

        This bypasses any stylesheet that may be applied and uses
        the AYON style system for rendering.

        Args:
            event: The paint event.
        """
        if self.testAttribute(Qt.WidgetAttribute.WA_StyleSheet):
            # QLineEdit has a pretty complicated paintEvent that we don't want to
            # interfere with too much. If a stylesheet is applied, we'll just let
            # it handle the painting and draw the focus frame ourselves.

            super().paintEvent(event)

            # do our stuff
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Create style option for the line edit
            option = QStyleOptionFrame()
            self.initStyleOption(option)

            opt = QStyleOptionFocusRect()
            opt.initFrom(self)

            if option.state & QStyle.StateFlag.State_HasFocus:
                style = get_ayon_style().model.get_style(
                    "QLineEdit", variant=self._variant_str
                )
                # draw a first rect outline to cover the factory focus frame.
                # use the parent's background color
                pw = self.parentWidget()
                if pw:
                    if isinstance(pw, AYFrame):
                        st2 = get_ayon_style().model.get_style(
                            "QFrame", variant=pw._variant_str
                        )
                        bgc = st2["background-color"]
                    else:
                        bgc = pw.palette().color(QPalette.ColorRole.Window)
                else:
                    bgc = style["background-color"]
                pen = QPen(QColor(bgc))
                pen.setWidth(4)
                painter.setPen(pen)
                painter.drawRect(option.rect)

                # draw our focus frame
                focus_outline_width = style.get("focus-outline-width", 2)
                focus_outline_color = QColor(
                    style.get("focus-outline-color", "#aaaaaa")
                )
                focus_pen = QPen(focus_outline_color)
                focus_pen.setWidth(focus_outline_width)
                painter.setPen(focus_pen)
                half_width = focus_outline_width / 2
                rect = QRectF(option.rect).adjusted(
                    half_width,
                    half_width,
                    -half_width,
                    -half_width,
                )
                radius = style.get("border-radius", 0)
                painter.drawRoundedRect(rect, radius, radius)
            return

        super().paintEvent(event)


if __name__ == "__main__":
    from .container import AYContainer
    from ..tester import test

    def _build() -> QWidget:
        container = AYContainer(
            variant=AYContainer.Variants.Low,
            layout=AYContainer.Layout.HBox,
            layout_margin=20,
        )
        container.setMinimumWidth(300)

        for variant in QLineEditVariants:
            line_edit = AYLineEdit(
                placeholder="Enter text here",
                variant=variant,
            )
            container.add_widget(line_edit)

        return container

    test(_build)

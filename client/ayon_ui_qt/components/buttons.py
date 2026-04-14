from __future__ import annotations

import logging
import os
from typing import Callable

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

from ..style import get_ayon_style, get_ayon_style_data
from ..color_utils import compute_color_for_contrast
from ..variants import QFrameVariants, QPushButtonVariants
from .container import AYContainer

logger = logging.getLogger(__name__)

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
        icon_on: str | None = None,
        icon_size: int = 16,
        icon_color: str | None = None,
        icon_fill=False,
        checkable=False,
        tooltip: str = "",
        name_id: str = "",
        contrast_color: QtGui.QColor | None = QtGui.QColor(),
        label_alignment: QtCore.Qt.AlignmentFlag | None = None,
        fixed_width: bool | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setCheckable(checkable)

        # Convert enum to string if needed
        style_dict = get_ayon_style_data("QPushButton", variant.value)

        self._icon = icon
        self._icon_on = icon_on or icon
        self._variant_str = variant.value
        self._icon_color = QtGui.QColor(
            icon_color or style_dict.get("color", "#ffffff")
        )
        self._icon_fill = icon_fill
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
        if isinstance(icon_hover_bg, str) and self._icon_color.isValid():
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

        self._label_alignment = label_alignment

        self._name_id = ""
        if name_id:
            self.setObjectName(name_id)
            self._name_id = name_id

        use_fixed_width = (
            style_dict.get("fixed-width", True)
            if fixed_width is None
            else fixed_width
        )
        if use_fixed_width:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
        else:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )

        self.setStyle(get_ayon_style())

    @property
    def contrast_color(self):
        return self._contrast_color

    def initStyleOption(self, option: QtWidgets.QStyleOptionButton) -> None:
        super().initStyleOption(option)
        option.iconSize = QtCore.QSize(self._icon_size, self._icon_size)

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
        p = QtGui.QPainter(self)
        option = QtWidgets.QStyleOptionButton()
        self.initStyleOption(option)
        # override rect set by stylesheet
        size = self.sizeHint()
        if (
            self.sizePolicy().horizontalPolicy()
            == QtWidgets.QSizePolicy.Policy.Fixed
        ):
            self.setFixedSize(size)
            option.rect = QtCore.QRect(0, 0, size.width(), size.height())
        else:
            self.setFixedHeight(size.height())  # draw
        return get_ayon_style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_PushButton, option, p, self
        )

    def set_icon(self, icon_name: str):
        self._icon = icon_name
        # icon conventions
        #   State.Off: checkable off
        #   State.On: checkable on
        #   State.Active: hover
        if self.isCheckable():
            icn = get_icon(
                icon_name_off=self._icon,
                color_off=self._icon_color,
                icon_name_on=self._icon_on,
                color_on=self._icon_color,
                fill=self._icon_fill,
            )
        else:
            icn = get_icon(
                icon_name_off=self._icon,
                color_off=self._icon_color,
                icon_name_on=self._icon,
                color_on=self._icon_hover_color,
                fill=self._icon_fill,
            )
        self.setIcon(icn)


class _ButtonMenuDropdown(AYContainer):
    """Floating dropdown popup for AYButtonMenu.

    A frameless popup QFrame that is shown below (or above, if not
    enough space) the parent button. It closes when it loses focus or
    the user presses Escape.

    Signals:
        popup_closed: Emitted when the popup is hidden/closed.
    """

    popup_closed = QtCore.Signal()

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize the dropdown popup frame.

        Args:
            parent: Optional parent widget (used for style inheritance).
        """
        super().__init__(
            parent,
            variant=AYContainer.Variants.Low_Framed_Thin,
            layout=AYContainer.Layout.VBox,
            layout_margin=10,
            layout_spacing=5,
        )

        self.setStyle(get_ayon_style())

        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

    def paintEvent(self, arg__1: QtGui.QPaintEvent) -> None:
        """Paint the frame using the AYON style.

        Args:
            arg__1: The paint event.
        """
        p = QtGui.QPainter(self)
        option = QtWidgets.QStyleOptionFrame()
        self.initStyleOption(option)
        get_ayon_style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_ShapedFrame,
            option,
            p,
            self,
        )

    def show_below(self, widget: QtWidgets.QWidget) -> None:
        """Position and show the popup below (or above) the widget.

        The popup is left-aligned with the widget's left edge. If there
        is not enough space below on the screen, the popup is shown
        above instead.

        Args:
            widget: The reference widget to position against.
        """
        global_pos = widget.mapToGlobal(QtCore.QPoint(0, widget.height() + 2))
        self.adjustSize()

        screen = QtWidgets.QApplication.screenAt(global_pos)
        if screen:
            screen_geo = screen.availableGeometry()

            # Shift left if popup would overflow right edge
            if global_pos.x() + self.width() > screen_geo.right():
                global_pos.setX(screen_geo.right() - self.width())

            # Show above if not enough vertical space below
            popup_bottom = global_pos.y() + self.height()
            if popup_bottom > screen_geo.bottom():
                above_y = (
                    widget.mapToGlobal(QtCore.QPoint(0, 0)).y() - self.height()
                )
                global_pos.setY(above_y)

        self.move(global_pos)
        self.show()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Close on Escape key.

        Args:
            event: The key event.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Emit popup_closed when the popup is hidden.

        Args:
            event: The close event.
        """
        self.popup_closed.emit()
        super().closeEvent(event)


class AYButtonMenu(AYButton):
    """A push button that shows a floating dropdown panel when clicked.

    When clicked, the button displays a ``QFrame`` popup positioned
    directly below it (or above when screen space is insufficient). The
    popup contents are provided by a caller-supplied
    ``populate_callback`` which receives the dropdown ``QFrame``
    container.

    Clicking the button again or clicking outside the popup closes the
    dropdown.

    Example::

        def populate(container: QtWidgets.QFrame) -> None:
            btn = QPushButton("Option A", container)
            container.layout().addWidget(btn)

        menu_btn = AYButtonMenu("Options", populate_callback=populate)

    Signals:
        menu_opened: Emitted when the dropdown is shown.
        menu_closed: Emitted when the dropdown is hidden.
    """

    menu_opened = QtCore.Signal()
    menu_closed = QtCore.Signal()

    def __init__(
        self,
        *args,
        populate_callback: Callable[[AYContainer], None],
        **kwargs,
    ) -> None:
        """Initialize the AYButtonMenu.

        Args:
            *args: Positional arguments forwarded to ``AYButton``.
            populate_callback: A callable that receives the dropdown
                ``QFrame`` container and is responsible for adding
                child widgets to it.
            **kwargs: Keyword arguments forwarded to ``AYButton``.
        """
        super().__init__(*args, **kwargs)

        self._populate_callback = populate_callback
        self._menu_open: bool = False

        self._dropdown = _ButtonMenuDropdown(self)
        self._populate_callback(self._dropdown)
        self._dropdown.popup_closed.connect(self._on_popup_closed)

        self.clicked.connect(self._on_button_clicked)

    # --- Event handlers ---

    def _on_button_clicked(self) -> None:
        """Toggle the dropdown popup visibility."""
        if self._menu_open:
            self._dropdown.close()
        else:
            self._menu_open = True
            self.menu_opened.emit()
            self._dropdown.show_below(self)

    def _on_popup_closed(self) -> None:
        """Update state when the popup signals it has closed."""
        self._menu_open = False
        self.menu_closed.emit()


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
        for var in variants:
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
        for var in variants:
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
        for var in variants:
            b = AYButton(
                variant=var,
                icon="home",
                tooltip=f"{var.value}",
            )
            l3.add_widget(b)
        l3.addStretch(1)

        l4 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            parent=widget,
            layout_spacing=10,
            layout_margin=10,
        )

        def populate_menu(container: AYContainer) -> None:
            layout = container.layout()
            assert layout is not None
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(5)
            for i in range(5):
                btn = AYButton(
                    f"Option {i + 1}",
                    parent=container,
                    variant=AYButton.Variants.Text,
                    icon=f"counter_{i + 1}",
                    checkable=True,
                )
                layout.addWidget(btn)

        menu_btn = AYButtonMenu(
            "Menu Button",
            variant=QPushButtonVariants.Filled,
            icon="layers",
            populate_callback=populate_menu,
        )
        l4.add_widget(menu_btn)
        l4.addStretch(1)

        widget.add_widget(l1)
        widget.add_widget(l2)
        widget.add_widget(l3)
        widget.add_widget(l4)

        return widget

    os.environ["QT_SCALE_FACTOR"] = "1"
    test(_build_test, style=Style.AyonStyleOverCSS)

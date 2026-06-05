"""Visual regression tests for QMenu styled via MenuDrawer."""

from __future__ import annotations

from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QApplication, QWidget

from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.label import AYLabel
from ayon_ui_qt.style import get_ayon_style
from tests.utils.composite_widget import CompositeWidget
from widget_test import WidgetTest


class _CompositeMenuWidget(CompositeWidget):
    """Composite widget that includes a QMenu popup in its grab().

    Args:
        menu: The ``QMenu`` instance whose popup will be composited.
        parent: Optional parent widget.
    """

    def __init__(
        self,
        menu: QtWidgets.QMenu,
        parent: QWidget | None = None,
    ) -> None:
        def popup_pos() -> QtCore.QPoint:
            if not menu.isVisible():
                return QtCore.QPoint(0, 0)
            global_pos = menu.mapToGlobal(QtCore.QPoint(0, 0))
            return self.mapFromGlobal(global_pos)

        super().__init__(
            widgets=[(menu, popup_pos)],
            parent=parent,
        )


class MenuTest(WidgetTest):
    """Tests QMenu painting via MenuDrawer across item types."""

    size = (400, 420)
    tolerance = 0.0

    def build(self) -> QWidget:
        # Build the menu with multiple item types
        style = get_ayon_style()

        self._menu = QtWidgets.QMenu()
        self._menu.setStyle(style)

        self._menu.addAction("Normal item")
        self._menu.addAction("Another item")

        # Checked item
        checked_action = self._menu.addAction("Checked item")
        checked_action.setCheckable(True)
        checked_action.setChecked(True)

        # Disabled item
        disabled_action = self._menu.addAction("Disabled item")
        disabled_action.setEnabled(False)

        self._menu.addSeparator()

        # Submenu
        submenu = QtWidgets.QMenu("Submenu")
        submenu.setStyle(style)
        submenu.addAction("Sub-action A")
        submenu.addAction("Sub-action B")
        self._menu.addMenu(submenu)
        self._submenu = submenu

        self._menu.addAction("After separator")

        # Container to serve as background
        inner = AYContainer(
            layout=AYContainer.Layout.VBox,
            layout_margin=20,
            layout_spacing=10,
        )
        inner.add_widget(AYLabel("Right-click context menu test:"))
        inner.add_widget(AYLabel("Steps will open the styled QMenu below"))

        root = _CompositeMenuWidget(self._menu, parent=None)
        lyt = QtWidgets.QVBoxLayout(root)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.addWidget(inner)

        self.widget = root
        return self.widget

    def wait_loaded(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        QApplication.processEvents()

    def show_menu(self) -> None:
        """Open the menu at a fixed position inside the composite widget."""
        self._menu.popup(self.widget.mapToGlobal(QtCore.QPoint(20, 60)))
        QApplication.processEvents()

    def steps(self):
        return [self.show_menu]

    def cleanup(self, step_name: str) -> None:
        if self._menu.isVisible():
            self._menu.hide()
            QApplication.processEvents()

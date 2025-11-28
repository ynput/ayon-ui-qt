"""AYON UI Qt - A Qt Widget library styled for AYON.

This module provides Qt widgets that match AYON's frontend design system,
enabling consistent UI across all AYON tools and applications.

Example:
    >>> from ayon_ui_qt import AYButton, AYContainer, style_widget_and_siblings
    >>> from ayon_ui_qt.components import AYLabel, AYTextBox
    >>>
    >>> # Create styled widgets
    >>> button = AYButton("Click me", variant="filled")
    >>> container = AYContainer(layout=AYContainer.Layout.VBox)
    >>>
    >>> # Apply AYON styling to widget tree
    >>> style_widget_and_siblings(my_widget)
"""
from __future__ import annotations

import copy

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget, QApplication

from .version import __version__
from .ayon_style import AYONStyle

_ayon_style_instance: AYONStyle | None = None


def get_ayon_style() -> AYONStyle:
    """Get the singleton AYONStyle instance.

    Returns:
        The singleton AYONStyle instance.
    """
    global _ayon_style_instance
    if _ayon_style_instance is None:
        _ayon_style_instance = AYONStyle()
    return _ayon_style_instance


def style_widget_and_siblings(widget: QWidget, fix_app: bool = True) -> None:
    """Apply AYON style to a widget and its siblings recursively.

    Removes any existing stylesheets and applies the AYON QStyle
    to the given widget and all its sibling widgets (widgets that
    share the same parent), including all their nested children
    even if they are in QLayouts.

    Args:
        widget: The widget whose siblings (and itself) will be styled.
        fix_app: Whether to temporarily remove and restore app stylesheet.
    """

    def _collect_widgets(w: QWidget, seen: set[int]) -> None:
        """Recursively collect all widgets including those in layouts."""
        if id(w) in seen:
            return

        seen.add(id(w))
        widgets_to_style.append(w)

        # Collect direct widget children
        for child in w.children():
            if isinstance(child, QWidget):
                _collect_widgets(child, seen)

        # Collect widgets from layouts
        if (layout := w.layout()) is not None:
            for i in range(layout.count()):
                if (item := layout.itemAt(i)) and (
                    item_widget := item.widget()
                ):
                    _collect_widgets(item_widget, seen)

    # Determine root widgets: siblings if parent exists, otherwise just widget
    root_widgets = [widget]

    # Collect all widgets recursively
    seen_widgets: set[int] = set()
    widgets_to_style: list[QWidget] = []
    for w in root_widgets:
        _collect_widgets(w, seen_widgets)

    qss = None
    app = QApplication.instance()
    if fix_app and app and isinstance(app, QApplication):
        qss = copy.copy(app.property("styleSheet"))

    if fix_app and qss and isinstance(app, QApplication):
        app.setStyleSheet("")

    widget.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation, False)

    # Apply style to all collected widgets
    style = get_ayon_style()
    for w in widgets_to_style:
        w.style().unpolish(w)
        w.setStyle(style)

    if fix_app and qss and isinstance(app, QApplication):
        app.setStyleSheet(qss)


# Convenience imports for commonly used components
# These are lazy-loaded to avoid circular imports

__all__ = [
    "__version__",
    "AYONStyle",
    "get_ayon_style",
    "style_widget_and_siblings",
]
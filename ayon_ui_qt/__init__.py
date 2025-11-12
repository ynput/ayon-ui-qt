from __future__ import annotations

import collections
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget, QApplication, QMainWindow, QDockWidget


from .ayon_style import AYONStyle

_ayon_style_instance: AYONStyle | None = None
_app_stylesheet_cleared: bool = False


def get_ayon_style() -> AYONStyle:
    """Get the singleton AYONStyle instance.

    Returns:
        The singleton AYONStyle instance.
    """
    global _ayon_style_instance
    if _ayon_style_instance is None:
        _ayon_style_instance = AYONStyle()
    return _ayon_style_instance


def style_widget_and_siblings(widget: QWidget, fix_app=True) -> None:
    """Apply AYON style to a widget and its children recursively.

    LEGACY: Consider using style_widget() or style_buttons_only() for better performance.

    Args:
        widget: The widget to style along with all its children.
        fix_app: If True, temporarily clears application stylesheet during styling.
        skip_types: Optional tuple of widget types to skip (e.g., (QMainWindow, QDockWidget)).
    """
    # Get style once at the start for efficiency
    style = get_ayon_style()

    # Collect all widgets using BFS
    seen: set[int] = set()
    to_style: list[QWidget] = []
    queue = collections.deque([widget])

    while queue:
        w = queue.popleft()
        widget_id = id(w)

        if widget_id in seen:
            continue

        seen.add(widget_id)
        to_style.append(w)

        # Add children - wrap in try/except for deleted widgets
        try:
            for child in w.children():
                if isinstance(child, QWidget):
                    queue.append(child)
        except RuntimeError:
            pass

        # Add layout widgets - wrap in try/except for deleted widgets
        try:
            layout = w.layout()
            if layout is not None:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item:
                        item_widget = item.widget()
                        if item_widget:
                            queue.append(item_widget)
        except RuntimeError:
            pass

    # Handle app stylesheet if needed - clear only once globally
    global _app_stylesheet_cleared

    if fix_app and not _app_stylesheet_cleared:
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            qss = app.property("styleSheet")
            if isinstance(qss, str) and qss.strip():
                app.setStyleSheet("")  # Clear once, never restore
                _app_stylesheet_cleared = True

    widget.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation, False)

    # Apply style to all collected widgets with error handling
    for w in to_style:
        try:
            current_style = w.style()
            # Only unpolish/setStyle if different style - major performance improvement
            if current_style is not style:
                current_style.unpolish(w)
                w.setStyle(style)
        except RuntimeError:
            # Widget was deleted, skip it
            pass

from __future__ import annotations

from qtpy.QtWidgets import QWidget

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


def style_widget_and_siblings(widget: QWidget) -> None:
    """Apply AYON style to a widget and its siblings recursively.

    Removes any existing stylesheets and applies the AYON QStyle
    to the given widget and all its sibling widgets (widgets that
    share the same parent), including all their nested children
    even if they are in QLayouts.

    Args:
        widget: The widget whose siblings (and itself) will be styled.
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
    parent = widget.parent()
    root_widgets = (
        [child for child in parent.children() if isinstance(child, QWidget)]
        if parent
        else [widget]
    )

    # Collect all widgets recursively
    seen_widgets: set[int] = set()
    widgets_to_style: list[QWidget] = []
    for w in root_widgets:
        _collect_widgets(w, seen_widgets)

    # Apply style to all collected widgets
    style = get_ayon_style()
    print(f"styling {len(widgets_to_style)} widgets")
    for w in widgets_to_style:
        w.setStyleSheet("")
        w.setStyle(style)

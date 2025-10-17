import logging
from .components.comment import AYComment, AYPublish

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def preprocess_payload(data: dict):
    """Preprocesses payload data to extract and parse comment activities.

    This function processes the input data to extract activities, specifically
    focusing on comment activities. It parses these activities using the
    AYComment class and returns a list of parsed comment objects.

    Args:
        data (dict): The input data containing project activities in a specific
            structure. Expected to have a nested structure with
            'data' -> 'project' -> 'activities' -> 'edges'.

    Returns:
        list: A list of parsed comment objects. Returns an empty list if no activities are found
            or if there's an error during processing.
    """
    try:
        activities: list = data["data"]["project"]["activities"]["edges"]
    except KeyError as err:
        logger.error(f"Could not extract activities: {err}")
        return []

    ui_data = []
    for act in activities:
        node = act.get("node")
        if node:
            activity_type = node.get("activityType", "")
            if activity_type == "comment":
                ui_data.append(AYComment.parse(node))
            elif activity_type == "version.publish":
                ui_data.append(AYPublish.parse(node))

    return ui_data


def clear_layout(layout):
    """Recursively deletes child QWidgets in the initial QLayout and in sub-layouts.

    This function handles all types of QLayout subclasses (QVBoxLayout, QHBoxLayout,
    QGridLayout, etc.) and safely deletes all child widgets while maintaining the
    integrity of the parent layout structure.

    Args:
        layout: QLayout instance to clear
    """
    if layout is None:
        return

    # print(f"layout = {layout}")

    # Work backwards through the layout to avoid index issues when removing items
    for i in reversed(range(layout.count())):
        item = layout.takeAt(i)
        if item is None:
            continue

        widget = item.widget()
        sub_layout = item.layout()

        if widget:
            # Recursively clear any layouts this widget might have
            # (in case it's a container widget with its own layouts)
            if hasattr(widget, "layout") and widget.layout():
                clear_layout(widget.layout())
            # Delete the widget
            widget.setParent(None)
            widget.deleteLater()
        elif sub_layout:
            # Recursively clear the sub-layout
            clear_layout(sub_layout)
            # Delete the layout
            sub_layout.deleteLater()

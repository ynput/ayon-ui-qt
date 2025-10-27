from __future__ import annotations

import logging
import json
from .data_models import CommentModel, VersionPublishModel, StatusChangeModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def preprocess_payload(
    activity_data: dict, project_data: dict
) -> list[CommentModel | VersionPublishModel | StatusChangeModel]:
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
        activities: list[dict] = activity_data["project"]["activities"]
    except KeyError as err:
        logger.error(f"Could not extract activities: {err}")
        return []

    users = {d["short_name"]: d for d in project_data.get("users", [])}

    ui_data = []
    nothing = "Not available"
    for act in activities:
        act_data = act.get("activityData", {})
        if isinstance(act_data, str):
            act_data = json.loads(act_data)
            act["activityData"] = act_data

        activity_type = act.get("activityType", "")

        user_name = act.get("author", {}).get("name", nothing)
        user_full_name = users.get(user_name, {}).get("full_name", user_name)
        date = act.get("updatedAt", nothing)

        if activity_type == "comment":
            ui_data.append(
                CommentModel(
                    user_full_name=user_full_name,
                    user_name=user_name,
                    comment=act.get("body", nothing),
                    comment_date=date,
                )
            )
        elif activity_type == "version.publish":
            ui_data.append(
                VersionPublishModel(
                    user_full_name=user_full_name,
                    user_name=user_name,
                    version=str(
                        act_data.get("origin", {}).get("name", nothing)
                    ),
                    product=str(
                        act_data.get("context", {}).get("productName", nothing)
                    ),
                    date=date,
                )
            )
        elif activity_type == "status.change":
            print(act.get("activityData", {}).get("oldValue", nothing))
            ui_data.append(
                StatusChangeModel(
                    user_full_name=user_full_name,
                    user_name=user_name,
                    product=nothing,
                    version=nothing,
                    old_status=str(act_data.get("oldValue", nothing)),
                    new_status=str(act_data.get("newValue", nothing)),
                    date=date,
                )
            )

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

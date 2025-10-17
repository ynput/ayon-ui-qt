import logging
import os

from qtpy import QtWidgets

from ayon_ui_qt.components.comment import AYComment
from ayon_ui_qt.components.container import AYContainer, AYFrame
from ayon_ui_qt.utils import clear_layout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity stream")


class AYActivityStream(AYContainer):
    def __init__(self, *args, **kwargs):
        self._activities = kwargs.pop("activities", {})
        self._category = kwargs.pop("category", "comment")

        super().__init__(
            *args,
            layout=AYContainer.Layout.VBox,
            variant="low",
            **kwargs,
        )

        self._build()
        self.update_stream(self._category, self._activities)

    def _build_stream(self):
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_ctnr = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant="low",
            layout_spacing=20,
        )

        self.scroll_area.setWidget(self.scroll_ctnr)
        self.scroll_area.setWidgetResizable(True)

        return self.scroll_area

    def _build(self):
        self.add_widget(self._build_stream())

    def update_stream(self, category, activities: list):
        clear_layout(self.scroll_ctnr)
        for event in activities:
            if event.type != category:
                continue
            self.scroll_ctnr.add_widget(AYComment(self, data=event))


#  TEST ======================================================================


if __name__ == "__main__":
    import json

    from ayon_ui_qt.tester import test
    from ayon_ui_qt.utils import preprocess_payload

    def build():
        data_file = os.path.join(
            os.path.dirname(__file__),
            "ayon_ui_qt",
            "resources",
            "GetActivities-recieved-data.json",
        )
        with open(data_file, "r") as fr:
            payload = json.load(fr)

        data = preprocess_payload(payload)

        w = AYActivityStream(activities=data)
        return w

    test(build)

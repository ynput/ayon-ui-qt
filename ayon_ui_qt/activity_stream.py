import os
from qtpy import QtWidgets
import logging

from ayon_ui_qt.layouts import AYVBoxLayout
from ayon_ui_qt.comment import AYCommentEditor, AYComment, CommentModel
from ayon_ui_qt.frame import AYFrame
from ayon_ui_qt.utils import clear_layout


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity panel")


class AYActivityStream(AYFrame):
    def __init__(self, *args, **kwargs):
        self._activities = kwargs.pop("activities", {})
        self._category = kwargs.pop("category", "comment")

        super().__init__(*args, bg=True, **kwargs)

        self._build()
        self.update_stream(self._category, self._activities)

    def _build_stream(self):
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_wdgt = QtWidgets.QWidget()

        self.stream_lyt = AYVBoxLayout(self.scroll_wdgt)

        self.scroll_wdgt.setLayout(self.stream_lyt)
        self.scroll_area.setWidget(self.scroll_wdgt)
        self.scroll_area.setWidgetResizable(True)

        return self.scroll_area

    def _build_editor(self):
        self.editor = AYCommentEditor(self)
        return self.editor

    def _build(self):
        lyt = AYVBoxLayout(self)
        self.setLayout(lyt)
        lyt.addWidget(self._build_stream())
        lyt.addWidget(self._build_editor())

    def update_stream(self, category, activities: list):
        clear_layout(self.stream_lyt)
        for event in activities:
            if event.type != category:
                continue
            self.stream_lyt.addWidget(AYComment(self, data=event))


#  TEST ======================================================================


if __name__ == "__main__":
    from ayon_ui_qt.tester import test
    from ayon_ui_qt.utils import preprocess_payload
    import json

    def build():
        data_file = os.path.join(
            os.path.dirname(__file__),
            "resources",
            "GetActivities-recieved-data.json",
        )
        with open(data_file, "r") as fr:
            payload = json.load(fr)

        data = preprocess_payload(payload)

        w = AYActivityStream(activities=data)
        return w

    test(build)

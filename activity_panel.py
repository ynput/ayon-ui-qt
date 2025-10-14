import logging
import os
from typing import Optional
from qtpy import QtCore, QtWidgets

from ayon_ui_qt.components.layouts import AYVBoxLayout
from ayon_ui_qt.components.frame import AYFrame
from ayon_ui_qt.components.text_box import AYTextBox
from detail_panel import AYDetailPanel
from activity_stream import AYActivityStream
from ayon_ui_qt.utils import preprocess_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity panel")


class ActivityPanelSignals(QtCore.QObject):
    # Signal emitted when comment button is clicked, passes markdown content
    comment_submitted = QtCore.Signal(str)  # type: ignore
    comment_edited = QtCore.Signal(int, str)  # type: ignore
    comment_deleted = QtCore.Signal(int, str)  # type: ignore
    priority_changed = QtCore.Signal(str)  # type: ignore
    assignee_changed = QtCore.Signal(str)  # type: ignore
    status_changed = QtCore.Signal(str)  # type: ignore


class ActivityPanel(AYFrame):
    signals = ActivityPanelSignals()

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        activities: Optional[list] = None,
        category: Optional[str] = None,
    ) -> None:
        self._activities = activities
        self._category = category

        super().__init__(parent, bg=True)

        self._build()

        # signals
        self.details.signals.view_changed.connect(
            lambda x: self.update_stream(x, self._activities)
        )

        self.update_stream(self._category, self._activities)

    def _build(self):
        self.main_lyt = AYVBoxLayout(self)

        # add header
        self.details = AYDetailPanel(self)
        self.main_lyt.addWidget(self.details, stretch=0)
        # add tab layout with hidden tabs
        self.stream = AYActivityStream(
            self, activities=self._activities, category=self._category
        )
        self.main_lyt.addWidget(self.stream, stretch=1)
        # add comment editor
        self.editor = AYTextBox()
        self.main_lyt.addWidget(self.editor, stretch=0)
        self.editor.signals.comment_submitted.connect(
            self.signals.comment_submitted.emit
        )

    def update_stream(self, category, activities: Optional[list] = None):
        if activities and activities != self._activities:
            self._activities = activities
        if self._activities:
            self.stream.update_stream(category, self._activities)


#  TEST =======================================================================


if __name__ == "__main__":
    from ayon_ui_qt.tester import test
    import json

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

        w = ActivityPanel(activities=data, category="comment")
        w.signals.comment_submitted.connect(
            lambda x: print(f"ActivityPanel.signals.comment_submitted: {x!r}")
        )

        return w

    test(build, use_css=False)

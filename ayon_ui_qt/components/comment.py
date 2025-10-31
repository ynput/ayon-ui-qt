from __future__ import annotations

from pathlib import Path
import json

from PySide6.QtCore import QEvent, Signal
from PySide6.QtGui import QEnterEvent
from qtpy.QtWidgets import QTextEdit, QMessageBox

from .buttons import AYButton
from .container import AYContainer, AYFrame
from .label import AYLabel
from .layouts import AYVBoxLayout, AYHBoxLayout
from .user_image import AYUserImage
from .combo_box import ALL_STATUSES
from ..data_models import (
    StatusChangeModel,
    StatusUiModel,
    VersionPublishModel,
    CommentModel,
)


# STATUS ---------------------------------------------------------------------


class AYStatusChange(AYFrame):
    def __init__(
        self,
        *args,
        data: StatusChangeModel | None = None,
        status_definitions: dict | None = None,
        **kwargs,
    ):
        self._data = data or StatusChangeModel()
        self.statuses = {
            kw["text"]: StatusUiModel(**kw)
            for kw in status_definitions or ALL_STATUSES
        }
        super().__init__(*args, variant="low", margin=0, **kwargs)
        self._build()

    @property
    def unknown_status(self):
        return StatusUiModel(
            "Unknown Status", "UKN", "shield_question", "#d05050"
        )

    def status_icon(self, status):
        model = self.statuses.get(status, self.unknown_status)
        return model.icon, model.color

    def _build_top_bar(self):
        small_icon_size = 14
        self.str_1 = AYLabel(
            f"{self._data.user_full_name} - {self._data.product} / "
            f"{self._data.version} - ",
            dim=True,
            rel_text_size=-2,
        )
        icon_name_0, icon_color_0 = self.status_icon(self._data.old_status)
        self.status_0 = AYLabel(
            self._data.old_status,
            icon=icon_name_0,
            icon_color=icon_color_0,
            icon_size=small_icon_size,
            icon_text_spacing=3,
            dim=True,
            rel_text_size=-2,
        )
        self.str_2 = AYLabel(" → ", dim=True, rel_text_size=-2)
        icon_name_1, icon_color_1 = self.status_icon(self._data.new_status)
        self.status_1 = AYLabel(
            self._data.new_status,
            icon=icon_name_1,
            icon_color=icon_color_1,
            icon_size=small_icon_size,
            icon_text_spacing=3,
            dim=True,
            rel_text_size=-2,
        )
        self.date = AYLabel(self._data.short_date, dim=True, rel_text_size=-2)
        cntr = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="low",
            layout_spacing=0,
        )
        cntr.add_widget(self.str_1, stretch=0)
        cntr.add_widget(self.status_0, stretch=0)
        cntr.add_widget(self.str_2, stretch=0)
        cntr.add_widget(self.status_1, stretch=0)
        cntr.addStretch()
        cntr.add_widget(self.date, stretch=0)
        return cntr

    def _build(self):
        lyt = AYVBoxLayout(self, margin=0, spacing=0)
        lyt.addWidget(self._build_top_bar(), stretch=0)

    @staticmethod
    def parse(data: dict):
        """Take a comment payload, and return a CommentModel dataclass.

        Args:
            data (dict): JSON payload from the activity stream.

        Returns:
            CommentModel: Contains all required comment data.
        """
        full_name = (
            data.get("author", {}).get("attrib", {}).get("fullName", "Someone")
        )

        activity_data = data.get("activityData", {})
        if isinstance(activity_data, str):
            activity_data = json.loads(activity_data)
        # print(f"STATUS CHANGE: {json.dumps(activity_data, indent=4)}")
        parents = activity_data.get("parents")
        product = [p for p in parents if p["type"] == "product"][0].get(
            "name", "UnknownProduct"
        )
        version = activity_data.get("origin", {}).get("name", "v???")

        return StatusChangeModel(
            user_full_name=full_name,
            user_name=full_name.split()[0],
            user_src="",
            product=product,
            version=version,
            old_status=activity_data.get("oldValue", "oldValue"),
            new_status=activity_data.get("newValue", "newValue"),
            date=data.get("updatedAt", "UnknownDate"),
        )


# PUBLISH ---------------------------------------------------------------------


class AYPublish(AYFrame):
    def __init__(
        self, *args, data: VersionPublishModel | None = None, **kwargs
    ):
        self._data = data or VersionPublishModel()
        super().__init__(*args, variant="low", margin=0, **kwargs)
        self._build()

    def _build_top_bar(self):
        self.user_icon = AYUserImage(
            parent=self,
            size=20,
            src=self._data.user_src,
            name=self._data.user_name,
            full_name=self._data.user_full_name,
            outline=False,
        )
        self.user_name = AYLabel(self._data.user_full_name, bold=True)
        self.date = AYLabel(self._data.short_date, dim=True, rel_text_size=-2)
        self.static = AYLabel(
            "published a version", dim=True, rel_text_size=-2
        )
        cntr = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="low",
            layout_spacing=8,
        )
        cntr.add_widget(self.user_icon, stretch=0)
        cntr.add_widget(self.user_name, stretch=0)
        cntr.add_widget(self.static, stretch=0)
        cntr.addStretch()
        cntr.add_widget(self.date, stretch=0)
        return cntr

    def _build(self):
        lyt = AYVBoxLayout(self, margin=0, spacing=0)
        lyt.addWidget(self._build_top_bar(), stretch=0)
        self.text_field = AYCommentField(
            text=f"{self._data.product}\n\n{self._data.version}",
            num_lines=3,
            read_only=True,
        )
        lyt.addWidget(self.text_field, stretch=0)

    def update_params(self, model: CommentModel):
        if self._data:
            self.user_icon.update_params(
                self._data.user_src, self._data.user_full_name
            )
            self.user_name.setText(self._data.user_name)
            self.date.setText(self._data.short_date)

    @staticmethod
    def parse(data: dict):
        """Take a comment payload, and return a CommentModel dataclass.

        Args:
            data (dict): JSON payload from the activity stream.

        Returns:
            CommentModel: Contains all required comment data.
        """
        full_name = (
            data.get("author", {}).get("attrib", {}).get("fullName", "Someone")
        )

        activity_data = data.get("activityData", {})
        if isinstance(activity_data, str):
            activity_data = json.loads(activity_data)
        context = activity_data.get("context")
        origin = activity_data.get("origin")

        return VersionPublishModel(
            user_full_name=full_name,
            user_name=full_name.split()[0],
            user_src="",
            version=origin.get("name", "no version"),
            product=context.get("productName", "no product name"),
            date=data.get("updatedAt", "not available"),
        )


# COMMENT ---------------------------------------------------------------------


class AYCommentField(QTextEdit):
    def __init__(self, *args, text="", read_only=False, num_lines=0, **kwargs):
        # remove our kwargs
        self._num_lines = num_lines
        self._text: str = text
        self._read_only: bool = read_only

        super().__init__(*args, **kwargs)
        self.setSizeAdjustPolicy(QTextEdit.SizeAdjustPolicy.AdjustToContents)
        self.setMarkdown(self._text)

        # configure
        if num_lines:
            height = int(self.fontMetrics().lineSpacing()) * num_lines + 8 + 8
            self.setFixedHeight(height)

        if not self._read_only:
            self.setPlaceholderText(
                "Comment or mention with @user, @@version, @@@task..."
            )
        self.setReadOnly(self._read_only)


class AYComment(AYFrame):
    comment_deleted = Signal(object)
    comment_edited = Signal(object)

    def __init__(self, *args, data: CommentModel | None = None, **kwargs):
        self._data = data if data else CommentModel()

        super().__init__(*args, variant="low", **kwargs)

        self._build()
        # configure
        if self._data:
            self.text_field.setMarkdown(self._data.comment)
            self.date.setText(self._data.short_date)

    def _build_top_bar(self):
        self.user_icon = AYUserImage(
            parent=self,
            size=20,
            src=self._data.user_src,
            name=self._data.user_name,
            full_name=self._data.user_full_name,
            outline=False,
        )
        self.user_name = AYLabel(self._data.user_full_name, bold=True)
        self.date = AYLabel(self._data.short_date, dim=True, rel_text_size=-2)
        cntr = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="low",
            layout_spacing=8,
        )
        cntr.addWidget(self.user_icon)
        cntr.addWidget(self.user_name)
        cntr.addStretch()
        cntr.addWidget(self.date)
        return cntr

    def _build_editor_toolbar(self):
        lyt = AYHBoxLayout()
        self.reaction = AYButton(
            variant="nav-small",
            icon="add_reaction",
            icon_color="#888",
            parent=self,
        )
        self.cancel_edit = AYButton("Cancel", variant="nav", parent=self)
        self.save_edit = AYButton("Save", variant="filled", parent=self)
        lyt.addWidget(self.reaction)
        lyt.addStretch(10)
        lyt.addWidget(self.cancel_edit)
        lyt.addWidget(self.save_edit)

        self.cancel_edit.clicked.connect(self._cancel_edit)
        self.cancel_edit.setVisible(False)
        self.save_edit.clicked.connect(self._save_edit)
        self.save_edit.setVisible(False)
        return lyt

    def _build_edit_buttons(self):
        self.edit_frame = AYContainer(
            layout=AYContainer.Layout.HBox, parent=self.top_line
        )
        bsize = 22
        self.del_button = AYButton(
            variant="nav-small", icon="delete", parent=self
        )
        self.del_button.setFixedSize(bsize, bsize)
        self.edit_button = AYButton(
            variant="nav-small",
            icon="edit_square",
            parent=self,
        )
        self.edit_button.setFixedSize(bsize, bsize)
        self.edit_frame.add_widget(self.del_button)
        self.edit_frame.add_widget(self.edit_button)
        self.edit_frame.setVisible(False)
        self.del_button.clicked.connect(self._confirm_delete)
        self.edit_button.clicked.connect(self._edit_comment)

    def _build(self):
        lyt = AYVBoxLayout(self, margin=0, spacing=0)
        lyt.addWidget(self._build_top_bar())
        self.text_field = AYCommentField(
            self, text=self._data.comment, read_only=True
        )

        editor_lyt = AYContainer(
            layout=AYContainer.Layout.VBox, variant="high"
        )
        self.top_line = AYFrame(variant="high")
        self.top_line.setFixedHeight(20)
        editor_lyt.add_widget(self.top_line, stretch=0)
        editor_lyt.add_widget(self.text_field, stretch=10)
        editor_lyt.add_layout(self._build_editor_toolbar(), stretch=0)
        lyt.addWidget(editor_lyt)
        self._build_edit_buttons()

    def _edit_comment(self):
        """Make the field editable, hide the edit/del buttons and show
        Save/Cancel."""
        self._show_edit_buttons(False)
        self.text_field.setReadOnly(False)
        self.cancel_edit.setVisible(True)
        self.save_edit.setVisible(True)

    def _cancel_edit(self):
        """Make rthe field read-only and restore text."""
        self.text_field.setReadOnly(True)
        self.cancel_edit.setVisible(False)
        self.save_edit.setVisible(False)
        self.text_field.setPlainText(self._data.comment)
        self._show_edit_buttons(True)

    def _save_edit(self):
        self.text_field.setReadOnly(True)
        self.cancel_edit.setVisible(False)
        self.save_edit.setVisible(False)
        self._show_edit_buttons(True)
        self._data.comment = self.text_field.toPlainText()
        self.comment_edited.emit(self._data)

    def _confirm_delete(self):
        mb = QMessageBox(
            text="Are you sure you want to delete this comment?",
            standardButtons=QMessageBox.StandardButton.Cancel
            | QMessageBox.StandardButton.Yes,  # type: ignore
            parent=self,
        )
        if mb.exec() == QMessageBox.StandardButton.Yes:
            self.comment_deleted.emit(self._data)

    def _show_edit_buttons(self, state):
        """show / hide edit buttons and position them."""
        if not self.text_field.isReadOnly():
            return
        self.edit_frame.setVisible(state)
        if state:
            fr = self.edit_frame.rect()
            vr = self.text_field.visibleRegion().boundingRect()
            self.edit_frame.move((vr.width() + vr.x()) - fr.width(), 0)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._show_edit_buttons(True)
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._show_edit_buttons(False)
        return super().leaveEvent(event)

    def update_params(self, model: CommentModel):
        if self._data:
            self.user_icon.update_params(
                self._data.user_src, self._data.user_full_name
            )
            self.user_name.setText(self._data.user_name)
            self.date.setText(self._data.short_date)

    @staticmethod
    def parse(data: dict):
        """Take a comment payload, and return a CommentModel dataclass.

        Args:
            data (dict): JSON payload from the activity stream.

        Returns:
            CommentModel: Contains all required comment data.
        """
        full_name = (
            data.get("author", {}).get("attrib", {}).get("fullName", "Someone")
        )
        return CommentModel(
            user_full_name=full_name,
            user_name=full_name.split()[0],
            user_src="",
            comment=data.get("body", ""),
            comment_date=data.get("updatedAt", "not available"),
        )


if __name__ == "__main__":
    from ..tester import Style, test
    from .container import AYContainer
    from .text_box import AYTextBox

    def build():
        rsrc_dir = Path(__file__).parent.parent / "resources"
        av1 = rsrc_dir / "avatar1.jpg"
        av2 = rsrc_dir / "avatar2.jpg"

        w = AYContainer(
            layout=AYContainer.Layout.VBox,
            # margin=8,
            layout_spacing=4,
            layout_margin=16,
            variant="low",
        )

        w.addWidget(
            AYComment(
                data=CommentModel(
                    user_src=str(av1),
                    user_full_name="Bob Morane",
                    comment="This is great !",
                )
            )
        )
        w.addWidget(
            AYComment(
                data=CommentModel(
                    user_src=(str(av2)),
                    user_full_name="Leia Organa",
                    comment="Can you avoid the dark side @Luke ?",
                )
            )
        )
        w.addWidget(
            AYComment(
                data=CommentModel(
                    user_full_name="Katniss Evergreen",
                    comment="One squirrel...\nTwo squirrels\nThree squirrels !",
                )
            )
        )
        w.addWidget(AYTextBox(num_lines=3))
        return w

    test(build, style=Style.Widget)

from __future__ import annotations

from pathlib import Path

from qtpy.QtCore import QEvent, Signal, Qt
from qtpy.QtGui import QEnterEvent, QTextDocument, QPixmap
from qtpy.QtWidgets import (
    QTextEdit,
    QMessageBox,
    QWidget,
    QLabel,
    QDialog,
    QSizePolicy,
    QVBoxLayout,
)

from .buttons import AYButton
from .container import AYContainer, AYFrame
from .label import AYLabel
from .layouts import AYVBoxLayout, AYHBoxLayout
from .user_image import AYUserImage
from .combo_box import ALL_STATUSES
from .comment_completion import (
    setup_user_completer,
    on_completer_text_changed,
    on_completer_activated,
    on_completer_key_press,
    format_comment_on_change,
    apply_web_markdown_formatting,
)
from ..data_models import (
    StatusChangeModel,
    StatusUiModel,
    VersionPublishModel,
    CommentModel,
    User,
)
from ..utils import color_blend


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
        cntr.setContentsMargins(0, 0, 0, 4)
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


# COMMENT ---------------------------------------------------------------------

MD_DIALECT = QTextDocument.MarkdownFeature.MarkdownDialectGitHub


class AYCommentField(QTextEdit):
    """Text field for comment display with markdown support."""

    def __init__(
        self,
        *args,
        text: str = "",
        read_only: bool = False,
        num_lines: int = 0,
        user_list: list[User] | None = None,
        model: CommentModel | None = None,
        **kwargs,
    ) -> None:
        # remove our kwargs
        self._num_lines = num_lines
        self._read_only: bool = read_only
        self._user_list: list[User] = user_list or []
        self._data = model
        self._bg_color = None

        super().__init__(*args, **kwargs)
        self.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        self.setSizeAdjustPolicy(QTextEdit.SizeAdjustPolicy.AdjustToContents)
        self.set_markdown(text)

        # configure
        if num_lines:
            height = int(self.fontMetrics().lineSpacing()) * num_lines + 8 + 8
            self.setFixedHeight(height)

        if not self._read_only:
            self.setPlaceholderText(
                "Comment or mention with @user, @@version, @@@task..."
            )
        self.setReadOnly(self._read_only)

        # Setup user completer
        setup_user_completer(
            self,
            self._on_completer_activated,
            self._on_text_changed,
        )

        # Connect text changed signal to format mentions
        self.document().contentsChanged.connect(
            lambda: format_comment_on_change(self)
        )

    def get_bg_color(self, base_color: str):
        if not self._bg_color:
            self._bg_color = base_color
            if self._data and self._data.category_color:
                self._bg_color = color_blend(
                    base_color, self._data.category_color, 0.1
                )
        return self._bg_color

    def set_markdown(self, md: str) -> None:
        """Set markdown content, supporting both standard markdown and web markdown.

        If text contains web markdown syntax (text\\n----, **bold**, _italic_, [link](url), `code`),
        it will be parsed and formatted accordingly with syntax removed.
        Otherwise, uses standard QTextDocument markdown.

        Args:
            md: Markdown text to display
        """
        # Check if text contains web markdown syntax
        has_web_markdown = any(
            pattern in md for pattern in ["\n----", "**", "_", "[", "`"]
        )

        if has_web_markdown:
            # Use web markdown formatting (removes syntax, applies formatting)
            self.set_web_markdown(md)
        else:
            # Use standard markdown
            self.document().setMarkdown(md, MD_DIALECT)

    def set_web_markdown(self, md: str, styles: dict | None = None) -> None:
        """Set markdown from web data with formatting.

        Removes markdown syntax (**text** becomes text with bold formatting).

        Args:
            md: Markdown text from web (**bold**, _italic_, [link](url), `code`)
            styles: Optional custom styles for formatting
        """
        apply_web_markdown_formatting(self, md, styles=styles)
        self.setReadOnly(self._read_only)

    def as_markdown(self) -> str:
        return self.document().toMarkdown(MD_DIALECT)

    def _on_text_changed(self) -> None:
        """Handle text changes to show/hide completer."""
        on_completer_text_changed(self)

    def _on_completer_activated(self, text: str) -> None:
        """Handle completer selection."""
        on_completer_activated(self, text)

    def keyPressEvent(self, event) -> None:
        """Handle key press events for completer."""
        if on_completer_key_press(self, event):
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press events to open links only in read-only mode."""
        # Only handle link clicks in read-only mode (display comments)
        if self.isReadOnly():
            # Get the character at the click position
            cursor = self.cursorForPosition(event.pos())
            char_format = cursor.charFormat()

            # Check if the clicked text is a link (has anchor href)
            if char_format.isAnchor() and char_format.anchorHref():
                import webbrowser
                url = char_format.anchorHref()
                webbrowser.open(url)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Change cursor to hand when hovering over links in read-only mode."""
        # Only show hand cursor in read-only mode (display comments)
        if self.isReadOnly():
            cursor = self.cursorForPosition(event.pos())
            char_format = cursor.charFormat()

            # Show hand cursor only for actual links with href
            if char_format.isAnchor() and char_format.anchorHref():
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)

        super().mouseMoveEvent(event)


class AYImageAttachment(AYLabel):
    """Widget to display an image attachment with thumbnail and full-size preview."""

    def __init__(
        self,
        parent: QWidget | None = None,
        image_path: str = "",
        thumb_path: str = "",
        max_width: int = 400,
        max_height: int = 300,
    ):
        super().__init__(parent)
        self._image_path = image_path
        self._thumb_path = thumb_path or image_path
        self._max_width = max_width
        self._max_height = max_height

        self.setScaledContents(False)
        self.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Set tooltip
        self.setToolTip("Click to view full size")

        # Load and display thumbnail
        self._load_thumbnail()

    def _load_thumbnail(self):
        """Load and display the thumbnail image."""
        if not self._thumb_path or not Path(self._thumb_path).exists():
            self.setText("Image not available")
            return

        pixmap = QPixmap(self._thumb_path)
        if pixmap.isNull():
            self.setText("Failed to load image")
            return

        # Scale pixmap to fit within max dimensions while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self._max_width,
            self._max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        """Handle click to show full-size image."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_full_size()
        super().mousePressEvent(event)

    def _show_full_size(self):
        """Show full-size image in a dialog that respects aspect ratio."""
        if not self._image_path or not Path(self._image_path).exists():
            QMessageBox.warning(
                self,
                "Image Not Available",
                "The full-size image is not available.",
            )
            return

        # Load the full-size image
        original_pixmap = QPixmap(self._image_path)

        if original_pixmap.isNull():
            QMessageBox.warning(
                self,
                "Image Load Error",
                "Failed to load the full-size image.",
            )
            return

        # Get screen dimensions
        screen_size = self.screen().availableGeometry()
        max_w = int(screen_size.width() * 0.8)
        max_h = int(screen_size.height() * 0.8)

        # Scale if too large for screen while maintaining aspect ratio
        display_pixmap = original_pixmap
        if original_pixmap.width() > max_w or original_pixmap.height() > max_h:
            display_pixmap = original_pixmap.scaled(
                max_w,
                max_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        dialog = QDialog(self)
        dialog.setWindowTitle("Image Preview")
        dialog.setModal(True)

        # Create layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create label to display image
        image_label = QLabel(dialog)
        image_label.setPixmap(display_pixmap)
        image_label.setScaledContents(False)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(image_label)

        # Set dialog size to match image
        dialog.resize(display_pixmap.size())

        # Show dialog
        dialog.exec()


class AYComment(AYFrame):
    """Enhanced comment widget that displays images from CommentModel.files."""

    comment_deleted = Signal(object)
    comment_edited = Signal(object)

    def __init__(
        self,
        *args,
        data: CommentModel | None = None,
        user_list: list[User] | None = None,
        **kwargs,
    ):
        self._data = data if data else CommentModel()
        self._user_list: list[User] = user_list or []
        self._bg_color = None

        super().__init__(
            *args,
            variant="low",
            bg_tint=self._data.category_color,
            **kwargs,
        )

        self._build()
        # configure
        if self._data:
            self.text_field.set_markdown(self._data.comment)
            self.date.setText(self._data.short_date)
            self.set_comment_category()
            self._build_image_attachments()

    def get_bg_color(self, base_color: str):
        if not self._bg_color:
            self._bg_color = base_color
            if self._data and self._data.category_color:
                self._bg_color = color_blend(
                    base_color, self._data.category_color, 0.1
                )
        return self._bg_color

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
        cntr.setContentsMargins(0, 0, 0, 4)
        cntr.add_widget(self.user_icon)
        cntr.add_widget(self.user_name)
        cntr.addStretch()
        cntr.add_widget(self.date)
        return cntr

    def _build_editor_toolbar(self):
        lyt = AYHBoxLayout()
        self.reaction = AYButton(
            variant="nav-small",
            icon="add_reaction",
            icon_color="#888",
            tooltip="Not Implemented Yet !",
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
            layout=AYContainer.Layout.HBox,
            bg_tint=self._data.category_color,
            parent=self.top_line,
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
        self.top_line.addStretch(100)
        self.top_line.add_widget(self.edit_frame)
        self.edit_frame.setVisible(False)
        self.del_button.clicked.connect(self._confirm_delete)
        self.edit_button.clicked.connect(self._edit_comment)

    def _build(self):
        self.main_lyt = AYVBoxLayout(self, margin=0, spacing=0)
        self.main_lyt.addWidget(self._build_top_bar())
        self.text_field = AYCommentField(
            self,
            text=self._data.comment,
            read_only=True,
            user_list=self._user_list,
            model=self._data,
        )

        editor_lyt = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant="high",
            bg_tint=self._data.category_color,
        )
        self.top_line = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="high",
            bg_tint=self._data.category_color,
        )
        self.images_container = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="high",
            bg_tint=self._data.category_color,
            layout_spacing=4,
            layout_margin=0,
        )
        self.images_container.setContentsMargins(0, 0, 0, 0)
        self.top_line.setFixedHeight(20)
        editor_lyt.add_widget(self.top_line, stretch=0)
        editor_lyt.add_widget(self.images_container, stretch=0)
        editor_lyt.add_widget(self.text_field, stretch=10)

        editor_lyt.add_layout(self._build_editor_toolbar(), stretch=0)
        self.main_lyt.addWidget(editor_lyt)
        self._build_edit_buttons()

    def _build_image_attachments(self):
        """Build and display image attachments as separate clickable widgets."""
        if (
            not self._data
            or not hasattr(self._data, "files")
            or not self._data.files
        ):
            return

        from .. import get_ayon_style

        style = get_ayon_style()
        for file_model in self._data.files:
            # Check if this file is marked as transparent in annotations
            is_transparent = False
            if hasattr(self._data, "annotations"):
                for annotation in self._data.annotations:
                    if file_model.id == annotation.transparent:
                        is_transparent = True
                        break

            if is_transparent:
                continue
            # Check if file has local_path
            if not hasattr(file_model, "local_path"):
                return

            # Check if path exists
            if not Path(file_model.local_path).exists():
                return

            # Get the text field width to scale images accordingly
            text_field_width = self.text_field.width()
            # Account for margins/padding and spacing between multiple images
            # Calculate how many images we'll have (not transparent)
            image_count = sum(
                1 for file in self._data.files
                if not any(
                    file.id == annotation.transparent
                    for annotation in (self._data.annotations or [])
                )
            )
            # Each image spacing is 4px (from layout_spacing)
            spacing_total = (image_count - 1) * 4
            max_image_width = max(
                int((text_field_width - spacing_total) / image_count)
                if image_count > 0 else 400,
                100  # Minimum width for images
            )

            thumb_path = getattr(file_model, "thumb_local_path", None)

            # Create image widget with dynamic width matching text field
            image_widget = AYImageAttachment(
                parent=self,
                image_path=file_model.local_path,
                thumb_path=thumb_path,
                max_width=max_image_width,
                max_height=800,
            )

            # Ensure the image widget is styled
            image_widget.setStyle(style)
            # Set fixed width to prevent expanding
            image_widget.setFixedWidth(max_image_width)
            # Set maximum height to maintain aspect ratio
            image_widget.setMaximumHeight(800)

            self.images_container.add_widget(
                image_widget, stretch=0, alignment=Qt.AlignmentFlag.AlignLeft
            )
        
        # Add stretch to push images to the left
        self.images_container.addStretch()

    def _edit_comment(self):
        """Make the field editable, hide the edit/del buttons and show
        Save/Cancel."""
        self._show_edit_buttons(False)
        self.text_field.setReadOnly(False)
        self.cancel_edit.setVisible(True)
        self.save_edit.setVisible(True)

    def _cancel_edit(self):
        """Make the field read-only and restore text."""
        self.text_field.setReadOnly(True)
        self.cancel_edit.setVisible(False)
        self.save_edit.setVisible(False)
        self.text_field.set_markdown(self._data.comment)
        self._show_edit_buttons(True)

    def _save_edit(self):
        self.text_field.setReadOnly(True)
        self.cancel_edit.setVisible(False)
        self.save_edit.setVisible(False)
        self._show_edit_buttons(True)
        self._data.comment = self.text_field.as_markdown()
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

    def set_comment_category(self):
        if not self._data.category:
            return
        cat = AYLabel(
            self._data.category,
            icon_color=self._data.category_color,
            variant="badge",
            rel_text_size=-2,
        )
        self.top_line.insert_widget(0, cat)

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

        w.add_widget(
            AYComment(
                data=CommentModel(
                    user_src=str(av1),
                    user_full_name="Bob Morane",
                    comment="This is great !",
                )
            )
        )
        w.add_widget(
            AYComment(
                data=CommentModel(
                    user_src=(str(av2)),
                    user_full_name="Leia Organa",
                    comment="Can you avoid the dark side @Luke ?",
                )
            )
        )
        w.add_widget(
            AYComment(
                data=CommentModel(
                    user_full_name="Katniss Evergreen",
                    comment=(
                        "Please check "
                        "[this link](https://doc.qt.io/qt-6/qtextdocument.html)\n\n"
                        "or [that one](https://doc.qt.io/qt-6/qtextblock.html#details) if need be. "
                        "maybe [a last URL](https://doc.qt.io/qt-6/qtextblock.html#details) ?"
                    ),
                )
            )
        )
        w.add_widget(AYTextBox(num_lines=3))
        return w

    test(build, style=Style.Widget)

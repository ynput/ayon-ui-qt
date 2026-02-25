"""Gallery dialog for navigating through activity thumbnails/images."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QKeyEvent, QPixmap
from qtpy.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GalleryDialog(QDialog):
    """Dialog for viewing and navigating through multiple images.

    This dialog provides a simple gallery view using standard Qt widgets,
    matching the official AYON style for image preview dialogs.

    Attributes:
        image_changed: Signal emitted when the current image changes.
            Emits the current index.

    Example:
        >>> images = [
        ...     ("/path/to/image1.png", "image1.png"),
        ...     ("/path/to/image2.png", "image2.png"),
        ... ]
        >>> dialog = GalleryDialog(images, current_index=0)
        >>> dialog.exec()
    """

    image_changed = Signal(int)

    def __init__(
        self,
        images: List[Tuple[str, str]],
        current_index: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the gallery dialog.

        Args:
            images: List of tuples (image_path, filename) for each image.
            current_index: Index of the image to show initially.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.images = images
        self.current_index = current_index

        self.setWindowTitle("Image Preview")
        self.setModal(True)

        # Apply AYON stylesheet if available
        try:
            from ayon_core import style
            self.setStyleSheet(style.load_stylesheet())
        except Exception:
            pass

        self._setup_ui()
        self._show_current_image()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components using standard Qt widgets."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image display area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        layout.addWidget(self.image_label, stretch=1)

        # Only show navigation controls if multiple images
        if len(self.images) > 1:
            # Navigation controls
            nav_widget = QWidget()
            nav_layout = QHBoxLayout(nav_widget)
            nav_layout.setContentsMargins(5, 5, 5, 5)
            nav_layout.setSpacing(5)

            # Previous button
            self.prev_btn = QPushButton("◀ Previous")
            self.prev_btn.setFixedWidth(100)
            self.prev_btn.clicked.connect(self._show_previous)
            nav_layout.addWidget(self.prev_btn)

            # Info label (counter and filename)
            self.info_label = QLabel()
            self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.info_label.setStyleSheet("font-size: 12px;")
            nav_layout.addWidget(self.info_label, stretch=1)

            # Next button
            self.next_btn = QPushButton("Next ▶")
            self.next_btn.setFixedWidth(100)
            self.next_btn.clicked.connect(self._show_next)
            nav_layout.addWidget(self.next_btn)

            layout.addWidget(nav_widget)

    def _show_current_image(self) -> None:
        """Display the current image with proper scaling."""
        if not self.images or self.current_index >= len(self.images):
            return

        image_path, filename = self.images[self.current_index]

        # Load the full-size image
        if not Path(image_path).exists():
            self.image_label.setText("Image not found")
            return

        original_pixmap = QPixmap(image_path)
        if original_pixmap.isNull():
            self.image_label.setText("Failed to load image")
            return

        # Get screen dimensions for sizing
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

        self.image_label.setPixmap(display_pixmap)

        # Set dialog size once on first image, then keep it consistent
        if not hasattr(self, '_dialog_size_set'):
            nav_height = 40 if len(self.images) > 1 else 0
            self.resize(max_w, max_h + nav_height)
            self._dialog_size_set = True

        # Update navigation controls if multiple images
        if len(self.images) > 1:
            # Update info label
            display_name = Path(filename).stem if filename else "Unknown"
            info_text = f"{self.current_index + 1} / {len(self.images)} - {display_name}"
            self.info_label.setText(info_text)

            # Update button states
            self.prev_btn.setEnabled(self.current_index > 0)
            self.next_btn.setEnabled(self.current_index < len(self.images) - 1)

        # Emit signal
        self.image_changed.emit(self.current_index)

    def _show_previous(self) -> None:
        """Show the previous image."""
        if self.current_index > 0:
            self.current_index -= 1
            self._show_current_image()

    def _show_next(self) -> None:
        """Show the next image."""
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self._show_current_image()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard navigation.

        Args:
            event: Key event to handle.
        """
        if event.key() == Qt.Key.Key_Left:
            self._show_previous()
        elif event.key() == Qt.Key.Key_Right:
            self._show_next()
        elif event.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)



if __name__ == "__main__":
    from pathlib import Path

    from ..tester import Style, test

    def build():
        rsrc_dir = Path(__file__).parent.parent / "resources"
        images = []

        # Add any available test images
        for img_file in rsrc_dir.glob("*.jpg"):
            images.append((str(img_file), img_file.name))
        for img_file in rsrc_dir.glob("*.png"):
            images.append((str(img_file), img_file.name))

        if not images:
            # Create dummy entries for testing
            images = [
                ("test1.png", "Test Image 1"),
                ("test2.png", "Test Image 2"),
            ]

        dialog = GalleryDialog(images, current_index=0)
        return dialog

    test(build, style=Style.AyonStyleOverCSS)


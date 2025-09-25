#!/usr/bin/env python3
"""Test script to demonstrate AYONStyle implementation replacing QSS."""

import os
import sys
from qtpy import QtCore, QtGui, QtWidgets

# Import our custom style and button
from ayon_ui_qt.ayon_style import AYONStyle
from ayon_ui_qt.buttons import AYButton, VARIANTS
from ayon_ui_qt.layouts import AYGridLayout, AYHBoxLayout, AYVBoxLayout
from ayon_ui_qt.label import AYLabel


def create_test_widget():
    """Create a test widget with all button variants using AYONStyle."""

    # Create main widget
    widget = QtWidgets.QFrame()
    widget.setWindowTitle("AYON Style Test - QStyle Implementation")
    widget.resize(1000, 400)

    # Create layout
    main_layout = AYVBoxLayout(widget, spacing=20, margin=20)

    # Add title
    title = AYLabel("AYON QStyle Implementation - Button Variants")
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(title)

    # Create sections for different button types
    sections = [
        ("Text Buttons", False, True),
        ("Icon + Text Buttons", True, True),
        ("Icon Only Buttons", True, False),
    ]

    for section_title, has_icon, has_text in sections:
        # Section header
        header = AYLabel(section_title)
        main_layout.addWidget(header)

        # Button layout
        button_layout = AYHBoxLayout(spacing=10)

        for variant in VARIANTS:
            # Create button with appropriate content
            kwargs = {"variant": variant}

            if has_text:
                kwargs["label"] = f"{variant.title()}"

            if has_icon:
                kwargs["icon"] = "add"

            button = AYButton(**kwargs)

            # Set the text and icon properly
            if has_text:
                button.set_label(f"{variant.title()}")
            if has_icon:
                button.set_icon("add")

            button_layout.addWidget(button)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    # Add spacing
    main_layout.addStretch()

    # Add information label
    info_label = AYLabel(
        "This demo uses pure QStyle implementation instead of QSS.\n"
        "All button styling is done through native Qt painting methods."
    )
    info_label.setStyleSheet("color: #888; font-size: 12px;")
    info_label.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(info_label)

    return widget


def test_ayon_style():
    """Test function compatible with the existing test framework."""
    def widget_creator():
        return create_test_widget()
    return widget_creator


def main():
    """Main function to run the test."""

    # Prevent scaling issues
    os.environ["QT_SCALE_FACTOR"] = "1"

    # Create application
    app = QtWidgets.QApplication(sys.argv)

    # Create and apply our custom style
    ayon_style = AYONStyle()
    app.setStyle(ayon_style)

    # Set a minimal background for better visibility
    app.setStyleSheet("""
        QWidget {
            background-color: #1e2329;
            color: #F4F5F5;
        }
        QLabel {
            color: #F4F5F5;
        }
    """)

    # Create and show test window
    widget = create_test_widget()
    widget.show()

    # Center the window on screen
    screen = app.primaryScreen().geometry()
    size = widget.geometry()
    widget.move(
        (screen.width() - size.width()) // 2,
        (screen.height() - size.height()) // 2
    )

    print("AYON QStyle test started. Close the window to exit.")
    print("This test demonstrates native Qt painting replacing QSS styles.")

    # Run application
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
import sys
from qtpy import QtWidgets
from ayon_ui_qt.ayon_style import AYONStyle

def test(test_widget, use_css=True):
    """Main function to run the Qt test."""
    app = QtWidgets.QApplication(sys.argv)

    if use_css:
        # Set a dark theme for the application
        ss = """
            QWidget {
                background-color: #1e1e1e;
                color: #F4F5F5;
                margin: 0px;
                padding: 0px;
                border: 0px;
            }
            QLabel {
                color: #F4F5F5;
            }
        """

        with open("ayon_ui_qt/old/output/complete_styles.qss", "r") as fr:
            ss += fr.read()

        app.setStyleSheet(ss)

    else:
        app.setStyle(AYONStyle())

    # Create and show the test widget
    widget = test_widget()

    widget.show()

    print("Qt widget test started. Close the window to exit.")
    return app.exec()

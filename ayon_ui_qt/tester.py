import sys
from enum import Enum
from pathlib import Path

from qtpy import QtWidgets

# from .ayon_style import AYONStyle
from . import style_widget_and_siblings, get_ayon_style


class Style(Enum):
    CSS = 0
    AyonStyle = 1
    Widget = 2


AWFUL_CSS = """
QWidget {
    background-color: #441e1e;
    color: #F4F5F5;
    margin: 0px;
    padding: 0px;
    border: 0px;
}
QLabel {
    color: #F4F5F5;
}
QPushButton {
    border-color: #acf;
    border-width: 2px;
    border-style: solid;
}
"""


def test(test_widget, style: Style = Style.Widget):
    """Main function to run the Qt test."""
    app = QtWidgets.QApplication(sys.argv)
    qcs = QtWidgets.QCommonStyle()
    app.setStyle(qcs)

    if style == Style.CSS:
        # Set a dark theme for the application
        ss = AWFUL_CSS

        fpath = Path(__file__).parent.joinpath(
            "old", "output", "complete_styles.qss"
        )
        with open(fpath, "r") as fr:
            ss += fr.read()

        app.setStyleSheet(ss)

    elif style == Style.AyonStyle:
        app.setStyle(get_ayon_style())

    # Create and show the test widget
    widget = test_widget()

    if style == Style.Widget:
        # add an awfull app css first to make sure it is overriden !
        app.setStyleSheet(AWFUL_CSS)
        # no app-level style
        style_widget_and_siblings(widget)

    widget.show()

    print("Qt widget test started. Close the window to exit.")
    return app.exec()

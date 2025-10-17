from __future__ import annotations

import copy
import json
from functools import partial
from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QRect, QRectF, QSize, Qt
from qtpy.QtGui import QBrush, QColor, QPainter, QPalette, QPen
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QLabel,
    QPushButton,
    QStyle,
    QStyleOption,
    QStyleOptionButton,
    QStyleOptionComboBox,
    QWidget,
)

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from .vendor.qtmaterialsymbols import get_icon

from .components.combo_box import Item


def _all_enums(t):
    meta_object: QtCore.QMetaObject = t.staticMetaObject
    enums = [
        meta_object.enumerator(v) for v in range(meta_object.enumeratorCount())
    ]
    for enum in enums:
        # enum.isFlag() is always False
        non_empty_indices = [i for i in range(17) if enum.valueToKey(i)]
        is_flag = non_empty_indices == [0, 1, 2, 4, 8, 16]

        print(
            f"  === {enum.scope()}.{enum.enumName()}[{enum.keyCount()}] -- {'Flag' if is_flag else ''}"
        )

        if is_flag:
            for i in range(enum.keyCount()):
                flag_idx = 2**i if i > 0 else 0
                v = enum.valueToKey(flag_idx)
                if v:
                    print(f"    {flag_idx}: {v}")
        else:
            for i in range(enum.keyCount()):
                print(f"    {i}: {enum.valueToKey(i)}")


def _enum_values(enum):
    # qmeta = QtCore.QMetaEnum(enum)
    meta_object: QtCore.QMetaObject = QStyle.staticMetaObject  # type: ignore
    enum_index = meta_object.indexOfEnumerator(enum.__name__)
    meta_enum: QtCore.QMetaEnum = meta_object.enumerator(enum_index)
    num_keys = meta_enum.keyCount()
    vals = [v for v in range(num_keys) if meta_enum.key(v)]
    # print(f"=== enum = {meta_enum.scope()}.{meta_enum.enumName()} -> {keys}")
    return vals


def enum_to_str(enum, enum_value: int, widget: str) -> str:
    """Convert enum value to string representation."""
    cachekey = f"{enum.__name__}_{enum_value}_{widget}"
    try:
        return enum_to_str._cache[cachekey]  # type: ignore
    except AttributeError:
        enum_to_str._cache = {}  # type: ignore
    except KeyError:
        pass

    try:
        enum_to_str._cache[cachekey] = enum.valueToKey(enum_value)  # type: ignore
    except AttributeError:
        meta_object = QStyle.staticMetaObject  # type: ignore
        enum_index = meta_object.indexOfEnumerator(enum.__name__)
        meta_enum = meta_object.enumerator(enum_index)
        enum_to_str._cache[cachekey] = (  # type: ignore
            f"{meta_enum.valueToKey(enum_value)}-{widget}"  # type: ignore
        )
        # print(f'{cachekey}: {enum_to_str._cache[cachekey]}')

    return enum_to_str._cache[cachekey]  # type: ignore


def hsl_to_html_color(hsl: str):
    vals = hsl[4:-1].split(", ")
    hue = int(vals[0]) / 360.0
    sat = int(vals[1][:-1]) / 100.0
    lum = int(vals[2][:-1]) / 100.0
    return QColor.fromHslF(hue, sat, lum).name()


def do_nothing(*args, **kwargs):
    pass


class StyleData:
    def __init__(self) -> None:
        fpath = Path(__file__).parent / "ayon_style.json"
        with open(fpath, "r") as fh:
            self.data = json.load(fh)
        # Palette values can reference each other
        self._palette = self.data.get("palette", {})
        for k, v in self._palette.items():
            if v.startswith("hsl("):
                self._palette[k] = hsl_to_html_color(v)
        for k, v in self._palette.items():
            self.data["palette"][k] = self.data["palette"].get(v, v)
        for k, v in self._palette.items():
            if v in self._palette:
                raise ValueError(f"Unresolved palette value in {k}")
        # cache
        self._cache = {}
        self.last_key = ""
        # base palette
        self.base_palette = self._build_palette()

    def _build_palette(self):
        bp = {
            QPalette.ColorRole.Window: "qt-active-window",
            QPalette.ColorRole.WindowText: "qt-active-window-text",
            QPalette.ColorRole.Base: "qt-active-base",
            QPalette.ColorRole.Text: "qt-active-text",
            QPalette.ColorRole.Link: "qt-active-link",
            QPalette.ColorRole.Button: "qt-active-button",
            QPalette.ColorRole.ButtonText: "qt-active-button-text",
            QPalette.ColorRole.PlaceholderText: "qt-active-placeholder-text",
            QPalette.ColorRole.Highlight: "qt-active-highlight",
            QPalette.ColorRole.HighlightedText: "qt-active-highlight-text",
        }
        p = QPalette()
        for role, color_name in bp.items():
            p.setColor(
                QPalette.ColorGroup.Active,
                role,
                QColor(self._palette.get(color_name, "#ff0000")),
            )
        return p

    def dump_cache_stats(self):
        print(f"[StyleData] cached {len(self._cache)} styles.")
        print(f"[StyleData]   >> {list(self._cache.keys())}")

    def widget_variants(self, widget):
        return list(self.data["widgets"][widget]["variants"].keys())

    def widget_data(self, widget):
        return self.data["widgets"].get(widget, {})

    def default_variant(self, widget_data):
        return widget_data.get(
            "default-variant", list(widget_data.get("variants", {}).keys())[0]
        )

    def validate_variant(self, widget_data, variant):
        if variant not in widget_data.get("variants", {}).keys():
            return self.default_variant(widget_data)
        return variant

    def palette(self):
        return self.data.get("palette", {})

    def get_style(self, widget: str, variant=None, state="base"):
        try:
            return self._cache[f"{widget}-{variant}-{state}"]
        except KeyError:
            pass

        data = self.widget_data(widget)
        vrt = self.validate_variant(data, variant)
        dvrt = self.default_variant(data)
        pal = self.palette()
        d = copy.copy(self.data["global"])
        d.update(copy.deepcopy(data.get("variants", {}).get(dvrt, {})))
        d.update(copy.deepcopy(data.get("variants", {}).get(vrt, {})))

        to_be_removed = []
        for key, val in d.items():
            if isinstance(val, dict):
                if key == state:
                    for kk, vv in val.items():
                        d[kk] = pal.get(vv, vv)
                to_be_removed.append(key)
            elif isinstance(val, list):
                pass
            else:
                d[key] = pal.get(val, val)
        for k in to_be_removed:
            d.pop(k)
        # cache result
        self.last_key = f"{widget}-{variant}-{state}"
        self._cache[self.last_key] = d
        return d

    def current_style(self):
        return self._cache[self.last_key]


# ----------------------------------------------------------------------------


class ButtonDrawer:
    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def base_class(self):
        return {"QPushButton": QPushButton}

    def register_drawers(self):
        return {
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_PushButton,
                "QPushButton",
            ): [
                partial(
                    self.style_inst.drawControl,
                    QStyle.ControlElement.CE_PushButtonBevel,
                ),
                partial(
                    self.style_inst.drawControl,
                    QStyle.ControlElement.CE_PushButtonLabel,
                ),
            ],
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_PushButtonBevel,
                "QPushButton",
            ): self.draw_push_button,
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_PushButtonLabel,
                "QPushButton",
            ): self.draw_push_button_label,
        }

    def register_sizers(self):
        return {
            enum_to_str(
                QStyle.ContentsType,
                QStyle.ContentsType.CT_PushButton,
                "QPushButton",
            ): self.calculate_push_button_size,
            enum_to_str(
                QStyle.SubElement,
                QStyle.SubElement.SE_PushButtonContents,
                "QPushButton",
            ): self.sub_element_rect,
            enum_to_str(
                QStyle.SubElement,
                QStyle.SubElement.SE_PushButtonFocusRect,
                "QPushButton",
            ): self.sub_element_rect,
        }

    def register_metrics(self):
        return {
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_ButtonMargin,
                "QPushButton",
            ): partial(self.get_metric, QStyle.PixelMetric.PM_ButtonMargin),
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_DefaultFrameWidth,
                "QPushButton",
            ): partial(
                self.get_metric, QStyle.PixelMetric.PM_DefaultFrameWidth
            ),
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_ButtonDefaultIndicator,
                "QPushButton",
            ): partial(
                self.get_metric, QStyle.PixelMetric.PM_ButtonDefaultIndicator
            ),
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_FocusFrameVMargin,
                "QPushButton",
            ): partial(
                self.get_metric, QStyle.PixelMetric.PM_FocusFrameVMargin
            ),
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_FocusFrameHMargin,
                "QPushButton",
            ): partial(
                self.get_metric, QStyle.PixelMetric.PM_FocusFrameHMargin
            ),
        }

    def get_metric(
        self,
        metric: QStyle.PixelMetric,
        opt: QStyleOption | None = None,
        widget: QWidget | None = None,
    ):
        if metric == QStyle.PixelMetric.PM_ButtonMargin:
            return 6
        elif metric == QStyle.PixelMetric.PM_DefaultFrameWidth:
            return 0
        elif metric == QStyle.PixelMetric.PM_ButtonDefaultIndicator:
            return 0
        elif metric == QStyle.PixelMetric.PM_FocusFrameVMargin:
            return 2
        elif metric == QStyle.PixelMetric.PM_FocusFrameHMargin:
            return 2

    def get_button_variant(self, widget: QWidget) -> str:
        """Extract button variant from widget properties."""
        if widget is None:
            return "surface"

        variant = None
        for at in ("_variant", "variant"):
            try:
                variant = getattr(widget, at)
            except AttributeError:
                pass

        if variant and variant in self.model.widget_variants("QPushButton"):
            return variant

        return "surface"

    def get_button_has_icon(self, widget: QWidget) -> bool:
        """Check if button has an icon."""
        if widget is None:
            return False

        # Method 1: Try has_icon property
        if hasattr(widget, "has_icon"):
            return widget.has_icon  # type: ignore

        # Method 2: Try Qt property
        has_icon_prop = widget.property("has_icon")
        if has_icon_prop is not None:
            return bool(has_icon_prop)

        # Method 3: Check the actual icon
        return bool(widget.icon() and not widget.icon().isNull())  # type: ignore

    def get_button_style(
        self, widget: QWidget, state: QStyle.StateFlag
    ) -> dict:
        """Get the appropriate style dictionary for the widget's variant and
        state."""
        variant = self.get_button_variant(widget)

        wstate = "base"
        if not (state & QStyle.StateFlag.State_Enabled):
            wstate = "disabled"
        elif state & QStyle.StateFlag.State_Sunken:
            wstate = "pressed"
        elif state & QStyle.StateFlag.State_MouseOver:
            wstate = "hover"

        style = self.model.get_style("QPushButton", variant, wstate)

        return style

    def draw_push_button(
        self,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None,
    ) -> None:
        """Draw the button background and frame with hover detection."""
        if not isinstance(option, QStyleOptionButton) or widget is None:
            return

        style = self.get_button_style(widget, option.state)
        rect = option.rect

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw button background with hover awareness
        bg_color = style["background-color"]
        painter.setOpacity(style.get("opacity", 1.0))

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        border_radius = style.get("border-radius", 0)
        painter.drawRoundedRect(rect, border_radius, border_radius)

        # Draw focus outline if needed
        if (
            option.state & QStyle.StateFlag.State_HasFocus
            and option.state  # type: ignore
            & QStyle.StateFlag.State_KeyboardFocusChange
        ):
            focus_color = style["focus-outline-color"]
            pen = QPen(
                QColor(focus_color), style.get("focus-outline-width", 0)
            )
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            focus_rect = rect.adjusted(1, 1, -1, -1)
            painter.drawRoundedRect(
                focus_rect, border_radius + 1, border_radius + 1
            )

        painter.restore()

    def draw_push_button_label(
        self,
        option: QStyleOption,
        painter: QPainter,
        widget: QWidget | None,
    ) -> None:
        """Draw the button text and icon."""
        if not isinstance(option, QStyleOptionButton) or widget is None:
            return

        style = self.get_button_style(widget, option.state)  # type: ignore

        # Set up text color
        text_color = style["color"]
        if not (option.state & QStyle.StateFlag.State_Enabled):  # type: ignore
            # Apply some opacity to disabled text
            text_color.setAlpha(int(255 * 0.5))

        painter.save()
        painter.setPen(text_color)

        # Set up font
        font = painter.font()
        font.setFamily(style["font-family"])
        font.setPointSize(style["font-size"])
        font.setWeight(QtGui.QFont.Weight(style["font-weight"]))
        painter.setFont(font)

        # Get content rectangle
        content_rect = self.style_inst.subElementRect(
            QStyle.SubElement.SE_PushButtonContents, option, widget
        )

        # Draw icon if present
        if not option.icon.isNull():  # type: ignore
            icon_rect = QRect(content_rect)
            if option.text:  # type: ignore
                # Icon + text: place icon on the left
                icon_size = option.iconSize  # type: ignore
                icon_rect.setSize(icon_size)
                icon_rect.moveCenter(
                    QtCore.QPoint(
                        content_rect.left() + style["icon-padding"][0],
                        content_rect.center().y(),
                    )
                )

                # Draw icon with text color inheritance
                mode = QtGui.QIcon.Mode.Normal
                if not (
                    option.state & QStyle.StateFlag.State_Enabled  # type: ignore
                ):
                    mode = QtGui.QIcon.Mode.Disabled
                elif option.state & QStyle.StateFlag.State_Sunken:  # type: ignore
                    mode = QtGui.QIcon.Mode.Active

                option.icon = get_icon(widget._icon, color=text_color)

                option.icon.paint(  # type: ignore
                    painter,
                    icon_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    mode,
                )

                # Adjust text rectangle
                text_rect = QRect(content_rect)
                text_rect.setLeft(icon_rect.right() + 4)

                # Draw text
                if option.text:  # type: ignore
                    painter.drawText(
                        text_rect,
                        Qt.AlignmentFlag.AlignCenter,
                        option.text,  # type: ignore
                    )
            else:
                # Icon only: center the icon
                mode = QtGui.QIcon.Mode.Normal
                if not (
                    option.state & QStyle.StateFlag.State_Enabled  # type: ignore
                ):
                    mode = QtGui.QIcon.Mode.Disabled
                elif option.state & QStyle.StateFlag.State_Sunken:  # type: ignore
                    mode = QtGui.QIcon.Mode.Active

                option.icon = get_icon(widget._icon, color=text_color)

                option.icon.paint(  # type: ignore
                    painter,
                    content_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    mode,
                )
        else:
            # Text only
            if option.text:  # type: ignore
                painter.drawText(
                    content_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    option.text,  # type: ignore
                )

        painter.restore()

    def calculate_push_button_size(
        self,
        contents_type: QStyle.ContentsType,
        option: QStyleOption | None,
        contents_size: QtCore.QSize,
        widget: QWidget | None,
    ) -> QtCore.QSize:
        """Calculate minimum size for push buttons with text, icons,
        and proper padding."""

        if not isinstance(option, QStyleOptionButton):
            # Fallback to parent if we don't have proper option data
            if option is not None:
                return super(AYONStyle, self.style_inst).sizeFromContents(
                    contents_type,
                    option,
                    contents_size,
                    widget,
                )
            else:
                # Return reasonable default for button if no option
                return QtCore.QSize(100, 30)

        # Set up font for text measurement
        style = self.get_button_style(widget, option.state)  # type: ignore
        font = QtGui.QFont()
        font.setFamily(style["font-family"])
        font.setPointSize(style["font-size"])
        font.setWeight(QtGui.QFont.Weight(style["font-weight"]))

        # Create font metrics for accurate text measurement
        font_metrics = QtGui.QFontMetrics(font)

        # Determine if button has icon
        has_icon = (
            self.get_button_has_icon(widget)
            if widget
            else not option.icon.isNull()  # type: ignore
        )
        has_icon = not option.icon.isNull()

        # Determine appropriate padding
        if has_icon and not option.text:  # type: ignore
            # Icon-only button
            padding = style["icon-padding"]
        else:
            # Text button or icon+text button
            padding = style["text-padding"]

        # Calculate text dimensions
        text_width = 0
        text_height = 0
        if option.text:  # type: ignore
            text_rect = font_metrics.boundingRect(option.text)  # type: ignore
            text_width = text_rect.width()
            text_height = text_rect.height()

        # Calculate icon dimensions
        icon_width = 0
        icon_height = 0
        if has_icon:
            icon_size = option.iconSize  # type: ignore
            icon_width = icon_size.width()
            icon_height = icon_size.height()

        # Calculate content dimensions
        content_width = 0
        content_height = 0

        if has_icon and option.text:  # type: ignore
            # Icon + text: icon on left, 4px spacing, then text
            content_width = icon_width + 4 + text_width
            content_height = max(icon_height, text_height)
        elif has_icon:
            # Icon only
            content_width = icon_width
            content_height = icon_height
        elif option.text:  # type: ignore
            # Text only
            content_width = text_width
            content_height = text_height

        # Add padding (vertical, horizontal)
        total_width = content_width + (
            2 * padding[1]
        )  # horizontal padding on both sides
        total_height = content_height + (
            2 * padding[0]
        )  # vertical padding on top and bottom

        # Ensure minimum button size (reasonable minimums)
        min_width = 32
        min_height = 24

        total_width = max(total_width, min_width)
        total_height = max(total_height, min_height)

        return QtCore.QSize(total_width, total_height)

    def sub_element_rect(
        self,
        element: QStyle.SubElement,
        option: QStyleOption,
        widget: QWidget,
    ):
        if element == QStyle.SubElement.SE_PushButtonContents:
            style = self.model.get_style(
                "QPushButton", self.get_button_variant(widget)
            )
            if widget and hasattr(widget, "has_icon"):
                has_icon = self.get_button_has_icon(widget)
                padding = (
                    style["icon-padding"]
                    if has_icon and not widget.text()  # type: ignore
                    else style["text-padding"]
                )
            else:
                padding = style["text-padding"]

            return option.rect.adjusted(  # type: ignore
                padding[1], padding[0], -padding[1], -padding[0]
            )

        elif element == QStyle.SubElement.SE_PushButtonFocusRect:
            return option.rect.adjusted(-2, -2, 2, 2)  # type: ignore

        raise ValueError(f"Nothing returned ! -> {element}")


# ----------------------------------------------------------------------------


class FrameDrawer:
    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def base_class(self):
        return {"QFrame": QFrame}

    def register_drawers(self):
        return {
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_ShapedFrame,
                "QFrame",
            ): self.draw_frame,
        }

    def draw_frame(self, option: QStyleOption, painter: QPainter, w: QWidget):
        # get style
        variant = getattr(w, "variant", "")
        style = self.model.get_style("QFrame", variant)
        # pen setup
        border_color = QColor(style["border-color"])
        border_width = style.get("border-width", 0)
        pen = QPen(border_color)
        pen.setWidth(border_width)
        pen.setStyle(
            Qt.PenStyle.SolidLine if border_width else Qt.PenStyle.NoPen
        )
        # brush setup
        bg_color = QColor(style["background-color"])
        brush = QBrush(bg_color)
        radius = style.get("border-radius", 0)
        # draw
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if radius:
            painter.drawRoundedRect(option.rect, radius, radius)
        else:
            painter.drawRect(option.rect)


# ----------------------------------------------------------------------------


class CheckboxDrawer:
    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def base_class(self):
        return {"QCheckBox": QCheckBox}

    def register_drawers(self):
        return {
            enum_to_str(
                QStyle.PrimitiveElement,
                QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                "QCheckBox",
            ): self.draw_toggle,
            enum_to_str(
                QStyle.PrimitiveElement,
                QStyle.PrimitiveElement.PE_FrameFocusRect,
                "QCheckBox",
            ): do_nothing,
        }

    def register_metrics(self):
        return {
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_IndicatorWidth,
                "QCheckBox",
            ): self.indicator_width,
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_IndicatorHeight,
                "QCheckBox",
            ): self.indicator_height,
            enum_to_str(
                QStyle.PixelMetric,
                QStyle.PixelMetric.PM_CheckBoxLabelSpacing,
                "QCheckBox",
            ): self.indicator_spacing,
        }

    def indicator_width(
        self, opt: QStyleOption | None = None, widget: QWidget | None = None
    ):
        return 32

    def indicator_height(
        self, opt: QStyleOption | None = None, widget: QWidget | None = None
    ):
        return 18

    def indicator_spacing(
        self, opt: QStyleOption | None = None, widget: QWidget | None = None
    ):
        return 8

    def draw_toggle(
        self,
        option: QStyleOption,
        painter: QPainter,
        w: QWidget | None = None,
    ):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        checked = bool(option.state & QStyle.StateFlag.State_On)
        style = self.model.get_style(
            "QCheckBox", "", state="checked" if checked else "base"
        )
        painter.setBrush(QColor(style["background-color"]))
        painter.setPen(Qt.PenStyle.NoPen)

        # draw toggle background
        frame_rect: QRectF = option.rect.toRectF().adjusted(1, 0, -1, 0)
        radius = frame_rect.height() / 2.0
        painter.drawRoundedRect(frame_rect, radius, radius)

        # draw toggle
        painter.setBrush(QColor(style["color"]))
        offset = frame_rect.height() * 0.125
        state_rect: QRectF = frame_rect.adjusted(
            offset, offset, -offset, -offset
        )
        state_rect.setWidth(state_rect.height())
        if checked:
            state_rect.moveRight(frame_rect.width() - offset * 0.5)
        painter.drawEllipse(state_rect)
        painter.restore()


# ----------------------------------------------------------------------------


class ComboBoxItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(
        self, parent=None, padding: int = 4, icon_size: int = 16
    ) -> None:
        super().__init__(parent)
        self._padding = padding
        self._icon_size = icon_size
        self._icon_text_spacing = 8

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        # change colors for highlight
        highlight_color = option.palette.color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Light
        )

        if option.state & QStyle.StateFlag.State_MouseOver:
            if index.data(QtCore.Qt.ItemDataRole.ForegroundRole):
                option.palette.setColor(
                    QPalette.ColorGroup.Active,
                    QPalette.ColorRole.Highlight,
                    highlight_color,
                )
                option.palette.setColor(
                    QPalette.ColorGroup.Active,
                    QPalette.ColorRole.HighlightedText,
                    index.data(QtCore.Qt.ItemDataRole.ForegroundRole).color(),
                )
        elif option.state & QStyle.StateFlag.State_Selected:
            if index.data(QtCore.Qt.ItemDataRole.ForegroundRole):
                option.palette.setColor(
                    QPalette.ColorGroup.Active,
                    QPalette.ColorRole.Highlight,
                    index.data(QtCore.Qt.ItemDataRole.ForegroundRole).color(),
                )
            if index.data(QtCore.Qt.ItemDataRole.BackgroundRole):
                option.palette.setColor(
                    QPalette.ColorGroup.Active,
                    QPalette.ColorRole.HighlightedText,
                    index.data(QtCore.Qt.ItemDataRole.BackgroundRole).color(),
                )

        super().paint(painter, option, index)

    def sizeHint(
        self, option: QtWidgets.QStyleOptionViewItem, index
    ) -> QtCore.QSize:
        """Calculate size hint including padding."""

        # Calculate text dimensions
        font_metrics = option.fontMetrics
        text_size = font_metrics.size(0, option.text)

        # Calculate content dimensions
        content_width = text_size.width()
        content_height = max(text_size.height(), self._icon_size)

        # Add icon space if present
        if option.icon:
            content_width += self._icon_size + self._icon_text_spacing

        # Add padding to get total size
        total_width = content_width + self._padding + self._padding
        total_height = content_height + self._padding + self._padding

        # Ensure minimum height
        total_height = max(total_height, 32)

        return QtCore.QSize(total_width, total_height)


class ComboBoxDrawer:
    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def base_class(self):
        return {"QComboBox": QComboBox}

    def register_drawers(self):
        return {
            enum_to_str(
                QStyle.ComplexControl,
                QStyle.ComplexControl.CC_ComboBox,
                "QComboBox",
            ): self.draw_box,
        }

    def register_sizers(self):
        return {
            enum_to_str(
                QStyle.ContentsType,
                QStyle.ContentsType.CT_ComboBox,
                "QComboBox",
            ): self.combobox_size,
        }

    def draw_box(
        self,
        opt: QtWidgets.QStyleOptionComplex,
        p: QPainter,
        w: QComboBox | None = None,
    ):
        # print(f"SUB_CTL: {opt.activeSubControls}")
        if not opt.editable:
            bg_color = opt.palette.color(
                QPalette.ColorGroup.Active, QPalette.ColorRole.Base
            )
            fg_color = opt.palette.color(
                QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText
            )

            if not w:
                # print("NO WIDGET")
                return

            cb_size = getattr(w, "_size", "full")
            inverted = False
            icon_name = ""

            # Get the current selected status
            current_index = w.currentIndex()
            if current_index >= 0:
                item: Item = w.itemData(
                    current_index, QtCore.Qt.ItemDataRole.UserRole
                )
                if item:
                    inverted = getattr(w, "_inverted", False)
                    fg_color = bg_color if inverted else QColor(item.color)
                    bg_color = QColor(item.color) if inverted else bg_color
                    icon_name = item.icon

            # Paint background with status color
            rect = opt.rect
            p.save()
            p.setBrush(QBrush(bg_color))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, 4, 4)
            p.restore()

            # set pen for text drawing
            p.setPen(fg_color)
            if icon_name:
                opt.currentIcon = get_icon(icon_name, color=fg_color)
        else:
            # editable combobox - IMPLEMENT ME
            pass

    def combobox_size(
        self,
        contents_type: QStyle.ContentsType,
        option: QStyleOption | None,
        contents_size: QtCore.QSize,
        widget: QWidget | None,
    ) -> QtCore.QSize:
        if not option or not isinstance(option, QStyleOptionComboBox):
            return QSize()

        style = self.model.get_style("QComboBox")

        text_width = cb_height = 0
        if option.currentText:
            text_rect: QRect = option.fontMetrics.boundingRect(
                option.currentText
            )
            text_width = text_rect.width() + style["text-padding"][0] * 2
            cb_height = text_rect.height() + style["text-padding"][1] * 2

        icon_width = 0
        if option.currentIcon:
            icon_size = getattr(widget, "_icon_size", 0)
            if icon_size == 0:
                all_sizes = option.currentIcon.availableSizes()
                icon_size = max(all_sizes[0].width(), all_sizes[0].height())
            icon_width = icon_size + style["icon-padding"][0] * 2
            icon_height = icon_size + style["icon-padding"][1] * 2
            cb_height = max(cb_height, icon_height)
            if text_width:
                icon_width += style["text-padding"][0]

        final_size = QSize(
            text_width + icon_width,
            cb_height,
        )
        print(f"final_size = {final_size}")
        return final_size


# ----------------------------------------------------------------------------


class LabelDrawer:
    def __init__(self, style_inst: AYONStyle) -> None:
        self.style_inst = style_inst
        self.model = style_inst.model

    @property
    def base_class(self):
        return {"QLabel": QLabel}

    def register_drawers(self):
        return {
            enum_to_str(
                QStyle.ControlElement,
                QStyle.ControlElement.CE_ShapedFrame,
                "QLabel",
            ): do_nothing,
        }


# ----------------------------------------------------------------------------


class AYONStyle(QtWidgets.QCommonStyle):
    """
    AYON QStyle implementation that replaces QSS styling with native Qt painting.
    Supports widget variants: surface, tonal, filled, tertiary, text, nav, etc.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model = StyleData()
        self.drawers = {}
        self.sizers = {}
        self.metrics = {}
        self.base_classes = {}
        self.drawer_objs = [
            LabelDrawer(self),  # first because QLabel inherits from QFrame.
            ButtonDrawer(self),
            CheckboxDrawer(self),
            ComboBoxDrawer(self),
            FrameDrawer(self),
        ]
        for obj in self.drawer_objs:
            self.base_classes.update(obj.base_class)
            if hasattr(obj, "register_drawers"):
                self.drawers.update(obj.register_drawers())
            if hasattr(obj, "register_sizers"):
                self.sizers.update(obj.register_sizers())
            if hasattr(obj, "register_metrics"):
                self.metrics.update(obj.register_metrics())

    def widget_key(self, w: QWidget | None) -> str:
        if w:
            for name, wtype in self.base_classes.items():
                if issubclass(type(w), wtype):
                    return name
        return ""

    def polish(self, widget) -> None:
        """Polish widgets to enable hover tracking and custom palette."""
        if isinstance(widget, QWidget):
            super().polish(widget)
            widget.setPalette(self.model.base_palette)

            # Enable mouse tracking for buttons to receive hover events
            widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            widget.setMouseTracking(True)

            if isinstance(widget, QComboBox):
                widget.setMinimumContentsLength(1)
                widget.setItemDelegate(ComboBoxItemDelegate(parent=widget))
                widget.setSizeAdjustPolicy(
                    QComboBox.SizeAdjustPolicy.AdjustToContents
                )

        elif isinstance(widget, QApplication):
            super().polish(widget)
        else:
            super().polish(widget)

    def drawControl(
        self,
        element: QStyle.ControlElement,
        option: QStyleOption,
        painter: QPainter,
        w: QWidget | None = None,
    ) -> None:
        """Draw control elements (buttons, labels, etc.)."""

        try:
            draw_ce_calls = self.drawers[
                enum_to_str(QStyle.ControlElement, element, self.widget_key(w))
            ]
        except KeyError:
            # no custom drawer fallback
            super().drawControl(element, option, painter, w)
            return
        else:
            if isinstance(draw_ce_calls, list):
                for draw_ce in draw_ce_calls:
                    draw_ce(option, painter, w)
            elif callable(draw_ce_calls):
                draw_ce_calls(option, painter, w)
            return

    def drawComplexControl(
        self,
        cc: QStyle.ComplexControl,
        opt: QtWidgets.QStyleOptionComplex,
        p: QPainter,
        w: QWidget | None = None,
    ) -> None:
        try:
            draw_cc = self.drawers[
                enum_to_str(QStyle.ComplexControl, cc, self.widget_key(w))
            ]
        except KeyError:
            # no custom drawer fallback
            return super().drawComplexControl(cc, opt, p, w)

        draw_cc(opt, p, w)

    def drawPrimitive(
        self,
        element: QStyle.PrimitiveElement,
        option: QStyleOption,
        painter: QPainter,
        w: QWidget | None = None,
    ) -> None:
        """Draw primitive elements."""

        try:
            draw_prim = self.drawers[
                enum_to_str(
                    QStyle.PrimitiveElement, element, self.widget_key(w)
                )
            ]
        except KeyError:
            # Fall back to parent implementation
            super().drawPrimitive(element, option, painter, w)
            return

        draw_prim(option, painter, w)

    def subElementRect(
        self,
        element: QStyle.SubElement,
        option: QStyleOption,
        widget: QWidget | None = None,
    ) -> QRect:
        """Calculate rectangles for sub-elements."""

        try:
            sizer = self.sizers[
                enum_to_str(
                    QStyle.SubElement, element, self.widget_key(widget)
                )
            ]
        except KeyError:
            # Fall back to parent implementation
            return super().subElementRect(element, option, widget)

        return sizer(element, option, widget)

    def pixelMetric(
        self,
        metric: QStyle.PixelMetric,
        opt: QStyleOption | None = None,
        widget: QWidget | None = None,
    ) -> int:
        """Return pixel measurements for various style metrics."""
        # print(f"PM: {metric}")

        try:
            metric_func = self.metrics[
                enum_to_str(
                    QStyle.PixelMetric, metric, self.widget_key(widget)
                )
            ]
        except KeyError:
            # Fall back to parent implementation
            return super().pixelMetric(metric, opt, widget)

        return metric_func(opt, widget)

    def styleHint(
        self,
        hint: QStyle.StyleHint,
        opt: QStyleOption | None = None,
        w: QWidget | None = None,
        shret: QtWidgets.QStyleHintReturn | None = None,
    ) -> int:
        """Return style hints for behavior configuration."""

        if hint == QStyle.StyleHint.SH_Button_FocusPolicy:
            return Qt.FocusPolicy.StrongFocus
        elif hint == QStyle.StyleHint.SH_RequestSoftwareInputPanel:
            return 0
        elif hint == QStyle.StyleHint.SH_ComboBox_PopupFrameStyle:
            return QFrame.Shape.NoFrame

        # Fall back to parent implementation
        return super().styleHint(hint, opt, w, shret)

    def sizeFromContents(
        self,
        contents_type: QStyle.ContentsType,
        option: QStyleOption | None,
        contents_size: QtCore.QSize,
        widget: QWidget | None = None,
    ) -> QtCore.QSize:
        """Calculate minimum size requirements for widgets based on their content."""
        # print(f"CT: {contents_type}")

        try:
            sizer = self.sizers[
                enum_to_str(
                    QStyle.ContentsType, contents_type, self.widget_key(widget)
                )
            ]
        except KeyError:
            if option:
                return super().sizeFromContents(
                    contents_type, option, contents_size, widget
                )
            else:
                # Create a default size if no option is provided
                return QtCore.QSize(100, 32)  # reasonable default
        else:
            return sizer(contents_type, option, contents_size, widget)


# TEST ========================================================================


if __name__ == "__main__":
    import time

    from .components.buttons import AYButton
    from .components.container import AYContainer, AYFrame
    from .components.label import AYLabel
    from .components.layouts import AYHBoxLayout
    from .components.text_box import AYTextBox
    from .tester import Style, test

    def time_it(func):
        i = time.time()
        r = func()
        e = (time.time() - i) * 1000
        return r, e

    m, e = time_it(StyleData)
    print(f"  init time: {e:.6f} ms")

    print("> button-surface-base: -------------------------------------------")
    d, e = time_it(lambda: m.get_style("QPushButton", "surface", "base"))
    # print(json.dumps(d, indent=4))
    print(f"  style time: {e:.6f} ms")

    print("> button-surface-hover -------------------------------------------")
    d, e = time_it(lambda: m.get_style("QPushButton", "surface", "hover"))
    # print(json.dumps(d, indent=4))
    print(f"  style time: {e:.6f} ms")

    d, e = time_it(lambda: m.get_style("QPushButton", "surface", "hover"))
    print(f"  cached style time: {e:.6f} ms")

    m.dump_cache_stats()

    print("> enum_to_str benchmarking --------------------------------------")
    ee = 0
    i = 0
    s = ""
    vals = _enum_values(QStyle.ControlElement)
    for i, v in enumerate(vals):
        s, e = time_it(lambda: enum_to_str(QStyle.ControlElement, v, ""))
        ee += e
    ee /= i
    print(f"  enum_to_str = {s!r}: {ee:.6f} ms ({i} lookups)")
    s = ""
    ee = 0
    runs = 1000
    for i in range(runs):
        for i, v in enumerate(vals):
            s, e = time_it(
                lambda: enum_to_str(
                    QStyle.ControlElement,
                    QStyle.ControlElement.CE_PushButtonBevel,
                    "",
                )
            )
            ee += e
    total_runs = runs * len(vals)
    ee /= total_runs
    print(f"  cached enum_to_str = {s!r}: {ee:.6f} ms ({total_runs} runs)")

    # all_enums(QStyle)

    print("> ui test --------------------------------------------------------")

    def _ui_test():
        # Create and show the test widget
        widget = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant="",
            margin=0,
            layout_spacing=10,
            layout_margin=10,
        )

        container_1 = AYContainer(
            widget,
            layout=AYContainer.Layout.VBox,
            variant="low",
            margin=0,
            layout_margin=10,
            layout_spacing=10,
        )
        widget.add_widget(container_1)

        variants = StyleData().widget_variants("QPushButton")

        l1 = AYHBoxLayout(margin=0)
        for i, var in enumerate(variants):
            b = AYButton(f"{var} button", variant=var)
            l1.addWidget(b)
        container_1.add_layout(l1)

        l2 = AYHBoxLayout(margin=0)
        for i, var in enumerate(variants):
            b = AYButton(f"{var} button", variant=var, icon="add")
            l2.addWidget(b)
        container_1.add_layout(l2)

        container_2 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="low",
            margin=0,
            layout_margin=10,
            layout_spacing=10,
        )
        for i, var in enumerate(variants):
            b = AYButton(variant=var, icon="add")
            container_2.add_widget(b)
        container_2.addStretch()
        widget.add_widget(container_2)

        container_3 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant="low",
            margin=0,
            layout_margin=10,
            layout_spacing=10,
        )
        container_3.add_widget(QtWidgets.QCheckBox("CheckBox"))
        te = AYTextBox()
        te.set_markdown(
            "## Title\nText can be **bold** or *italic*, as expected !\n"
            "- [ ] Do this\n- [ ] Do that\n"
        )
        container_3.add_widget(te)
        container_3.add_widget(AYLabel("Normal"))
        container_3.add_widget(AYLabel("Dimmed", dim=True))
        container_3.addStretch()

        widget.add_widget(container_3)

        return widget

    test(_ui_test, style=Style.Widget)

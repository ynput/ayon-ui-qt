from __future__ import annotations

import copy
import json
import logging
import os
import platform
from functools import cmp_to_key
from glob import glob
from pathlib import Path
from typing import Any

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QRect, QRectF, Qt
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
)
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QCommonStyle,
    QFrame,
    QHeaderView,
    QLabel,
    QMenu,
    QStyle,
    QStyleOption,
    QWidget,
)
from qtpy.shiboken import isValid

from .drawers import (
    ButtonDrawer,
    CheckboxDrawer,
    ComboBoxDrawer,
    ComboBoxItemDelegate,
    FrameDrawer,
    ItemViewItemDrawer,
    LabelDrawer,
    LineEditDrawer,
    ScrollAreaDrawer,
    ScrollBarDrawer,
    TableHeaderDrawer,
    TableItemDelegate,
    TooltipDrawer,
    TreeViewDrawer,
    TreeViewItemDelegate,
    enum_to_str,
    style_font,
)

_ayon_style_instance: AYONStyle | None = None


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]:   %(funcName)16s:  %(message)s",
)
log = logging.getLogger("Ayon Style")


# DEBUG -----------------------------------------------------------------------


def _debug_rect(p: QPainter, color: str, rect: QRect | QRectF):
    p.save()
    pen = QPen(QColor(color))
    brush = QBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen)
    p.setBrush(brush)
    p.drawRect(rect)
    p.restore()


# Override the platform key used for OS-specific font sizes.
# Set the ``AYON_UI_QT_FONT_OS`` env var to a fixed value (e.g. ``"linux"``)
# to make font selection deterministic across machines — useful for visual
# regression tests.


def _font_platform() -> str:
    """Return the platform key used to select OS-specific font sizes.

    Resolution order:
    1. ``AYON_UI_QT_FONT_OS`` environment variable.
    2. Live ``platform.system()`` result (normalised to lower-case).
    """
    env_val = os.environ.get("AYON_UI_QT_FONT_OS")
    if env_val:
        return env_val.lower()
    return platform.system().lower()


def _style_font(style: dict, w: QWidget | None) -> QFont:
    return style_font(style, w)


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
            f"  === {enum.scope()}.{enum.enumName()}[{enum.keyCount()}]"
            f" -- {'Flag' if is_flag else ''}"
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
    meta_object: QtCore.QMetaObject = QStyle.staticMetaObject  # type: ignore
    enum_index = meta_object.indexOfEnumerator(enum.__name__)
    meta_enum: QtCore.QMetaEnum = meta_object.enumerator(enum_index)
    num_keys = meta_enum.keyCount()
    vals = [meta_enum.value(v) for v in range(num_keys) if meta_enum.key(v)]
    return vals


def _enum_values_dict(enum):
    meta_object: QtCore.QMetaObject = QStyle.staticMetaObject  # type: ignore
    enum_index = meta_object.indexOfEnumerator(enum.__name__)
    meta_enum: QtCore.QMetaEnum = meta_object.enumerator(enum_index)
    num_keys = meta_enum.keyCount()
    vals = {
        meta_enum.key(i): meta_enum.value(i)
        for i in range(num_keys)
        if meta_enum.key(i)
    }
    return vals


def hsl_to_html_color(hsl: str):
    vals = hsl[4:-1].split(", ")
    hue = int(vals[0]) / 360.0
    sat = int(vals[1][:-1]) / 100.0
    lum = int(vals[2][:-1]) / 100.0
    return QColor.fromHslF(hue, sat, lum).name()


# ----------------------------------------------------------------------------


def get_ayon_style() -> AYONStyle:
    """Get the singleton AYONStyle instance.

    Returns:
        The singleton AYONStyle instance.
    """
    global _ayon_style_instance
    if _ayon_style_instance is None:
        _ayon_style_instance = AYONStyle()
    return _ayon_style_instance


def get_ayon_style_data(
    widget_cls: str, variant: str | None = None
) -> StyleDict:
    """Get the AYON style data.

    Returns:
        The AYON style data.
    """
    return get_ayon_style().model.get_style(
        widget_cls, variant=variant, state="all"
    )


def style_widget_and_siblings(widget: QWidget, fix_app: bool = False) -> None:
    """Apply AYON style to a widget and its siblings recursively.

    Removes any existing stylesheets and applies the AYON QStyle
    to the given widget and all its sibling widgets (widgets that
    share the same parent), including all their nested children
    even if they are in QLayouts.

    Args:
        widget: The widget whose siblings (and itself) will be styled.
        fix_app: Whether to temporarily remove and restore app stylesheet.
    """

    def _collect_widgets(w: QWidget, seen: set[int]) -> None:
        """Recursively collect all widgets including those in layouts."""
        if id(w) in seen:
            return

        seen.add(id(w))
        widgets_to_style.append(w)

        # Collect direct widget children
        for child in w.children():
            if isinstance(child, QWidget):
                _collect_widgets(child, seen)

        # Collect widgets from layouts
        if (layout := w.layout()) is not None:
            for i in range(layout.count()):
                if (item := layout.itemAt(i)) and (
                    item_widget := item.widget()
                ):
                    _collect_widgets(item_widget, seen)

    # Determine root widgets: siblings if parent exists, otherwise just widget
    root_widgets = [widget]

    # Collect all widgets recursively
    seen_widgets: set[int] = set()
    widgets_to_style: list[QWidget] = []
    for w in root_widgets:
        _collect_widgets(w, seen_widgets)

    qss = None
    app = QApplication.instance()
    if fix_app and app and isinstance(app, QApplication):
        qss = copy.copy(app.property("styleSheet"))

    if fix_app and qss and isinstance(app, QApplication):
        app.setStyleSheet("")

    widget.setAttribute(Qt.WidgetAttribute.WA_WindowPropagation, False)

    # Apply style to all collected widgets
    style = get_ayon_style()
    for w in widgets_to_style:
        w.style().unpolish(w)
        w.setStyle(style)

    if fix_app and qss and isinstance(app, QApplication):
        app.setStyleSheet(qss)


class StyleDict(dict):
    """A dict where string values starting with '@' are resolved
    via getattr() on a bound context object.

    Example:
        ctx = SomeWidget(...)
        d = StyleDict({"color": "@fg_color"}, _context=ctx)
        d["color"]  # -> ctx.fg_color
    """

    _SENTINEL = object()

    def __init__(
        self,
        *args: Any,
        _context: Any = None,
        deepcopy: bool = True,
        **kwargs: Any,
    ) -> None:
        if deepcopy:
            args = copy.deepcopy(args)
            kwargs = copy.deepcopy(kwargs)
        super().__init__(*args, **kwargs)
        # store as attribute on the instance — not as a dict key
        object.__setattr__(self, "_context", _context)
        # convert nested dicts to StyleDicts with the same context
        for k, v in self.items():
            super().__setitem__(
                k,
                StyleDict(v, _context=_context) if isinstance(v, dict) else v,
            )

    def set_context(self, _context: Any) -> None:
        object.__setattr__(self, "_context", _context)
        for v in self.values():
            if isinstance(v, StyleDict):
                v.set_context(_context)

    def __getitem__(self, key: str) -> Any:
        value = super().__getitem__(key)
        return self._resolve(value)

    def get(self, key: str, default: Any = None, raw: bool = False) -> Any:
        value = super().get(key, self._SENTINEL)
        if value is self._SENTINEL:
            return default
        if raw:
            return value
        return self._resolve(value)

    def _resolve(self, value: Any) -> Any:
        if (
            isinstance(value, str)
            and value.startswith("@")
            and self._context is not None
        ):
            return getattr(self._context, value[1:], value)
        return value

    def __repr__(self) -> str:
        return f"StyleDict({super().__repr__()}, context={self._context!r})"


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
            self._palette[k] = self._palette.get(v, v)
        for k, v in self._palette.items():
            if v in self._palette:
                raise ValueError(f"Unresolved palette value in {k}")
        # cache
        self._cache = {}
        self.last_key = ""
        # base palette
        self.base_palette: QPalette = self._build_palette()
        self._base_font: QFont | None = None
        self._base_font_checked: bool = False

    @property
    def base_font(self) -> QFont:
        # delayed to make sure QApplication is initialized
        if self._base_font is None:
            self._base_font = style_font(
                self.data.get("global", {}), QWidget()
            )
            if not self._base_font_checked:
                self._check_font_availability(self._base_font)
        return QFont(self._base_font)

    def _check_font_availability(self, font: QFont):
        # check if the font is available and load it if need be.
        families = QFontDatabase.families()
        if font.family() not in families:
            # Attempt to load from resources
            font_name = font.family().replace(" ", "")
            glob_path = str(
                Path(__file__).parent / "resources" / f"{font_name}*.ttf"
            )
            font_files = glob(glob_path)

            if not font_files:
                log.error(
                    f"Base font '{font.family()}' is not available and no "
                    f"font files were found in '{glob_path}'"
                )
            else:
                for font_path in font_files:
                    if QFontDatabase.addApplicationFont(str(font_path)) == -1:
                        log.error(f"Failed to load base font from {font_path}")
                    else:
                        log.debug(f"Loaded base font file {font_path}")
        self._base_font_checked = True

    def _build_palette(self) -> QPalette:
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
            QPalette.ColorRole.Light: "qt-active-light",
            QPalette.ColorRole.Midlight: "qt-active-midlight",
            QPalette.ColorRole.Dark: "qt-active-dark",
            QPalette.ColorRole.Mid: "qt-active-mid",
            QPalette.ColorRole.Shadow: "qt-active-shadow",
        }
        p = QPalette()
        for role, color_name in bp.items():
            p.setColor(
                QPalette.ColorGroup.Active,
                role,
                QColor(self._palette.get(color_name, "#ff0000")),
            )
        return p

    def get_style_palette(self, widget: QWidget, widget_key: str) -> QPalette:
        """Get a QPalette for the widget based on the current style data.

        Resolves any @ references in the style data to widget attributes.
        Caches results for efficiency, if there are no @ references.
        """
        variant = getattr(widget, "_variant_str", "default")
        # check if cached
        cache_key = f"{widget_key}-{variant}-palette"
        if cache_key in self._cache:
            return QPalette(self._cache[cache_key])

        style: StyleDict = self.get_styles(
            widget_key,
            variant=variant,
        )
        style.set_context(widget)

        p = QPalette(self.base_palette)

        fg_color = style.get("base", {}).get("color")
        if fg_color:
            p.setColor(
                widget.foregroundRole(),
                QColor(fg_color),
            )
        opacity = style.get("disabled", {}).get("opacity")
        if opacity:
            disabled_fg_color = QColor(fg_color)
            disabled_fg_color.setAlphaF(opacity)
            p.setColor(
                QPalette.ColorGroup.Disabled,
                widget.foregroundRole(),
                disabled_fg_color,
            )

        bg_color = style.get("base", {}).get("background-color")
        if bg_color:
            p.setColor(
                widget.backgroundRole(),
                QColor(bg_color),
            )

        # cache result
        style.set_context(None)
        self._cache[cache_key] = p

        return QPalette(p)

    def dump_cache_stats(self):
        print(f"[StyleData] cached {len(self._cache)} styles.")
        print(f"[StyleData]   >> {list(self._cache.keys())}")

    def widget_variants(self, widget_cls: str) -> list[str]:
        return list(
            self.data["widgets"].get(widget_cls, {}).get("variants", {}).keys()
        )

    def widget_states(self, widget_cls: str) -> list[str]:
        states = list(
            self.data["widgets"].get(widget_cls, {}).get("states", [])
        )
        return states if "base" in states else ["base"] + states

    def widget_data(self, widget_cls: str) -> dict:
        return self.data["widgets"].get(widget_cls, {})

    def widget_list(self) -> list[str]:
        return list(self.data["widgets"].keys())

    def default_variant(self, widget_data) -> str:
        variants = widget_data.get("variants", {})
        return widget_data.get(
            "default-variant", next(iter(variants.keys()), "default")
        )

    def validate_variant(self, widget_data, variant) -> str:
        if variant not in widget_data.get("variants", {}):
            return self.default_variant(widget_data)
        return variant

    def palette(self):
        return self._palette

    def get_style(
        self,
        widget_cls: str,
        variant=None,
        state="base",
    ) -> StyleDict:
        """Returns a style for a widget, variant and state."""
        try:
            return StyleDict(self._cache[f"{widget_cls}-{variant}-{state}"])
        except KeyError:
            pass

        data = self.widget_data(widget_cls)
        vrt = self.validate_variant(data, variant)
        dvrt = self.default_variant(data)
        pal = self._palette
        d = copy.copy(self.data["global"])
        d.update(copy.deepcopy(data.get("variants", {}).get(dvrt, {})))
        d.update(copy.deepcopy(data.get("variants", {}).get(vrt, {})))

        if state == "all":
            for key, val in d.items():
                if isinstance(val, dict):
                    d[key] = {kk: pal.get(vv, vv) for kk, vv in val.items()}
                elif not isinstance(val, list):
                    d[key] = pal.get(val, val)
        else:
            # Override palette variables with the current state's values and
            # remove all states. That way, we can directly use
            # "background-color" without checking the widget's state.
            state_dict = {}
            for key, val in list(d.items()):
                if isinstance(val, dict):
                    if key == state:
                        state_dict = {
                            kk: pal.get(vv, vv) for kk, vv in val.items()
                        }
                    d.pop(key)
                elif not isinstance(val, list):
                    d[key] = pal.get(val, val)
            # apply current state overrides last to ensure they take precedence
            # over the base variant
            d.update(state_dict)

        # cache result
        d = StyleDict(d)
        self.last_key = f"{widget_cls}-{variant}-{state}"
        self._cache[self.last_key] = d
        return StyleDict(d)

    def get_styles(
        self,
        widget_cls: str,
        variant: str | None = None,
        states: list[str] | None = None,
    ) -> StyleDict:
        """Returns styles for a widget, variant and multiple states at once.

        This is more efficient than calling get_style() multiple times
        when you need styles for several states of the same widget/variant.

        Args:
            widget_cls: The widget class name (e.g., "QStyledItemDelegate").
            variant: The variant name (e.g., "default"). Defaults to None.
            states: List of states to retrieve (e.g., ["base", "hover",
                "checked"]). Defaults to all defined states.

        Returns:
            A dictionary mapping state names to their style dictionaries.
        """
        if states is None:
            states = self.widget_states(widget_cls)

        cache_key = f"all-{widget_cls}-{variant}-{'|'.join(states)}"
        try:
            return StyleDict(self._cache[cache_key])
        except KeyError:
            pass

        d = {
            state: self.get_style(widget_cls, variant, state)
            for state in states
        }
        self._cache[cache_key] = StyleDict(d)
        return StyleDict(d)

    def current_style(self):
        return self._cache[self.last_key]

    def get_widget_color(
        self,
        color_name: str,
        style: dict,
        w: QWidget,
        default: str | QColor,
    ) -> QColor:
        """Process color definitions referencing a widget attribute/property
        using the @ syntax.

        Args:
            color_name: The color name to retrieve.
            style: The style dictionary.
            w: The widget to get the color from.
            default: The default color to use if the attribute is not found.
        Returns:
            The color.
        """
        color = style[color_name]
        if isinstance(color, str) and color.startswith("@"):
            color = getattr(w, color[1:], default)
        return QColor(color)


# ----------------------------------------------------------------------------
W_T = {}


class AYONStyle(QCommonStyle):
    """
    AYON QStyle implementation that replaces QSS styling with native Qt
    painting. Supports widget variants: surface, tonal, filled, tertiary,
    text, nav, etc.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model = StyleData()
        self._in_widget_key = False
        self.drawers = {}
        self.sizers = {}
        self.metrics = {}
        self.base_classes = {}
        self.drawer_objs = [
            TooltipDrawer(self),
            LabelDrawer(self),
            LineEditDrawer(self),
            ButtonDrawer(self),
            CheckboxDrawer(self),
            ComboBoxDrawer(self),
            ScrollBarDrawer(self),
            FrameDrawer(self),
            TreeViewDrawer(self),
            TableHeaderDrawer(self),
            ItemViewItemDrawer(self),
            ScrollAreaDrawer(self),
        ]
        for obj in self.drawer_objs:
            self.base_classes.update(obj.base_class)
            if hasattr(obj, "register_drawers"):
                self.drawers.update(obj.register_drawers())
            if hasattr(obj, "register_sizers"):
                self.sizers.update(obj.register_sizers())
            if hasattr(obj, "register_metrics"):
                self.metrics.update(obj.register_metrics())

        # Sort base_classes: most-specific first to guarantee correct widget
        # key resolution order.
        def _specificity_cmp(a, b):
            """Return <0 if `a` is more specific than `b`.

            More specific means: `a` is a (strict) subclass of `b`.
            For unrelated classes, fall back to MRO depth so deeper
            classes still come first, then class name for stability.
            """
            ca, cb = a[1], b[1]
            if ca is cb:
                return 0
            if issubclass(ca, cb):
                return -1  # a before b
            if issubclass(cb, ca):
                return 1  # b before a
            # Unrelated: deeper MRO first, then name for determinism.
            d = len(cb.__mro__) - len(ca.__mro__)
            if d:
                return d
            return (ca.__name__ > cb.__name__) - (ca.__name__ < cb.__name__)

        self.base_classes = dict(
            sorted(self.base_classes.items(), key=cmp_to_key(_specificity_cmp))
        )

    def widget_key(self, w: QWidget | None) -> str:
        if self._in_widget_key or w is None or not isValid(w):
            return ""

        if w:
            # Handle item view widgets - check parent for delegate and exclude
            # ComboBoxItemDelegate
            if hasattr(w, "itemDelegate") and not isinstance(
                w, (QComboBox, QHeaderView)
            ):
                # Calling itemDelegate() is not a simple getter - it can
                # trigger Qt's internal operations that call back into the
                # custom style methods (subElementRect, drawPrimitive,
                # pixelMetric, etc.), each of which calls widget_key() again,
                # creating infinite recursion.
                self._in_widget_key = True
                try:
                    delegate = w.itemDelegate()
                    cbd = delegate and isinstance(
                        delegate, ComboBoxItemDelegate
                    )
                    tvd = delegate and isinstance(
                        delegate, (TreeViewItemDelegate, TableItemDelegate)
                    )
                    if not cbd and not tvd:
                        return "QStyledItemDelegate"
                finally:
                    self._in_widget_key = False
            for name, wtype in self.base_classes.items():
                if issubclass(type(w), wtype):
                    if w.objectName() == "qtooltip_label":
                        return "QToolTip"
                    if isinstance(w, QLabel):
                        p = w.parent()
                        # NOTE: Qt does not use QToolTip but a QLabel (a
                        # private QLabelTip class) !!
                        # if the parent is a widget and it doesn't have a
                        # layout, it could be a tooltip.
                        # Sometimes, objectName() == "qtooltip_label" but the
                        # object name is set when the rect requests are made.
                        if p and isinstance(p, QWidget) and not p.layout():
                            return "QToolTip"
                    return name
        return ""

    def style_widget(self, widget: QWidget) -> None:
        """Apply AYON style to a widget (palette, font, hover tracking)."""
        if isinstance(widget, QWidget):
            variant = getattr(widget, "_variant_str", "default")
            if hasattr(widget, "_style_data"):
                if not widget._style_data:
                    widget._style_data = self.model.get_style(
                        self.widget_key(widget),
                        variant,
                    )
                    widget._style_data.set_context(widget)

            if hasattr(widget, "set_palette"):
                widget.set_palette(
                    self.model.get_style_palette(
                        widget, self.widget_key(widget)
                    )
                )
            else:
                widget.setPalette(QtGui.QPalette(self.model.base_palette))

            if hasattr(widget, "set_font"):
                widget.set_font(QFont(self.model.base_font))
            else:
                widget.setFont(QFont(self.model.base_font))

            # Enable mouse tracking for buttons to receive hover events
            widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            widget.setMouseTracking(True)

            if isinstance(widget, QComboBox):
                widget.setMinimumContentsLength(1)
                widget.setItemDelegate(
                    ComboBoxItemDelegate(parent=widget, style_model=self.model)
                )
                widget.setSizeAdjustPolicy(
                    QComboBox.SizeAdjustPolicy.AdjustToContents
                )
            elif isinstance(widget, QLabel):
                # rounded corner no background.
                widget.setAttribute(
                    Qt.WidgetAttribute.WA_TranslucentBackground, True
                )

    def polish(self, widget) -> None:
        """Polish widgets to enable hover tracking and custom palette."""
        if isinstance(widget, QWidget):
            super().polish(widget)
            self.style_widget(widget)

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
        key = enum_to_str(QStyle.ControlElement, element, self.widget_key(w))

        if type(w).__name__ in W_T:
            log.info("  >>  drawControl %s %s", type(w), key)

        try:
            draw_ce_calls = self.drawers[key]
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
        key = enum_to_str(QStyle.ComplexControl, cc, self.widget_key(w))
        if type(w).__name__ in W_T:
            log.info("  >>  drawComplexControl %s %s", type(w), key)

        try:
            draw_cc = self.drawers[key]
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

        key = enum_to_str(QStyle.PrimitiveElement, element, self.widget_key(w))
        if type(w).__name__ in W_T:
            log.info("  >>  drawPrimitive %s %s", type(w), key)

        try:
            draw_prim = self.drawers[key]
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
        key = enum_to_str(QStyle.SubElement, element, self.widget_key(widget))

        if isinstance(widget, QLabel):
            log.debug("%s %s", type(widget).__name__, key)

        try:
            sizer = self.sizers[key]
        except KeyError:
            # Fall back to parent implementation
            # Catch RuntimeError in case widget's C++ object was already
            # deleted
            try:
                if widget is not None:
                    return super().subElementRect(element, option, widget)
                else:
                    return super().subElementRect(element, option)
            except RuntimeError:
                # Widget was deleted, call without it
                return super().subElementRect(element, option)

        return sizer(element, option, widget)

    def subControlRect(
        self,
        cc: QStyle.ComplexControl,
        opt: QtWidgets.QStyleOptionComplex,
        sc: QStyle.SubControl,
        w: QWidget | None = None,
    ) -> QRect:
        key = enum_to_str(QStyle.ComplexControl, cc, self.widget_key(w))

        if isinstance(w, QLabel):
            log.debug("%s %s", type(w).__name__, key)

        try:
            sizer = self.sizers[key]
        except KeyError:
            # Fall back to parent implementation
            return super().subControlRect(cc, opt, sc, w)

        try:
            return sizer(cc, opt, sc, w)
        except ValueError:
            return super().subControlRect(cc, opt, sc, w)

    def pixelMetric(
        self,
        metric: QStyle.PixelMetric,
        opt: QStyleOption | None = None,
        widget: QWidget | None = None,
    ) -> int:
        """Return pixel measurements for various style metrics."""
        key = enum_to_str(QStyle.PixelMetric, metric, self.widget_key(widget))

        if isinstance(widget, QLabel):
            log.debug("%s %s", type(widget), key)

        try:
            metric_func = self.metrics[key]
        except KeyError:
            # Fall back to parent implementation
            return super().pixelMetric(metric, opt, widget)

        return metric_func(metric, opt, widget)

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
        """Calculate minimum size requirements for widgets based on their
        content."""
        key = enum_to_str(
            QStyle.ContentsType, contents_type, self.widget_key(widget)
        )

        if isinstance(widget, QLabel):
            log.debug("%s", widget)

        try:
            sizer = self.sizers[key]
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
    from .components.check_box import AYCheckBox
    from .components.combo_box import ALL_STATUSES, AYComboBox
    from .components.container import AYContainer
    from .components.label import AYLabel
    from .components.layouts import AYHBoxLayout, AYVBoxLayout
    from .components.text_box import AYTextBox
    from .components.user_image import AYUserImage
    from .tester import Style, test
    from .variants import QPushButtonVariants

    def time_it(func):
        i = time.time()
        r = func()
        e = (time.time() - i) * 1000
        return r, e

    m, e = time_it(StyleData)
    print(f"  init time: {e:.6f} ms")

    print("> button-surface-base: -------------------------------------------")
    d, e = time_it(lambda: m.get_style("QPushButton", "surface", "base"))
    print(f"  style time: {e:.6f} ms")

    print("> button-surface-hover -------------------------------------------")
    d, e = time_it(lambda: m.get_style("QPushButton", "surface", "hover"))
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

    print("> ui test --------------------------------------------------------")

    def _ui_test():
        # Create and show the test widget
        widget = AYContainer(
            layout=AYContainer.Layout.VBox,
            variant=AYContainer.Variants.Default,
            margin=0,
            layout_spacing=10,
            layout_margin=10,
        )

        container_1 = AYContainer(
            widget,
            layout=AYContainer.Layout.VBox,
            variant=AYContainer.Variants.Low,
            margin=0,
            layout_margin=10,
            layout_spacing=10,
        )
        container_1.setToolTip("container_1")
        widget.add_widget(container_1)

        variants = [v for v in QPushButtonVariants]

        # text buttons
        l1 = AYHBoxLayout(margin=0)
        for i, var in enumerate(variants):
            b = AYButton(
                f"{var.value} button",
                variant=var,
                tooltip=f"using variant {var.value}...",
            )
            l1.addWidget(b)
        container_1.add_layout(l1)

        # text + icon buttons
        l2 = AYHBoxLayout(margin=0)
        for i, var in enumerate(variants):
            b = AYButton(f"{var.value} button", variant=var, icon="add")
            l2.addWidget(b)
        container_1.add_layout(l2)

        container_2 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            margin=0,
            layout_margin=10,
            layout_spacing=10,
        )
        # icon buttons
        for i, var in enumerate(variants):
            b = AYButton(
                variant=var,
                icon="add",
                name_id="ICON_ONLY" if i == 0 else "",
            )
            container_2.add_widget(b)
        container_2.addStretch()
        widget.add_widget(container_2)

        container_3 = AYContainer(
            layout=AYContainer.Layout.HBox,
            variant=AYContainer.Variants.Low,
            margin=0,
            layout_margin=10,
            layout_spacing=10,
        )
        te = AYTextBox()
        te.set_markdown(
            "## Title\nText can be **bold** or *italic*, as expected !\n"
            "- [ ] Do this\n- [ ] Do that\n"
        )
        container_3.add_widget(te)
        vblyt = AYVBoxLayout(spacing=8)
        cbb = AYComboBox(items=ALL_STATUSES)
        vblyt.addWidget(cbb)
        cbbi = AYComboBox(items=ALL_STATUSES, inverted=True)
        vblyt.addWidget(cbbi)
        cb = AYCheckBox("CheckBox")
        cb.setToolTip(("A typical switch..."))
        vblyt.addWidget(cb)
        vblyt.addWidget(AYLabel("Normal label", tool_tip="text only"))
        vblyt.addWidget(
            AYLabel("Dimmed label", dim=True, tool_tip="text dimmed")
        )
        vblyt.addWidget(
            AYLabel(
                "Icon + text label",
                icon="favorite",
                tool_tip="Icon and text",
            )
        )
        vblyt.addWidget(
            AYLabel(
                icon="token",
                icon_color="#ff8800",
                icon_size=32,
                tool_tip="32 px orange icon only",
            )
        )
        vblyt.addWidget(
            AYLabel(
                "a badge",
                icon_color="#0088ff",
                variant=AYLabel.Variants.Badge,
                tool_tip="a blue badge",
            )
        )
        vblyt.addStretch()
        container_3.add_layout(vblyt)

        # 3rd column
        col3_lyt = AYVBoxLayout(spacing=8)
        usr_ly = AYHBoxLayout(spacing=8)
        usr_ly.addWidget(
            AYUserImage(
                src=Path(__file__).parent / "resources" / "avatar1.jpg"
            )
        )
        usr_ly.addWidget(AYUserImage(full_name="John Doe"))
        col3_lyt.addLayout(usr_ly)

        col3_lyt.addStretch()
        container_3.add_layout(col3_lyt)

        container_3.addStretch()
        widget.add_widget(container_3)

        return widget

    test(_ui_test, style=Style.AyonStyleOverCSS)

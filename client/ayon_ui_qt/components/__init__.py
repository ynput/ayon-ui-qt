"""AYON UI Qt components package.

This package provides reusable Qt widgets styled according to the AYON
design system.
"""

from importlib import import_module
from typing import Any

__all__ = (
    "AYButton",
    "AYCheckBox",
    "AYComboBox",
    "AYContainer",
    "AYLabel",
    "AYHBoxLayout",
    "AYVBoxLayout",
    "AYGridLayout",
    "AYLineEdit",
    "AYTextEdit",
    "AYTreeView",
)

_EXPORT_MAP = {
    "AYButton": (".buttons", "AYButton"),
    "AYCheckBox": (".check_box", "AYCheckBox"),
    "AYComboBox": (".combo_box", "AYComboBox"),
    "AYContainer": (".container", "AYContainer"),
    "AYLabel": (".label", "AYLabel"),
    "AYHBoxLayout": (".layouts", "AYHBoxLayout"),
    "AYVBoxLayout": (".layouts", "AYVBoxLayout"),
    "AYGridLayout": (".layouts", "AYGridLayout"),
    "AYLineEdit": (".line_edit", "AYLineEdit"),
    "AYTextEdit": (".text_edit", "AYTextEdit"),
    "AYTreeView": (".tree_view", "AYTreeView"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from exc

    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))

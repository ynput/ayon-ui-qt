"""AYON UI Qt components package.

This package provides reusable Qt widgets styled according to the AYON
design system.

Lazy Loading
------------
Components are loaded on first access rather than at import time. This
avoids importing every submodule (and their Qt dependencies) when only a
subset of components is needed.

The mechanism relies on two module-level dunder hooks:

* ``__getattr__`` — called by Python whenever an attribute is not found in
  the module's ``globals()``.  It looks up the requested name in
  ``_EXPORT_MAP``, imports the owning submodule, resolves the attribute,
  and caches the result directly in ``globals()`` so that subsequent
  accesses are O(1) dictionary look-ups without going through
  ``__getattr__`` again.

* ``__dir__`` — merges the live ``globals()`` with the statically declared
  ``__all__`` so that ``dir()`` and tab-completion tools always advertise
  the full public API, regardless of which components have been loaded so
  far.
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
    """Lazy-load a public component on first attribute access.

    Python invokes this hook when ``name`` is not present in the module's
    ``globals()``.  The function consults ``_EXPORT_MAP`` to find which
    submodule owns the requested symbol, imports that submodule, retrieves
    the attribute, and stores it in ``globals()`` so that all future
    accesses bypass this hook entirely.

    Args:
        name: The attribute name being accessed on this module.

    Returns:
        The resolved component class (or object) from its submodule.

    Raises:
        AttributeError: If ``name`` is not listed in ``_EXPORT_MAP``.
    """
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
    """Return the full public API regardless of what has been loaded.

    Merges the currently populated ``globals()`` with the statically
    declared ``__all__`` tuple so that introspection tools (``dir()``,
    IDE auto-complete, ``help()``) always advertise every exported name,
    even for components that have not been lazily imported yet.

    Returns:
        A sorted list of all attribute names available on this module.
    """
    return sorted(set(globals()) | set(__all__))

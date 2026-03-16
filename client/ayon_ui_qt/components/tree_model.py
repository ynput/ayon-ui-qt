"""Lazy-loading tree model for AYON UI Qt components."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from qtpy.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
)

try:
    from qtmaterialsymbols import get_icon  # type: ignore
except ImportError:
    from ..vendor.qtmaterialsymbols import get_icon

log = logging.getLogger(__name__)


@dataclass
class TreeNode:
    """Represents a single node in a lazy-loaded tree.

    Attributes:
        id: Unique identifier for this node.
        label: Display label shown in the view.
        has_children: Whether this node can have children.
        icon: Optional icon name or path.
        data: Arbitrary extra data associated with this node.
    """

    id: str
    label: str
    has_children: bool = False
    icon: str = ""
    icon_color: str = "#f4f5f5"
    icon_fill: bool = False
    data: dict = field(default_factory=dict)


class _InternalNode:
    """Internal tree node used by LazyTreeModel.

    Attributes:
        tree_node: The public TreeNode data, or None for the root.
        parent: Parent _InternalNode, or None for the root.
        children: Ordered list of child _InternalNode instances.
        children_loaded: Whether children have been fetched.
    """

    def __init__(
        self,
        tree_node: TreeNode | None,
        parent: _InternalNode | None,
    ) -> None:
        self.tree_node: TreeNode | None = tree_node
        self.parent: _InternalNode | None = parent
        self.children: list[_InternalNode] = []
        self.children_loaded: bool = False

    @property
    def is_root(self) -> bool:
        """Return True if this node is the virtual root."""
        return self.tree_node is None


class LazyTreeModel(QAbstractItemModel):
    """Qt model that lazily loads children via a callback.

    Children are fetched on demand using Qt's canFetchMore/fetchMore
    protocol. The root level is loaded immediately on construction.

    Args:
        fetch_children: Callable that takes a parent node ID (``None``
            for root) and returns a list of :class:`TreeNode` instances.
        parent: Optional parent QObject.

    Example::

        def fetch(parent_id):
            if parent_id is None:
                return [TreeNode("root", "Root", has_children=True)]
            return []

        model = LazyTreeModel(fetch_children=fetch)
    """

    def __init__(
        self,
        fetch_children: Callable[[str | None], list[TreeNode]],
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._fetch_children = fetch_children
        self._root = _InternalNode(tree_node=None, parent=None)
        self._root.children_loaded = True
        self._load_children(self._root)

    def _do_fetch_children(self, node: _InternalNode) -> list[_InternalNode]:
        """Fetch children for a node via the callback.

        Args:
            node: The parent node to fetch children for.

        Returns:
            List of newly created internal nodes.
        """
        parent_id = None if node.is_root else node.tree_node.id  # type: ignore[union-attr]
        try:
            tree_nodes = self._fetch_children(parent_id)
        except Exception:
            log.exception(
                "fetch_children raised for parent_id=%r",
                parent_id,
            )
            tree_nodes = []
        return [_InternalNode(tree_node=tn, parent=node) for tn in tree_nodes]

    def _load_children(self, node: _InternalNode) -> None:
        """Fetch and attach children for the given internal node.

        Args:
            node: The node whose children should be loaded.
        """
        children = self._do_fetch_children(node)
        # print(f"    _load_children: {node} -> {children}")
        node.children = children
        node.children_loaded = True

    def _node_from_index(
        self, index: QModelIndex | QPersistentModelIndex
    ) -> _InternalNode:
        """Return the internal node for a model index.

        Args:
            index: A valid or invalid QModelIndex.

        Returns:
            The corresponding _InternalNode; returns root for invalid
            indexes.
        """
        if not index.isValid():
            return self._root
        return index.internalPointer()  # type: ignore[return-value]

    # keep old name as alias for backward compatibility
    def _node_for_index(self, index: QModelIndex) -> _InternalNode:
        """Alias for _node_from_index."""
        return self._node_from_index(index)

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> QModelIndex:
        """Create a model index for the given row/column under parent.

        Args:
            row: Row number under the parent.
            column: Column number (always 0).
            parent: Parent index.

        Returns:
            A valid QModelIndex, or an invalid one if out of range.
        """
        parent_node = self._node_from_index(parent)
        if row < 0 or row >= len(parent_node.children):
            return QModelIndex()
        child_node = parent_node.children[row]
        return self.createIndex(row, column, child_node)

    def parent(self, index: QModelIndex) -> QModelIndex:  # type: ignore[override]
        """Return the parent index of the given index.

        Args:
            index: A model index whose parent is requested.

        Returns:
            Parent QModelIndex, or an invalid index if parent is root.
        """
        if not index.isValid():
            return QModelIndex()

        node: _InternalNode = index.internalPointer()  # type: ignore[assignment]
        parent_node = node.parent
        if parent_node is None or parent_node.is_root:
            return QModelIndex()

        # grandparent is always non-None for a non-root parent_node
        grandparent = parent_node.parent
        row = grandparent.children.index(parent_node)  # type: ignore[union-attr]
        return self.createIndex(row, 0, parent_node)

    def rowCount(
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        """Return the number of rows under the given parent.

        Args:
            parent: The parent index.

        Returns:
            Number of loaded children. Returns 0 for nodes whose
            children have not been fetched yet; Qt uses hasChildren()
            to decide whether to show a disclosure triangle.
        """
        node = self._node_from_index(parent)
        return len(node.children)

    def columnCount(
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        """Return the number of columns (always 1).

        Args:
            parent: Unused parent index.

        Returns:
            Always 1.
        """
        return 1

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        """Return data for the given index and role.

        Args:
            index: The model index to query.
            role: The data role.

        Returns:
            The node label for DisplayRole, None otherwise.
        """
        if not index.isValid():
            return None
        node: _InternalNode = index.internalPointer()  # type: ignore[assignment]
        if role == Qt.ItemDataRole.DisplayRole:
            return node.tree_node.label if node.tree_node else None
        elif role == Qt.ItemDataRole.DecorationRole:
            if node.tree_node and node.tree_node.icon:
                return get_icon(
                    node.tree_node.icon,
                    node.tree_node.icon_color,
                    fill=node.tree_node.icon_fill,
                )
        elif role == Qt.ItemDataRole.UserRole:
            if node.tree_node and node.tree_node.data:
                return node.tree_node.data
        return None

    def hasChildren(
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> bool:
        """Return whether the node at parent has or can have children.

        This is used by Qt to decide whether to draw the disclosure
        triangle, even before children are loaded.

        Args:
            parent: The parent index.

        Returns:
            True if the node has loaded children or has_children is
            True on the TreeNode.
        """
        node = self._node_from_index(parent)
        if node.is_root:
            return bool(node.children)
        # node.tree_node is non-None here (is_root is False)
        if node.children_loaded:
            return bool(node.children)
        return node.tree_node.has_children  # type: ignore[union-attr]

    def canFetchMore(
        self, parent: QModelIndex | QPersistentModelIndex
    ) -> bool:
        """Return True if more children can be fetched for parent.

        Args:
            parent: The parent index to check.

        Returns:
            True if the node has potential children but they have not
            been loaded yet.
        """
        node = self._node_from_index(parent)
        if node.is_root:
            return False
        # node.tree_node is non-None here (is_root is False)
        return (  # type: ignore[union-attr]
            node.tree_node.has_children and not node.children_loaded
        )

    def fetchMore(self, parent: QModelIndex | QPersistentModelIndex) -> None:
        """Fetch and insert children for the node at parent.

        Args:
            parent: The parent index whose children should be loaded.
        """
        node = self._node_from_index(parent)
        if node.children_loaded:
            return
        children = self._do_fetch_children(node)
        if children:
            self.beginInsertRows(parent, 0, len(children) - 1)
            node.children = children
            node.children_loaded = True
            self.endInsertRows()
        else:
            node.children_loaded = True

    def get_node_id(self, index: QModelIndex) -> str | None:
        """Return the TreeNode.id for the given model index.

        Args:
            index: A valid QModelIndex.

        Returns:
            The node's string ID, or None if the index is invalid.
        """
        if not index.isValid():
            return None
        node: _InternalNode = index.internalPointer()  # type: ignore[assignment]
        if node.tree_node is None:
            return None
        return node.tree_node.id

    def reset(self) -> None:
        """Reset the model to its initial state."""
        self.beginResetModel()
        self._root = _InternalNode(tree_node=None, parent=None)
        self._root.children_loaded = True
        self._load_children(self._root)
        self.endResetModel()


# --------------- fake data for testing --------------------------------

PRODUCTS_TEST_DATA: dict[str | None, list[TreeNode]] = {
    None: [
        TreeNode("assets", "Assets", has_children=True, icon="category"),
        TreeNode("shots", "Shots", has_children=True, icon="theaters"),
        TreeNode("refs", "References", has_children=False, icon="menu_book"),
    ],
    "assets": [
        TreeNode("char", "Characters", has_children=True, icon="folder"),
        TreeNode("props", "Props", has_children=True, icon="folder"),
    ],
    "char": [
        TreeNode("char_pi", "pigeon", icon="smart_toy"),
        TreeNode("char_ro", "robot", icon="smart_toy"),
    ],
    "props": [
        TreeNode("props_p", "Peace", icon="self_improvement"),
        TreeNode("props_l", "Love", icon="favorite"),
    ],
    "shots": [
        TreeNode("sh010", "SH010", has_children=True, icon="folder"),
        TreeNode("sh020", "SH020", has_children=True, icon="folder"),
        TreeNode("sh030", "SH030", has_children=True, icon="folder"),
    ],
    "sh010": [
        TreeNode("sh010_anim", "Animation", icon="directions_run"),
        TreeNode("sh010_lgt", "Lighting", icon="highlight"),
    ],
    "sh020": [
        TreeNode("sh020_anim", "Animation", icon="directions_run"),
        TreeNode("sh020_comp", "Compositing", icon="layers"),
    ],
    "sh030": [
        TreeNode("sh030_fx", "FX", icon="fireplace"),
        TreeNode("sh030_lgt", "Lighting", icon="highlight"),
    ],
}

REVIEWS_TEST_DATA: dict[str | None, list[TreeNode]] = {
    None: [
        TreeNode("rev1", "Review 1", has_children=False, icon="subscriptions"),
        TreeNode("rev2", "Review 2", has_children=False, icon="subscriptions"),
        TreeNode("rev3", "Review 3", has_children=False, icon="subscriptions"),
    ]
}

# AYON UI Qt

Qt widget library addon for AYON. It provides AYON-styled widgets,
data models, and utility components for building consistent desktop tools.

## Overview

`ayon-ui-qt` packages reusable UI building blocks that mirror AYON's visual
language while staying native to Qt. It includes:

- A custom `QStyle` implementation (`AYONStyle`) and style helpers
- Component widgets (buttons, form controls, containers, cards, filters)
- Data-driven views and models for paginated tables and lazy trees
- Async task queue utilities for non-blocking model/view updates

## Recent Changes

- Added/expanded advanced data components:
  - `PaginatedTableModel` with async fetch, sorting, tree mode, and
       optional event-loop batch fetching via `fetch_page_batch`
  - `AYTableView` support for persistent editor widgets through
       `TableColumn.widget_factory`
  - `LazyTreeModel` for async on-demand tree loading
- Added richer filtering/tagging and selection components:
  - `AYFilter`, `AYFilterByCategory`, `AYTableFilter`, `AYTagSelector`
- Added more view widgets and helpers:
  - `AYCardView`, `AYGalleryDialog`, `AYFilterableList`, `AYSlicer`
- Async infrastructure and monitoring:
  - `AsyncTaskQueue` and `AsyncTaskQueueMonitor`

## Installation

### As an AYON Addon

1. Build the addon package:

    ```bash
    python create_package.py
    ```

2. Upload the generated zip package from `dist/` to your AYON server.
3. Enable the addon in AYON Studio Settings.

### For Development

```bash
uv sync
uv run pytest
```

Python requirement: `>=3.9.1,<3.10`

## Quick Start

```python
from qtpy.QtWidgets import QApplication

from ayon_ui_qt.style import get_ayon_style, style_widget_and_siblings
from ayon_ui_qt.components.buttons import AYButton
from ayon_ui_qt.components.container import AYContainer
from ayon_ui_qt.components.label import AYLabel

app = QApplication([])
app.setStyle(get_ayon_style())

container = AYContainer(
      layout=AYContainer.Layout.VBox,
      variant=AYContainer.Variants.Low,
      layout_margin=10,
      layout_spacing=8,
)

container.add_widget(
      AYButton("Run", variant=AYButton.Variants.Filled, icon="play_arrow")
)
container.add_widget(
      AYLabel("Ready", icon="check_circle", icon_color="#60c689")
)

style_widget_and_siblings(container)
container.show()
app.exec()
```

## Paginated Model API

`PaginatedTableModel` expects a page fetch callback with this signature:

```python
def fetch_page(
      page: int,
      page_size: int,
      sort_key: str | None,
      descending: bool,
      parent_id: str | None,
) -> list[dict]:
      ...
```

Optional batch callback (tree mode child fetches):

```python
from ayon_ui_qt.components.table_model import BatchFetchRequest


def fetch_page_batch(
      requests: list[BatchFetchRequest],
) -> dict[str | None, list[dict]]:
      ...
```

Notes:

- Root-level fetch uses `fetch_page`
- Child-node fetches can be coalesced per event-loop tick using
   `fetch_page_batch`
- Use `reset_data()` when external context changes (project/folder/filter)

## Component Catalog

### Core Widgets

| Module | Main classes |
| --- | --- |
| `buttons.py` | `AYButton`, `AYButtonMenu` |
| `check_box.py` | `AYCheckBox` |
| `combo_box.py` | `AYComboBox`, `AYComboBoxModel` |
| `line_edit.py` | `AYLineEdit` |
| `text_edit.py` | `AYTextEdit` |
| `text_box.py` | `AYTextBox`, `AYTextEditor` |
| `label.py` | `AYLabel` |
| `frame.py` | `AYFrame` |
| `container.py` | `AYContainer` |
| `scroll_area.py` | `AYScrollArea`, `AYScrollBar` |

### Data Views and Models

| Module | Main classes |
| --- | --- |
| `table_model.py` | `PaginatedTableModel`, `TableColumn`, `BatchFetchRequest` |
| `table_view.py` | `AYTableView`, `AYTableHeader` |
| `table_filter.py` | `AYTableFilter`, `AYTableFilterProxyModel` |
| `tree_model.py` | `LazyTreeModel`, `TreeNode` |
| `tree_view.py` | `AYTreeView` |
| `card_view.py` | `AYCardView` |

### Entity and Content Widgets

| Module | Main classes |
| --- | --- |
| `entity_card.py` | `AYEntityCard` |
| `entity_path.py` | `AYEntityPath`, `AYEntityPathSegment` |
| `entity_thumbnail.py` | `AYEntityThumbnail` |
| `comment.py` | `AYComment` and related comment widgets |
| `comment_completion.py` | Comment completion helpers |
| `gallery_dialog.py` | `AYGalleryDialog` |
| `user_image.py` | `AYUserImage` |

### Filtering, Tags, and Selection

| Module | Main classes |
| --- | --- |
| `filter.py` | `AYFilter`, `AYFilterByCategory`, `FilterItem` |
| `filterable_list.py` | `AYFilterableList` |
| `tag.py` | `AYTag` |
| `tag_selector.py` | `AYTagSelector`, `TagData` |
| `slicer.py` | `AYSlicer` |
| `dropdown.py` | `AYDropdownPopup` |

### Layout and Utility Components

| Module | Main classes |
| --- | --- |
| `layouts.py` | `AYHBoxLayout`, `AYVBoxLayout`, `AYGridLayout`, `AYFlowLayout` |
| `task_queue.py` | `AsyncTaskQueue`, `AsyncTask`, queue helpers |
| `task_queue_monitor.py` | `AsyncTaskQueueMonitor` |
| `qss_override.py` | QSS/style event filter helpers |
| `checkbox_handler.py` | Checkbox event/data helpers |
| `screenshot_capture.py` | Widget screenshot capture helpers |

## Project Structure

```text
ayon-ui-qt/
├── client/
│   └── ayon_ui_qt/
│       ├── __init__.py
│       ├── addon.py
│       ├── style.py
│       ├── variants.py
│       ├── components/
│       ├── resources/
│       └── vendor/
├── server/
│   └── __init__.py
├── package.py
├── create_package.py
├── pyproject.toml
├── TESTING.md
└── README.md
```

## Development

- Install dependencies: `uv sync`
- Run tests: `uv run pytest`
- Run a single test: `uv run pytest tests/<file>::<test> -v`
- Format: `uv run ruff format <file>`
- Lint: `uv run ruff check <file>`

Detailed visual testing workflow is documented in `TESTING.md`.

## License

Apache-2.0

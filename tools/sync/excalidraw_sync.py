"""
Utilities for converting Drauvye IR into a matching Excalidraw file.

For this first pass we render nodes as text elements and edges as bound arrows.
Frames are preserved in the IR but are not yet mapped to Excalidraw containers.
"""

import json
import logging
import random
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _base_dir() -> Path:
    return Path(__file__).parent.parent.parent


def load_current_config() -> dict[str, Any]:
    config_file = _base_dir() / "current.config"
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_board_paths() -> tuple[Path, Path]:
    config = load_current_config()
    board_dir_raw = config.get("path")
    proj_name = config.get("proj_name")

    if not board_dir_raw or not proj_name:
        raise ValueError("No board path set in current.config. Call set_board first.")

    board_dir = Path(board_dir_raw)
    ir_path = board_dir / f"{proj_name}_drauvye_ir.json"
    excalidraw_path = board_dir / f"{proj_name}.excalidraw"
    return ir_path, excalidraw_path


def load_ir() -> dict[str, Any]:
    ir_path, _ = get_board_paths()
    if not ir_path.exists():
        raise FileNotFoundError(f"IR file not found: {ir_path}")

    with open(ir_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_excalidraw_template() -> dict[str, Any]:
    template_path = _base_dir() / "templates" / "excalidraw_template.json"
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _text_metrics(text: str) -> tuple[float, float]:
    lines = text.splitlines() or [""]
    longest_line = max(len(line) for line in lines)
    width = max(120.0, min(320.0, 24.0 + longest_line * 8.0))
    height = max(40.0, 20.0 + (len(lines) * 22.0))
    return width, height


def _index_token(index: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    return f"a{alphabet[index % len(alphabet)]}{index // len(alphabet) if index >= len(alphabet) else ''}"


def _seed() -> int:
    return random.randint(1, 2_000_000_000)


def _timestamp() -> int:
    return int(time.time() * 1000)


def _make_text_element(node: dict[str, Any], index: int, position: tuple[float, float]) -> dict[str, Any]:
    text = str(node.get("text", ""))
    width, height = _text_metrics(text)
    x, y = position
    return {
        "id": node["id"],
        "type": "text",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "index": _index_token(index),
        "roundness": None,
        "seed": _seed(),
        "version": 1,
        "versionNonce": random.randint(1, 2_000_000_000),
        "isDeleted": False,
        "boundElements": [],
        "updated": _timestamp(),
        "link": None,
        "locked": False,
        "text": text,
        "fontSize": 20,
        "fontFamily": 5,
        "textAlign": "left",
        "verticalAlign": "top",
        "containerId": None,
        "originalText": text,
        "autoResize": True,
        "lineHeight": 1.25,
    }


def _center_of(element: dict[str, Any]) -> tuple[float, float]:
    return (
        float(element["x"]) + float(element["width"]) / 2.0,
        float(element["y"]) + float(element["height"]) / 2.0,
    )


def _make_arrow_element(
    edge: dict[str, Any],
    start_element: dict[str, Any],
    end_element: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    start_x, start_y = _center_of(start_element)
    end_x, end_y = _center_of(end_element)
    origin_x = min(start_x, end_x)
    origin_y = min(start_y, end_y)

    return {
        "id": edge["id"],
        "type": "arrow",
        "x": origin_x,
        "y": origin_y,
        "width": abs(end_x - start_x),
        "height": abs(end_y - start_y),
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "index": _index_token(index),
        "roundness": {"type": 2},
        "seed": _seed(),
        "version": 1,
        "versionNonce": random.randint(1, 2_000_000_000),
        "isDeleted": False,
        "boundElements": None,
        "updated": _timestamp(),
        "link": None,
        "locked": False,
        "points": [
            [start_x - origin_x, start_y - origin_y],
            [end_x - origin_x, end_y - origin_y],
        ],
        "lastCommittedPoint": None,
        "startBinding": {
            "elementId": start_element["id"],
            "focus": 0.5,
            "gap": 8,
        },
        "endBinding": {
            "elementId": end_element["id"],
            "focus": 0.5,
            "gap": 8,
        },
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "elbowed": False,
    }


def _layout_nodes(nodes: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    base_x = 120.0
    base_y = 120.0
    column_gap = 260.0
    row_gap = 150.0
    columns = 3

    for index, node in enumerate(nodes):
        column = index % columns
        row = index // columns
        positions[node["id"]] = (
            base_x + column * column_gap,
            base_y + row * row_gap,
        )

    return positions


def _attach_edge_backrefs(nodes_by_id: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    for node in nodes_by_id.values():
        node["boundElements"] = []

    for edge in edges:
        start_id = edge.get("from")
        end_id = edge.get("to")
        if start_id in nodes_by_id:
            nodes_by_id[start_id]["boundElements"].append({"id": edge["id"], "type": "arrow"})
        if end_id in nodes_by_id:
            nodes_by_id[end_id]["boundElements"].append({"id": edge["id"], "type": "arrow"})


def sync_excalidraw_from_ir(ir_data: dict[str, Any] | None = None) -> Path:
    """
    Regenerate the board's .excalidraw file from the current IR.

    Nodes become text elements and edges become bound arrows. Frames are left
    untouched for now.
    """
    if ir_data is None:
        ir_data = load_ir()

    _, excalidraw_path = get_board_paths()
    template = _load_excalidraw_template()

    nodes = list(ir_data.get("nodes", []))
    edges = list(ir_data.get("edges", []))
    positions = _layout_nodes(nodes)

    node_elements: list[dict[str, Any]] = []
    nodes_by_id: dict[str, dict[str, Any]] = {}

    for index, node in enumerate(nodes):
        position = positions.get(node["id"], (120.0, 120.0))
        element = _make_text_element(node, index, position)
        node_elements.append(element)
        nodes_by_id[element["id"]] = element

    _attach_edge_backrefs(nodes_by_id, edges)

    arrow_elements: list[dict[str, Any]] = []
    for edge_index, edge in enumerate(edges, start=len(node_elements)):
        start_id = edge.get("from")
        end_id = edge.get("to")
        if start_id not in nodes_by_id or end_id not in nodes_by_id:
            logger.warning("Skipping edge %s because one endpoint is missing", edge.get("id"))
            continue
        arrow_elements.append(
            _make_arrow_element(
                edge,
                nodes_by_id[start_id],
                nodes_by_id[end_id],
                edge_index,
            )
        )

    excalidraw_data = {
        "type": template.get("type", "excalidraw"),
        "version": template.get("version", 2),
        "source": template.get("source", "https://excalidraw.com"),
        "elements": node_elements + arrow_elements,
        "appState": template.get("appState", {}),
        "files": template.get("files", {}),
    }

    tmp_path = excalidraw_path.with_name(f"{excalidraw_path.name}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(excalidraw_data, f, indent=2)

    tmp_path.replace(excalidraw_path)
    logger.info("Excalidraw synced: %s", excalidraw_path)
    return excalidraw_path

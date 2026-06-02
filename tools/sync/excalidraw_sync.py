"""
Utilities for converting Drauvye IR into a matching Excalidraw file.

Nodes become text elements, edges become bound arrows, and frames become
Excalidraw frame containers when the IR provides frame bounds.
"""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Any

from graph.frame_layout import measure_node

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


def _index_token(index: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    return f"a{alphabet[index % len(alphabet)]}{index // len(alphabet) if index >= len(alphabet) else ''}"


def _seed() -> int:
    return random.randint(1, 2_000_000_000)


def _timestamp() -> int:
    return int(time.time() * 1000)


def _make_text_element(node: dict[str, Any], index: int, position: tuple[float, float]) -> dict[str, Any]:
    text = str(node.get("text", ""))
    width, height = measure_node(node)
    x = float(node.get("x", position[0]))
    y = float(node.get("y", position[1]))
    return {
        "id": node["id"],
        "type": "text",
        "x": x,
        "y": y,
        "width": float(node.get("width", width)),
        "height": float(node.get("height", height)),
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": node.get("frame_id"),
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


def _make_frame_element(frame: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": frame["id"],
        "type": "frame",
        "x": float(frame.get("x", 100.0)),
        "y": float(frame.get("y", 100.0)),
        "width": float(frame.get("width", 320.0)),
        "height": float(frame.get("height", 220.0)),
        "angle": 0,
        "strokeColor": "#bbb",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
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
        "name": frame.get("name"),
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


def _frame_bounds_from_nodes(frame_nodes: list[dict[str, Any]]) -> dict[str, float]:
    if not frame_nodes:
        return {"x": 100.0, "y": 100.0, "width": 280.0, "height": 180.0}

    padding_x = 40.0
    padding_y = 56.0
    header_space = 28.0

    min_x = min(float(node.get("x", 0.0)) for node in frame_nodes)
    min_y = min(float(node.get("y", 0.0)) for node in frame_nodes)
    max_x = max(float(node.get("x", 0.0)) + float(node.get("width", 0.0)) for node in frame_nodes)
    max_y = max(float(node.get("y", 0.0)) + float(node.get("height", 0.0)) for node in frame_nodes)

    return {
        "x": min_x - padding_x,
        "y": min_y - padding_y - header_space,
        "width": (max_x - min_x) + padding_x * 2,
        "height": (max_y - min_y) + padding_y + header_space,
    }


def sync_excalidraw_from_ir(ir_data: dict[str, Any] | None = None) -> Path:
    """
    Regenerate the board's .excalidraw file from the current IR.

    Nodes become text elements, edges become bound arrows, and frames become
    Excalidraw frame elements when bounds are available.
    """
    if ir_data is None:
        ir_data = load_ir()

    _, excalidraw_path = get_board_paths()
    template = _load_excalidraw_template()

    nodes = list(ir_data.get("nodes", []))
    edges = list(ir_data.get("edges", []))
    frames = list(ir_data.get("frames", []))

    positions = _layout_nodes(nodes)
    node_elements: list[dict[str, Any]] = []
    nodes_by_id: dict[str, dict[str, Any]] = {}

    node_to_frame_id: dict[str, str] = {}
    for frame in frames:
        for node_id in frame.get("elements", []):
            if node_id not in node_to_frame_id:
                node_to_frame_id[node_id] = frame["id"]

    for index, node in enumerate(nodes):
        position = positions.get(node["id"], (120.0, 120.0))
        element = _make_text_element(node, index, position)
        element["frameId"] = node_to_frame_id.get(node["id"])
        node_elements.append(element)
        nodes_by_id[element["id"]] = element

    _attach_edge_backrefs(nodes_by_id, edges)

    frame_elements: list[dict[str, Any]] = []
    for frame_index, frame in enumerate(frames):
        frame_nodes = [nodes_by_id[node_id] for node_id in frame.get("elements", []) if node_id in nodes_by_id]
        if "x" not in frame or "y" not in frame or "width" not in frame or "height" not in frame:
            frame_bounds = _frame_bounds_from_nodes(frame_nodes)
        else:
            frame_bounds = {
                "x": float(frame["x"]),
                "y": float(frame["y"]),
                "width": float(frame["width"]),
                "height": float(frame["height"]),
            }
        frame = {**frame, **frame_bounds}
        frame_elements.append(_make_frame_element(frame, frame_index))

    arrow_elements: list[dict[str, Any]] = []
    for edge_index, edge in enumerate(edges, start=len(node_elements) + len(frame_elements)):
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
        "elements": frame_elements + node_elements + arrow_elements,
        "appState": template.get("appState", {}),
        "files": template.get("files", {}),
    }

    tmp_path = excalidraw_path.with_name(f"{excalidraw_path.name}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(excalidraw_data, f, indent=2)

    tmp_path.replace(excalidraw_path)
    logger.info("Excalidraw synced: %s", excalidraw_path)
    return excalidraw_path


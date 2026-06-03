"""
Graph operations tools for Drauvye MCP Server
Handles adding/removing nodes, edges, frames, and frame layout relaxation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp.types import TextContent, CallToolResult

from graph.aliasing import (
    build_alias_maps,
    resolve_edge_ref,
    resolve_frame_ref,
    resolve_node_ref,
)
from graph.frame_layout import relax_nodes_in_frame
from sync.excalidraw_sync import get_board_paths, sync_excalidraw_from_ir, sync_ir_from_excalidraw

logger = logging.getLogger(__name__)


def get_ir_path():
    """Get the repo-local IR file path for the active diagram."""
    ir_path, _ = get_board_paths()
    return ir_path


def get_current_config_path() -> Path:
    return Path(__file__).parent.parent.parent / "current.config"


def load_current_config() -> dict[str, Any]:
    config_file = get_current_config_path()
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_current_config(config: dict[str, Any]) -> None:
    config_file = get_current_config_path()
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_ir():
    """Load the IR JSON file"""
    sync_ir_from_excalidraw()
    ir_path = get_ir_path()

    if not ir_path.exists():
        raise FileNotFoundError(f"IR file not found: {ir_path}")

    with open(ir_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_ir(ir_data: dict):
    """Save the IR JSON file"""
    ir_path = get_ir_path()

    with open(ir_path, "w", encoding="utf-8") as f:
        json.dump(ir_data, f, indent=2)

    logger.info("IR saved: %s", ir_path)
    sync_excalidraw_from_ir(ir_data)


def _node_alias_map(ir_data: dict[str, Any]) -> dict[str, str]:
    return build_alias_maps(ir_data)[0]


def _edge_alias_map(ir_data: dict[str, Any]) -> dict[str, str]:
    return build_alias_maps(ir_data)[1]


def _frame_alias_map(ir_data: dict[str, Any]) -> dict[str, str]:
    return build_alias_maps(ir_data)[2]


def _format_node_ref(ir_data: dict[str, Any], node_id: str) -> str:
    aliases = _node_alias_map(ir_data)
    node = next((n for n in ir_data.get("nodes", []) if n["id"] == node_id), None)
    return aliases.get(node_id, node_id) if node else node_id


def _format_edge_ref(ir_data: dict[str, Any], edge_id: str) -> str:
    aliases = _edge_alias_map(ir_data)
    return aliases.get(edge_id, edge_id)


def _format_frame_ref(ir_data: dict[str, Any], frame_id: str) -> str:
    aliases = _frame_alias_map(ir_data)
    return aliases.get(frame_id, frame_id)


def _active_frame(ir_data: dict[str, Any]) -> dict[str, Any] | None:
    active_frame_id = load_current_config().get("active_frame_id")
    if not active_frame_id:
        return None
    return next((frame for frame in ir_data.get("frames", []) if frame.get("id") == active_frame_id), None)


def _active_frame_center(ir_data: dict[str, Any]) -> tuple[float, float, str | None]:
    frame = _active_frame(ir_data)
    if not frame:
        return 0.0, 0.0, None

    x = float(frame.get("x", 0.0))
    y = float(frame.get("y", 0.0))
    width = float(frame.get("width", 0.0))
    height = float(frame.get("height", 0.0))
    return x + width / 2.0, y + height / 2.0, frame["id"]


def _coerce_texts(arguments: dict[str, Any]) -> list[str]:
    if "texts" in arguments:
        raw_nodes = arguments.get("texts", [])
    else:
        raw_nodes = arguments.get("nodes", [])

    texts: list[str] = []
    for item in raw_nodes:
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            text = str(item.get("text", ""))
        else:
            text = ""
        if text:
            texts.append(text)
    return texts


def _coerce_edges(arguments: dict[str, Any]) -> list[dict[str, str]]:
    raw_edges = arguments.get("edges", [])
    edges: list[dict[str, str]] = []
    for item in raw_edges:
        if not isinstance(item, dict):
            continue
        from_ref = item.get("from") or item.get("from_node") or item.get("source")
        to_ref = item.get("to") or item.get("to_node") or item.get("target")
        if from_ref and to_ref:
            edges.append({"from": str(from_ref), "to": str(to_ref)})
    return edges


async def set_frame(arguments: dict[str, Any]) -> CallToolResult:
    """Set the active frame before adding nodes and edges."""
    frame_ref = arguments.get("frame_id") or arguments.get("frame_name")

    if not frame_ref:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: frame_id or frame_name is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        frame_id = resolve_frame_ref(ir_data, frame_ref)
        if not frame_id:
            matching_frame = next((f for f in ir_data.get("frames", []) if f.get("name") == frame_ref), None)
            frame_id = matching_frame["id"] if matching_frame else None
        if not frame_id:
            frame_aliases = _frame_alias_map(ir_data)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error: Frame '{frame_ref}' not found. Available: {list(frame_aliases.values())}",
                    )
                ],
                isError=True,
            )

        config = load_current_config()
        config["active_frame_id"] = frame_id
        save_current_config(config)

        frame_alias = _format_frame_ref(ir_data, frame_id)
        frame = next((f for f in ir_data.get("frames", []) if f["id"] == frame_id), {})
        result_message = f"Active frame set successfully!\nFrame: {frame_alias}\nFrame Name: {frame.get('name', '')}"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in set_frame: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def add_nodes(arguments: dict[str, Any]) -> CallToolResult:
    """Add multiple nodes to the IR."""
    texts = _coerce_texts(arguments)

    if not texts:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: texts is required and must contain at least one value")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        x, y, frame_id = _active_frame_center(ir_data)
        created_nodes: list[dict[str, Any]] = []

        for text in texts:
            node = {
                "id": str(uuid4()),
                "text": text,
                "x": x,
                "y": y,
            }
            if frame_id:
                node["frame_id"] = frame_id
            ir_data["nodes"].append(node)
            created_nodes.append(node)

        if frame_id:
            frame = next((f for f in ir_data.get("frames", []) if f.get("id") == frame_id), None)
            if frame is not None:
                frame.setdefault("elements", [])
                for node in created_nodes:
                    if node["id"] not in frame["elements"]:
                        frame["elements"].append(node["id"])

        save_ir(ir_data)

        result_lines = ["Nodes added successfully!"]
        for node in created_nodes:
            result_lines.append(f"  - {_format_node_ref(ir_data, node['id'])}: {node['text']}")
        if frame_id:
            result_lines.append(f"Placed at active frame center: {_format_frame_ref(ir_data, frame_id)}")
        else:
            result_lines.append("Placed at default position: x=0.0, y=0.0")

        result_message = "\n".join(result_lines)
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in add_nodes: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def add_edges(arguments: dict[str, Any]) -> CallToolResult:
    """Add multiple edges between nodes."""
    edge_specs = _coerce_edges(arguments)

    if not edge_specs:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: edges is required and must contain from/to values")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        _, _, active_frame_id = _active_frame_center(ir_data)
        created_edges: list[dict[str, str]] = []

        for edge_spec in edge_specs:
            from_node = resolve_node_ref(ir_data, edge_spec["from"])
            to_node = resolve_node_ref(ir_data, edge_spec["to"])
            if not from_node or not to_node:
                node_aliases = _node_alias_map(ir_data)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=(
                                "Error: One or both nodes don't exist. "
                                f"Failed edge: {edge_spec['from']} -> {edge_spec['to']}. "
                                f"Available nodes: {list(node_aliases.values())}"
                            ),
                        )
                    ],
                    isError=True,
                )

            edge = {
                "id": str(uuid4()),
                "from": from_node,
                "to": to_node,
            }
            if active_frame_id:
                edge["frame_id"] = active_frame_id
            ir_data["edges"].append(edge)
            created_edges.append(edge)

        save_ir(ir_data)

        result_lines = ["Edges added successfully!"]
        for edge in created_edges:
            result_lines.append(
                f"  - {_format_edge_ref(ir_data, edge['id'])}: "
                f"{_format_node_ref(ir_data, edge['from'])} -> {_format_node_ref(ir_data, edge['to'])}"
            )
        if active_frame_id:
            result_lines.append(f"Active frame: {_format_frame_ref(ir_data, active_frame_id)}")

        result_message = "\n".join(result_lines)
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in add_edges: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def add_node(arguments: dict[str, Any]) -> CallToolResult:
    """Add a node to the IR with given text"""
    text = arguments.get("text")

    if not text:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: text is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()

        node_id = str(uuid4())
        node = {
            "id": node_id,
            "text": text,
        }

        ir_data["nodes"].append(node)
        save_ir(ir_data)

        node_alias = _format_node_ref(ir_data, node_id)
        result_message = f"Node added successfully!\nNode: {node_alias}\nText: {text}"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in add_node: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def add_edge(arguments: dict[str, Any]) -> CallToolResult:
    """Add an edge between two nodes"""
    from_node_ref = arguments.get("from")
    to_node_ref = arguments.get("to")

    if not from_node_ref or not to_node_ref:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'from' and 'to' node IDs are required")],
            isError=True,
        )

    try:
        ir_data = load_ir()

        from_node = resolve_node_ref(ir_data, from_node_ref)
        to_node = resolve_node_ref(ir_data, to_node_ref)
        if not from_node or not to_node:
            node_aliases = _node_alias_map(ir_data)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=(
                            "Error: One or both nodes don't exist. "
                            f"Available nodes: {list(node_aliases.values())}"
                        ),
                    )
                ],
                isError=True,
            )

        edge_id = str(uuid4())
        edge = {
            "id": edge_id,
            "from": from_node,
            "to": to_node,
        }

        ir_data["edges"].append(edge)
        save_ir(ir_data)

        edge_alias = _format_edge_ref(ir_data, edge_id)
        result_message = (
            f"Edge added successfully!\nEdge: {edge_alias}\n"
            f"From: {_format_node_ref(ir_data, from_node)} -> To: {_format_node_ref(ir_data, to_node)}"
        )
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in add_edge: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def add_frame(arguments: dict[str, Any]) -> CallToolResult:
    """Add a frame with a list of node IDs or aliases"""
    node_list = arguments.get("node_list", [])
    frame_name = arguments.get("frame_name", f"Frame_{uuid4().hex[:8]}")

    try:
        ir_data = load_ir()

        resolved_nodes: list[str] = []
        for node_ref in node_list:
            node_id = resolve_node_ref(ir_data, node_ref)
            if not node_id:
                node_aliases = _node_alias_map(ir_data)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: Node {node_ref} doesn't exist. Available: {list(node_aliases.values())}",
                        )
                    ],
                    isError=True,
                )
            resolved_nodes.append(node_id)

        frame_id = str(uuid4())
        frame = {
            "id": frame_id,
            "name": frame_name,
            "elements": resolved_nodes,
        }

        ir_data["frames"].append(frame)
        save_ir(ir_data)

        frame_alias = _format_frame_ref(ir_data, frame_id)
        element_aliases = [_format_node_ref(ir_data, node_id) for node_id in resolved_nodes]
        result_message = (
            f"Frame added successfully!\nFrame: {frame_alias}\n"
            f"Frame Name: {frame_name}\nElements: {element_aliases}"
        )
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in add_frame: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def relax_frame(arguments: dict[str, Any]) -> CallToolResult:
    """Re-layout all nodes in a frame after adding a batch of nodes and edges."""
    frame_ref = arguments.get("frame_id") or arguments.get("frame_name")

    if not frame_ref:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: frame_id or frame_name is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        frame_id = resolve_frame_ref(ir_data, frame_ref)
        if not frame_id:
            frame_aliases = _frame_alias_map(ir_data)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error: Frame '{frame_ref}' not found. Available: {list(frame_aliases.values())}",
                    )
                ],
                isError=True,
            )

        frame = next((f for f in ir_data.get("frames", []) if f["id"] == frame_id), None)
        if not frame:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Frame '{frame_ref}' not found")],
                isError=True,
            )

        nodes_by_id = {node["id"]: node for node in ir_data.get("nodes", [])}
        frame_nodes = [nodes_by_id[node_id] for node_id in frame.get("elements", []) if node_id in nodes_by_id]
        if not frame_nodes:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Frame '{frame.get('name', frame_ref)}' has no valid nodes to arrange")],
                isError=False,
            )

        positions, bounds = relax_nodes_in_frame(frame, frame_nodes, ir_data.get("edges", []))
        for node in frame_nodes:
            x, y = positions[node["id"]]
            width, height = node.get("width"), node.get("height")
            if width is None or height is None:
                from graph.frame_layout import measure_node
                width, height = measure_node(node)
            node["x"] = x
            node["y"] = y
            node["width"] = width
            node["height"] = height
            node["frame_id"] = frame_id

        frame["x"] = bounds["x"]
        frame["y"] = bounds["y"]
        frame["width"] = bounds["width"]
        frame["height"] = bounds["height"]
        frame["layout"] = {
            "type": "grid",
            "columns": max(1, min(3, len(frame_nodes))),
        }

        save_ir(ir_data)

        frame_alias = _format_frame_ref(ir_data, frame_id)
        node_aliases = [_format_node_ref(ir_data, node["id"]) for node in frame_nodes]
        result_message = (
            f"Frame relaxed successfully!\nFrame: {frame_alias}\n"
            f"Nodes arranged: {node_aliases}\n"
            f"Bounds: x={bounds['x']}, y={bounds['y']}, width={bounds['width']}, height={bounds['height']}"
        )
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in relax_frame: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_node(arguments: dict[str, Any]) -> CallToolResult:
    """Remove a node from the IR"""
    node_ref = arguments.get("node_id")

    if not node_ref:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: node_id is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        node_id = resolve_node_ref(ir_data, node_ref)
        if not node_id:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Node {node_ref} not found")],
                isError=True,
            )

        initial_count = len(ir_data["nodes"])
        ir_data["nodes"] = [n for n in ir_data["nodes"] if n["id"] != node_id]

        if len(ir_data["nodes"]) == initial_count:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Node {node_ref} not found")],
                isError=True,
            )

        ir_data["edges"] = [e for e in ir_data["edges"] if e["from"] != node_id and e["to"] != node_id]

        for frame in ir_data["frames"]:
            frame["elements"] = [nid for nid in frame["elements"] if nid != node_id]

        save_ir(ir_data)

        result_message = f"Node {_format_node_ref(ir_data, node_id)} removed successfully (including connected edges and frame references)"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in remove_node: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_nodes(arguments: dict[str, Any]) -> CallToolResult:
    """Remove multiple nodes from the IR."""
    node_refs = arguments.get("node_ids") or arguments.get("nodes") or []

    if not node_refs:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: node_ids is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        resolved_node_ids: list[str] = []
        for node_ref in node_refs:
            node_id = resolve_node_ref(ir_data, str(node_ref))
            if not node_id:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: Node {node_ref} not found")],
                    isError=True,
                )
            resolved_node_ids.append(node_id)

        node_id_set = set(resolved_node_ids)
        removed_aliases = [_format_node_ref(ir_data, node_id) for node_id in resolved_node_ids]
        initial_edge_count = len(ir_data["edges"])

        ir_data["nodes"] = [n for n in ir_data["nodes"] if n["id"] not in node_id_set]
        ir_data["edges"] = [e for e in ir_data["edges"] if e["from"] not in node_id_set and e["to"] not in node_id_set]

        for frame in ir_data["frames"]:
            frame["elements"] = [node_id for node_id in frame["elements"] if node_id not in node_id_set]

        removed_edge_count = initial_edge_count - len(ir_data["edges"])
        save_ir(ir_data)

        result_message = (
            "Nodes removed successfully!\n"
            f"Nodes: {removed_aliases}\n"
            f"Connected edges removed: {removed_edge_count}"
        )
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in remove_nodes: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_edge(arguments: dict[str, Any]) -> CallToolResult:
    """Remove an edge from the IR"""
    edge_ref = arguments.get("edge_id")

    if not edge_ref:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: edge_id is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        edge_id = resolve_edge_ref(ir_data, edge_ref)
        if not edge_id:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Edge {edge_ref} not found")],
                isError=True,
            )

        initial_count = len(ir_data["edges"])
        ir_data["edges"] = [e for e in ir_data["edges"] if e["id"] != edge_id]

        if len(ir_data["edges"]) == initial_count:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Edge {edge_ref} not found")],
                isError=True,
            )

        save_ir(ir_data)

        result_message = f"Edge {_format_edge_ref(ir_data, edge_id)} removed successfully"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in remove_edge: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_edges(arguments: dict[str, Any]) -> CallToolResult:
    """Remove multiple edges from the IR."""
    edge_refs = arguments.get("edge_ids") or arguments.get("edges") or []

    if not edge_refs:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: edge_ids is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        resolved_edge_ids: list[str] = []
        for edge_ref in edge_refs:
            edge_id = resolve_edge_ref(ir_data, str(edge_ref))
            if not edge_id:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: Edge {edge_ref} not found")],
                    isError=True,
                )
            resolved_edge_ids.append(edge_id)

        removed_aliases = [_format_edge_ref(ir_data, edge_id) for edge_id in resolved_edge_ids]
        edge_id_set = set(resolved_edge_ids)
        ir_data["edges"] = [e for e in ir_data["edges"] if e["id"] not in edge_id_set]

        save_ir(ir_data)

        result_message = f"Edges removed successfully!\nEdges: {removed_aliases}"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in remove_edges: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_frame(arguments: dict[str, Any]) -> CallToolResult:
    """Remove a frame from the IR"""
    frame_ref = arguments.get("frame_id")

    if not frame_ref:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: frame_id is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        frame_id = resolve_frame_ref(ir_data, frame_ref)
        if not frame_id:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Frame {frame_ref} not found")],
                isError=True,
            )

        initial_count = len(ir_data["frames"])
        ir_data["frames"] = [f for f in ir_data["frames"] if f["id"] != frame_id]

        if len(ir_data["frames"]) == initial_count:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Frame {frame_ref} not found")],
                isError=True,
            )

        save_ir(ir_data)

        result_message = f"Frame {_format_frame_ref(ir_data, frame_id)} removed successfully"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in remove_frame: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )

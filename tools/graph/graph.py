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
from sync.excalidraw_sync import sync_excalidraw_from_ir

logger = logging.getLogger(__name__)


def get_ir_path():
    """Get the IR file path from current.config"""
    config_file = Path(__file__).parent.parent.parent / "current.config"

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    if not config.get("path"):
        raise ValueError("No board path set in current.config. Call set_board first.")

    ir_path = Path(config["path"]) / f"{config['proj_name']}_drauvye_ir.json"
    return ir_path


def load_ir():
    """Load the IR JSON file"""
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
    """Re-layout all nodes in a frame and update the frame bounds."""
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

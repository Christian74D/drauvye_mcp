"""
Read operations tools for Drauvye MCP Server
Handles reading nodes, edges, frames and other IR data
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.types import TextContent, CallToolResult

from graph.aliasing import build_alias_maps

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


def _format_node_lines(ir_data: dict[str, Any]) -> list[str]:
    node_alias_by_id = build_alias_maps(ir_data)[0]
    lines = []
    for node in ir_data.get("nodes", []):
        alias = node_alias_by_id.get(node["id"], node["id"])
        lines.append(f"  - {alias}: {node.get('text', '')}")
    return lines


def _format_edge_lines(ir_data: dict[str, Any]) -> list[str]:
    node_alias_by_id, edge_alias_by_id, _ = build_alias_maps(ir_data)
    lines = []
    for edge in ir_data.get("edges", []):
        edge_alias = edge_alias_by_id.get(edge["id"], edge["id"])
        from_alias = node_alias_by_id.get(edge.get("from", ""), edge.get("from", "unknown"))
        to_alias = node_alias_by_id.get(edge.get("to", ""), edge.get("to", "unknown"))
        lines.append(f"  - {edge_alias}: {from_alias} -> {to_alias}")
    return lines


def _format_frame_lines(ir_data: dict[str, Any]) -> list[str]:
    node_alias_by_id, _, frame_alias_by_id = build_alias_maps(ir_data)
    lines = []
    for frame in ir_data.get("frames", []):
        frame_alias = frame_alias_by_id.get(frame["id"], frame["id"])
        node_aliases = [node_alias_by_id.get(node_id, node_id) for node_id in frame.get("elements", [])]
        lines.append(f"  - {frame_alias}: {frame.get('name', '')} | Nodes: {node_aliases}")
    return lines


async def read_graph(arguments: dict[str, Any]) -> CallToolResult:
    """Read and return the entire IR graph"""
    try:
        ir_data = load_ir()

        node_alias_by_id, edge_alias_by_id, frame_alias_by_id = build_alias_maps(ir_data)
        result_lines = [
            "Current Graph State:",
            "",
            f"Nodes ({len(ir_data.get('nodes', []))}):",
            *(_format_node_lines(ir_data) or ["  (none)"]),
            "",
            f"Edges ({len(ir_data.get('edges', []))}):",
            *(_format_edge_lines(ir_data) or ["  (none)"]),
            "",
            f"Frames ({len(ir_data.get('frames', []))}):",
            *(_format_frame_lines(ir_data) or ["  (none)"]),
        ]
        result_message = "\n".join(result_lines)

        logger.info("Graph read successfully")

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in read_graph: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def read_frame_get_all(arguments: dict[str, Any]) -> CallToolResult:
    """Read and return all frame names"""
    try:
        ir_data = load_ir()
        frames = ir_data.get("frames", [])

        if not frames:
            result_message = "No frames found in the graph"
        else:
            result_message = "Available Frames:\n"
            for frame in frames:
                frame_alias = frame_alias_by_id.get(frame["id"], frame["id"])
                result_message += f"  - {frame_alias}: {frame.get('name', '')}\n"

        logger.info("All frames read successfully")

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in read_frame_get_all: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def read_frame_get_elements(arguments: dict[str, Any]) -> CallToolResult:
    """Read and return all elements in a specific frame"""
    frame_name = arguments.get("frame_name")

    if not frame_name:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: frame_name is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()
        node_alias_by_id, _, frame_alias_by_id = build_alias_maps(ir_data)
        frames = ir_data.get("frames", [])

        target_frame = None
        for frame in frames:
            if frame.get("name") == frame_name or frame_alias_by_id.get(frame["id"]) == frame_name:
                target_frame = frame
                break

        if not target_frame:
            available_frames = [frame_alias_by_id.get(f["id"], f["id"]) for f in frames]
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Frame '{frame_name}' not found. Available: {available_frames}")],
                isError=True,
            )

        element_ids = target_frame.get("elements", [])
        result_lines = [f"Elements in frame '{target_frame.get('name', frame_name)}':"]
        if not element_ids:
            result_lines.append("  (empty frame)")
        else:
            for node_id in element_ids:
                node = next((n for n in ir_data.get("nodes", []) if n["id"] == node_id), None)
                if node:
                    result_lines.append(f"  - {node_alias_by_id.get(node_id, node_id)}: {node.get('text', '')}")
                else:
                    result_lines.append(f"  - (Node ID: {node_id} - not found)")

        logger.info("Frame elements read: %s", frame_name)

        return CallToolResult(
            content=[TextContent(type="text", text="\n".join(result_lines))],
            isError=False,
        )

    except Exception as e:
        logger.error("Error in read_frame_get_elements: %s", str(e))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )

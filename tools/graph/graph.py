"""
Graph operations tools for Drauvye MCP Server
Handles adding/removing nodes, edges, and frames
"""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp.types import TextContent, CallToolResult
from sync.excalidraw_sync import sync_excalidraw_from_ir

logger = logging.getLogger(__name__)


def get_ir_path():
    """Get the IR file path from current.config"""
    config_file = Path(__file__).parent.parent.parent / "current.config"

    with open(config_file, "r") as f:
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

    with open(ir_path, "r") as f:
        return json.load(f)


def save_ir(ir_data: dict):
    """Save the IR JSON file"""
    ir_path = get_ir_path()

    with open(ir_path, "w") as f:
        json.dump(ir_data, f, indent=2)

    logger.info(f"IR saved: {ir_path}")
    sync_excalidraw_from_ir(ir_data)


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

        result_message = f"Node added successfully!\nNode ID: {node_id}\nText: {text}"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in add_node: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def add_edge(arguments: dict[str, Any]) -> CallToolResult:
    """Add an edge between two nodes"""
    from_node = arguments.get("from")
    to_node = arguments.get("to")

    if not from_node or not to_node:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'from' and 'to' node IDs are required")],
            isError=True,
        )

    try:
        ir_data = load_ir()

        # Check if nodes exist
        node_ids = [node["id"] for node in ir_data["nodes"]]
        if from_node not in node_ids or to_node not in node_ids:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: One or both nodes don't exist. Available nodes: {node_ids}")],
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

        result_message = f"Edge added successfully!\nEdge ID: {edge_id}\nFrom: {from_node} -> To: {to_node}"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in add_edge: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def add_frame(arguments: dict[str, Any]) -> CallToolResult:
    """Add a frame with a list of node IDs"""
    node_list = arguments.get("node_list", [])
    frame_name = arguments.get("frame_name", f"Frame_{uuid4().hex[:8]}")

    try:
        ir_data = load_ir()

        # Check if all nodes exist
        node_ids = [node["id"] for node in ir_data["nodes"]]
        for node_id in node_list:
            if node_id not in node_ids:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: Node {node_id} doesn't exist")],
                    isError=True,
                )

        frame_id = str(uuid4())
        frame = {
            "id": frame_id,
            "name": frame_name,
            "elements": node_list,
        }

        ir_data["frames"].append(frame)
        save_ir(ir_data)

        result_message = f"Frame added successfully!\nFrame ID: {frame_id}\nFrame Name: {frame_name}\nElements: {node_list}"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in add_frame: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_node(arguments: dict[str, Any]) -> CallToolResult:
    """Remove a node from the IR"""
    node_id = arguments.get("node_id")

    if not node_id:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: node_id is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()

        # Find and remove the node
        initial_count = len(ir_data["nodes"])
        ir_data["nodes"] = [n for n in ir_data["nodes"] if n["id"] != node_id]

        if len(ir_data["nodes"]) == initial_count:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Node {node_id} not found")],
                isError=True,
            )

        # Remove edges connected to this node
        ir_data["edges"] = [e for e in ir_data["edges"] if e["from"] != node_id and e["to"] != node_id]

        # Remove node from all frames
        for frame in ir_data["frames"]:
            frame["elements"] = [nid for nid in frame["elements"] if nid != node_id]

        save_ir(ir_data)

        result_message = f"Node {node_id} removed successfully (including connected edges and frame references)"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in remove_node: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_edge(arguments: dict[str, Any]) -> CallToolResult:
    """Remove an edge from the IR"""
    edge_id = arguments.get("edge_id")

    if not edge_id:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: edge_id is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()

        # Find and remove the edge
        initial_count = len(ir_data["edges"])
        ir_data["edges"] = [e for e in ir_data["edges"] if e["id"] != edge_id]

        if len(ir_data["edges"]) == initial_count:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Edge {edge_id} not found")],
                isError=True,
            )

        save_ir(ir_data)

        result_message = f"Edge {edge_id} removed successfully"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in remove_edge: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def remove_frame(arguments: dict[str, Any]) -> CallToolResult:
    """Remove a frame from the IR"""
    frame_id = arguments.get("frame_id")

    if not frame_id:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: frame_id is required")],
            isError=True,
        )

    try:
        ir_data = load_ir()

        # Find and remove the frame
        initial_count = len(ir_data["frames"])
        ir_data["frames"] = [f for f in ir_data["frames"] if f["id"] != frame_id]

        if len(ir_data["frames"]) == initial_count:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Frame {frame_id} not found")],
                isError=True,
            )

        save_ir(ir_data)

        result_message = f"Frame {frame_id} removed successfully"
        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in remove_frame: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )

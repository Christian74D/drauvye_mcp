"""
Read operations tools for Drauvye MCP Server
Handles reading nodes, edges, frames and other IR data
"""

import json
import logging
from pathlib import Path
from typing import Any

from mcp.types import TextContent, CallToolResult

logger = logging.getLogger(__name__)


def get_ir_path():
    """Get the IR file path from current.config"""
    config_file = Path(__file__).parent.parent.parent / "current.config"
    
    with open(config_file, 'r') as f:
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
    
    with open(ir_path, 'r') as f:
        return json.load(f)


async def read_graph(arguments: dict[str, Any]) -> CallToolResult:
    """Read and return the entire IR graph"""
    try:
        ir_data = load_ir()
        
        # Format the output nicely
        result_message = f"""Current Graph State:

Nodes ({len(ir_data.get('nodes', []))}):\n"""
        for node in ir_data.get('nodes', []):
            result_message += f"  - ID: {node['id']}, Text: {node['text']}\n"
        
        result_message += f"\nEdges ({len(ir_data.get('edges', []))}):\n"
        for edge in ir_data.get('edges', []):
            result_message += f"  - ID: {edge['id']}, {edge['from']} → {edge['to']}\n"
        
        result_message += f"\nFrames ({len(ir_data.get('frames', []))}):\n"
        for frame in ir_data.get('frames', []):
            result_message += f"  - ID: {frame['id']}, Name: {frame['name']}, Elements: {frame['elements']}\n"
        
        logger.info("Graph read successfully")
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False
        )
    
    except Exception as e:
        logger.error(f"Error in read_graph: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


async def read_frame_get_all(arguments: dict[str, Any]) -> CallToolResult:
    """Read and return all frame names"""
    try:
        ir_data = load_ir()
        frames = ir_data.get('frames', [])
        
        if not frames:
            result_message = "No frames found in the graph"
        else:
            result_message = "Available Frames:\n"
            for frame in frames:
                result_message += f"  - {frame['name']} (ID: {frame['id']})\n"
        
        logger.info("All frames read successfully")
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False
        )
    
    except Exception as e:
        logger.error(f"Error in read_frame_get_all: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


async def read_frame_get_elements(arguments: dict[str, Any]) -> CallToolResult:
    """Read and return all elements in a specific frame"""
    frame_name = arguments.get("frame_name")
    
    if not frame_name:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: frame_name is required")],
            isError=True
        )
    
    try:
        ir_data = load_ir()
        frames = ir_data.get('frames', [])
        
        # Find the frame by name
        target_frame = None
        for frame in frames:
            if frame['name'] == frame_name:
                target_frame = frame
                break
        
        if not target_frame:
            available_frames = [f['name'] for f in frames]
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Frame '{frame_name}' not found. Available: {available_frames}")],
                isError=True
            )
        
        # Get the elements (node IDs) in the frame
        element_ids = target_frame['elements']
        
        # Get the actual node data
        nodes = {node['id']: node for node in ir_data.get('nodes', [])}
        
        result_message = f"Elements in frame '{frame_name}':\n"
        if not element_ids:
            result_message += "  (empty frame)"
        else:
            for node_id in element_ids:
                node = nodes.get(node_id)
                if node:
                    result_message += f"  - {node['text']} (ID: {node_id})\n"
                else:
                    result_message += f"  - (Node ID: {node_id} - not found)\n"
        
        logger.info(f"Frame elements read: {frame_name}")
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False
        )
    
    except Exception as e:
        logger.error(f"Error in read_frame_get_elements: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )

#!/usr/bin/env python3
"""
Drauvye MCP Server - A Model Context Protocol server for managing Drauvye project boards.
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

# Add tools folder to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from setup.setup import set_board
from graph.graph import add_node, add_edge, add_frame, remove_node, remove_edge, remove_frame
from read.read import read_graph, read_frame_get_all, read_frame_get_elements

# Set up logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("drauvye")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="set_board",
            description="Set up a Drauvye board in a specified folder. Creates a .drauvye folder with IR and Excalidraw files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "The base folder path where the .drauvye folder will be created"
                    },
                    "name": {
                        "type": "string",
                        "description": "The name for the board"
                    }
                },
                "required": ["folder_path", "name"]
            }
        ),
        Tool(
            name="add_node",
            description="Add a node to the graph with given text",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text content of the node"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="add_edge",
            description="Add an edge between two nodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "from": {
                        "type": "string",
                        "description": "The ID of the source node"
                    },
                    "to": {
                        "type": "string",
                        "description": "The ID of the target node"
                    }
                },
                "required": ["from", "to"]
            }
        ),
        Tool(
            name="add_frame",
            description="Add a frame with a list of node IDs",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of node IDs to include in the frame"
                    },
                    "frame_name": {
                        "type": "string",
                        "description": "Optional name for the frame (auto-generated if not provided)"
                    }
                },
                "required": ["node_list"]
            }
        ),
        Tool(
            name="remove_node",
            description="Remove a node from the graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The ID of the node to remove"
                    }
                },
                "required": ["node_id"]
            }
        ),
        Tool(
            name="remove_edge",
            description="Remove an edge from the graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "edge_id": {
                        "type": "string",
                        "description": "The ID of the edge to remove"
                    }
                },
                "required": ["edge_id"]
            }
        ),
        Tool(
            name="remove_frame",
            description="Remove a frame from the graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "frame_id": {
                        "type": "string",
                        "description": "The ID of the frame to remove"
                    }
                },
                "required": ["frame_id"]
            }
        ),
        Tool(
            name="read_graph",
            description="Read and return the entire IR graph with all nodes, edges, and frames",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="read_frame_get_all",
            description="Get all available frame names in the graph",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="read_frame_get_elements",
            description="Get all elements (nodes) in a specific frame",
            inputSchema={
                "type": "object",
                "properties": {
                    "frame_name": {
                        "type": "string",
                        "description": "The name of the frame to read"
                    }
                },
                "required": ["frame_name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]):
    """Execute a tool."""
    try:
        if name == "set_board":
            return await set_board(arguments)
        elif name == "add_node":
            return await add_node(arguments)
        elif name == "add_edge":
            return await add_edge(arguments)
        elif name == "add_frame":
            return await add_frame(arguments)
        elif name == "remove_node":
            return await remove_node(arguments)
        elif name == "remove_edge":
            return await remove_edge(arguments)
        elif name == "remove_frame":
            return await remove_frame(arguments)
        elif name == "read_graph":
            return await read_graph(arguments)
        elif name == "read_frame_get_all":
            return await read_frame_get_all(arguments)
        elif name == "read_frame_get_elements":
            return await read_frame_get_elements(arguments)
        else:
            from mcp.types import TextContent, CallToolResult
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    except Exception as e:
        from mcp.types import TextContent, CallToolResult
        logger.error(f"Error calling tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )




async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Drauvye MCP server started on stdio")
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())

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
from graph.graph import add_nodes, add_edges, relax_frame, remove_nodes, remove_edges, set_frame
from read.read import read_graph, read_frame_get_all, read_frame_get_elements
from sync.excalidraw_sync import sync_ir_from_excalidraw

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
            description="Register the target .excalidraw diagram for this session. Call this first before any other board tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "excalidraw_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the target .excalidraw file"
                    }
                },
                "required": ["excalidraw_path"]
            }
        ),
        Tool(
            name="set_frame",
            description="Set the active frame before adding nodes and edges. Prefer the hex-prefixed frame id or alias returned by the read tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "frame_id": {
                        "type": "string",
                        "description": "Hex-prefixed frame id or alias from the read tools"
                    },
                    "frame_name": {
                        "type": "string",
                        "description": "Optional human-readable frame name; use frame_id when available"
                    }
                }
            }
        ),
        Tool(
            name="add_nodes",
            description="Add one or more nodes to the graph. Nodes are placed at the active frame center, or 0,0 if no frame is active.",
            inputSchema={
                "type": "object",
                "properties": {
                    "texts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Text values for the nodes to create"
                    }
                },
                "required": ["texts"]
            }
        ),
        Tool(
            name="add_edges",
            description="Add one or more edges between existing nodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "edges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {
                                    "type": "string",
                                    "description": "The ID or alias of the source node"
                                },
                                "to": {
                                    "type": "string",
                                    "description": "The ID or alias of the target node"
                                }
                            },
                            "required": ["from", "to"]
                        },
                        "description": "Edges to create"
                    }
                },
                "required": ["edges"]
            }
        ),
        Tool(
            name="remove_nodes",
            description="Remove one or more nodes from the graph, including connected edges and frame references",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Node IDs or aliases to remove"
                    }
                },
                "required": ["node_ids"]
            }
        ),
        Tool(
            name="remove_edges",
            description="Remove one or more edges from the graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "edge_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Edge IDs or aliases to remove"
                    }
                },
                "required": ["edge_ids"]
            }
        ),
        Tool(
            name="relax_frame",
            description="Relax a populated frame after adding a batch of nodes and edges. Use the hex-prefixed frame id or alias returned by the read tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "frame_id": {
                        "type": "string",
                        "description": "Hex-prefixed frame id or alias from the read tools"
                    },
                    "frame_name": {
                        "type": "string",
                        "description": "Optional human-readable frame name; prefer frame_id for reliable calls"
                    }
                }
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
        if name != "set_board":
            sync_ir_from_excalidraw()

        if name == "set_board":
            return await set_board(arguments)
        elif name == "set_frame":
            return await set_frame(arguments)
        elif name == "add_nodes":
            return await add_nodes(arguments)
        elif name == "add_edges":
            return await add_edges(arguments)
        elif name == "remove_nodes":
            return await remove_nodes(arguments)
        elif name == "remove_edges":
            return await remove_edges(arguments)
        elif name == "relax_frame":
            return await relax_frame(arguments)
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

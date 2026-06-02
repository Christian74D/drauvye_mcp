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
                        "description": "The name for the board (used to create <name>_drauvye_ir.json and <name>.excalidraw files)"
                    }
                },
                "required": ["folder_path", "name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]):
    """Execute a tool."""
    try:
        if name == "set_board":
            return await set_board(arguments)
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

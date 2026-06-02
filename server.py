#!/usr/bin/env python3
"""
Drauvye MCP Server - A Model Context Protocol server for managing Drauvye project boards.
"""

import os
import json
import sys
import logging
import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

# Set up logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("drauvye")

# Current configuration path storage
current_config = {
    "board_path": None,
    "board_name": None
}

# Default templates
EXCALIDRAW_TEMPLATE = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://marketplace.visualstudio.com/items?itemName=pomdtr.excalidraw-editor",
    "elements": [],
    "appState": {
        "gridSize": 20,
        "gridStep": 5,
        "gridModeEnabled": False,
        "viewBackgroundColor": "#ffffff"
    },
    "files": {}
}

IR_TEMPLATE = {}


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
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Execute a tool."""
    try:
        if name == "set_board":
            return await set_board_tool(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


async def set_board_tool(arguments: dict[str, Any]) -> CallToolResult:
    """
    Set up a Drauvye board in the specified folder.
    
    Creates:
    - .drauvye folder
    - <name>_drauvye_ir.json with default content
    - <name>.excalidraw with template content
    """
    folder_path = arguments.get("folder_path")
    name = arguments.get("name")
    
    if not folder_path:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: folder_path is required")],
            isError=True
        )
    
    if not name:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: name is required")],
            isError=True
        )
    
    try:
        # Convert to Path object and resolve
        base_path = Path(folder_path).resolve()
        
        # Check if base folder exists
        if not base_path.exists():
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Folder does not exist: {folder_path}")],
                isError=True
            )
        
        # Create .drauvye folder
        drauvye_folder = base_path / ".drauvye"
        drauvye_folder.mkdir(exist_ok=True)
        
        # Create IR file
        ir_filename = f"{name}_drauvye_ir.json"
        ir_path = drauvye_folder / ir_filename
        with open(ir_path, 'w') as f:
            json.dump(IR_TEMPLATE, f, indent=2)
        
        # Create Excalidraw file
        excalidraw_filename = f"{name}.excalidraw"
        excalidraw_path = drauvye_folder / excalidraw_filename
        with open(excalidraw_path, 'w') as f:
            json.dump(EXCALIDRAW_TEMPLATE, f, indent=2)
        
        # Update current config
        current_config["board_path"] = str(drauvye_folder)
        current_config["board_name"] = name
        
        # Create current.config file
        config_file = drauvye_folder / "current.config"
        with open(config_file, 'w') as f:
            json.dump(current_config, f, indent=2)
        
        result_message = f"""Board '{name}' created successfully!
        
Location: {drauvye_folder}
Files created:
- {ir_filename}
- {excalidraw_filename}
- current.config

Current config updated:
- board_path: {drauvye_folder}
- board_name: {name}"""
        
        logger.info(result_message)
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False
        )
    
    except Exception as e:
        logger.error(f"Error in set_board: {str(e)}")
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
    import asyncio
    asyncio.run(main())

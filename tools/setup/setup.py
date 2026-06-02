"""
Setup tools for Drauvye MCP Server
"""

import json
import logging
from pathlib import Path
from typing import Any

from mcp.types import TextContent, CallToolResult
from sync.excalidraw_sync import sync_excalidraw_from_ir

logger = logging.getLogger(__name__)


def load_templates():
    """Load templates from templates folder"""
    template_dir = Path(__file__).parent.parent.parent / "templates"

    with open(template_dir / "ir_template.json", "r") as f:
        ir_template = json.load(f)

    with open(template_dir / "excalidraw_template.json", "r") as f:
        excalidraw_template = json.load(f)

    return ir_template, excalidraw_template


def update_current_config(path: str, proj_name: str):
    """Update the current.config file with path and proj_name"""
    config_file = Path(__file__).parent.parent.parent / "current.config"

    config = {
        "path": path,
        "proj_name": proj_name,
    }

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    logger.info(f"Updated current.config: path={path}, proj_name={proj_name}")


async def set_board(arguments: dict[str, Any]) -> CallToolResult:
    """
    Set up a Drauvye board in the specified folder.

    Creates:
    - .drauvye folder
    - <name>_drauvye_ir.json with default content
    - <name>.excalidraw with template content
    - Updates current.config in drauvye_mcp folder
    """
    folder_path = arguments.get("folder_path")
    name = arguments.get("name")

    if not folder_path:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: folder_path is required")],
            isError=True,
        )

    if not name:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: name is required")],
            isError=True,
        )

    try:
        # Load templates
        ir_template, excalidraw_template = load_templates()

        # Convert to Path object and resolve
        base_path = Path(folder_path).resolve()

        # Check if base folder exists
        if not base_path.exists():
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Folder does not exist: {folder_path}")],
                isError=True,
            )

        # Create .drauvye folder
        drauvye_folder = base_path / ".drauvye"
        drauvye_folder.mkdir(exist_ok=True)

        # Create IR file
        ir_filename = f"{name}_drauvye_ir.json"
        ir_path = drauvye_folder / ir_filename
        with open(ir_path, "w") as f:
            json.dump(ir_template, f, indent=2)

        # Create Excalidraw file
        excalidraw_filename = f"{name}.excalidraw"
        excalidraw_path = drauvye_folder / excalidraw_filename
        with open(excalidraw_path, "w") as f:
            json.dump(excalidraw_template, f, indent=2)

        # Update current.config in drauvye_mcp folder
        update_current_config(str(drauvye_folder), name)

        # Regenerate the Excalidraw file from the IR so the source of truth stays aligned.
        sync_excalidraw_from_ir(ir_template)

        result_message = f"""Board '{name}' created successfully!

Location: {drauvye_folder}
Files created:
- {ir_filename}
- {excalidraw_filename}

Current config updated in drauvye_mcp/current.config:
- path: {drauvye_folder}
- proj_name: {name}"""

        logger.info(result_message)

        return CallToolResult(
            content=[TextContent(type="text", text=result_message)],
            isError=False,
        )

    except Exception as e:
        logger.error(f"Error in set_board: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )

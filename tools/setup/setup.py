"""
Setup tools for Drauvye MCP Server
"""

import json
import logging
from pathlib import Path
from typing import Any

from mcp.types import TextContent, CallToolResult
from sync.excalidraw_sync import get_board_paths, sync_ir_from_excalidraw

logger = logging.getLogger(__name__)


def update_current_config(excalidraw_path: str):
    """Update the current.config file with the active diagram path."""
    config_file = Path(__file__).parent.parent.parent / "current.config"

    config = {
        "excalidraw_path": excalidraw_path,
        "active_frame_id": None,
    }

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    logger.info("Updated current.config: excalidraw_path=%s", excalidraw_path)


async def set_board(arguments: dict[str, Any]) -> CallToolResult:
    """
    Register the target Excalidraw diagram for this MCP session.

    The diagram file must already exist. The IR snapshot is stored in the
    repo-local ir_graphs directory and the diagram remains the source of truth.
    """
    excalidraw_path_raw = arguments.get("excalidraw_path") or arguments.get("path") or arguments.get("folder_path")

    if not excalidraw_path_raw:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: excalidraw_path is required")],
            isError=True,
        )

    try:
        excalidraw_path = Path(excalidraw_path_raw).resolve()
        if excalidraw_path.suffix.lower() != ".excalidraw":
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: target diagram must be an .excalidraw file: {excalidraw_path_raw}")],
                isError=True,
            )

        if not excalidraw_path.exists():
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: target diagram does not exist: {excalidraw_path}")],
                isError=True,
            )

        update_current_config(str(excalidraw_path))
        ir_path, _ = get_board_paths()
        sync_ir_from_excalidraw()

        result_message = f"""Board registered successfully!

Target diagram: {excalidraw_path}
IR snapshot: {ir_path}
Config: drauvye_mcp/current.config

Call set_frame before adding nodes and edges."""

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

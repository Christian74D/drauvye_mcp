# Drauvye MCP Usage

Use the Drauvye MCP tools to create and update graph content on a board.

## Basic Workflow

1. Call `set_board` before working with a board.

Use `excalidraw_path` for the target `.excalidraw` file path. This should be the first call before any other board tool.

2. Call `read_frame_get_all` when you need to see available frames.

Frames are usually created or edited by the user in the drawing surface.

3. Call `set_frame` before adding graph content to a frame.

Use `frame_id` when you already have the frame ID or alias from the read tools. Prefer the hex-prefixed alias format to avoid mismatches.

4. Call `add_nodes` with all node labels for the graph.

Prefer one batch call with `texts` instead of many single-node calls.

5. Call `add_edges` after nodes exist.

Use node IDs or aliases returned by `add_nodes` or `read_graph`.

6. Call `relax_frame` after nodes and edges have been added.

Use the same hex-prefixed `frame_id` alias returned by the read tools. This arranges the frame contents into a readable layout.

7. Use `read_graph` or `read_frame_get_elements` to verify the result.

## Editing Existing Graphs

Use `remove_nodes` and `remove_edges` for cleanup. Prefer batch removals when removing multiple items.

Do not create, rename, resize, or remove frames unless the user explicitly asks through the drawing surface. Use frame read tools and `set_frame` to target existing frames.

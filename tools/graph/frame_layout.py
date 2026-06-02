"""
Utilities for laying out nodes inside a frame.
"""

from __future__ import annotations

import hashlib
import math
import random
from typing import Any


def measure_node(node: dict[str, Any]) -> tuple[float, float]:
    text = str(node.get("text", ""))
    lines = text.splitlines() or [""]
    longest = max(len(line) for line in lines)
    width = max(120.0, min(320.0, 28.0 + longest * 8.0))
    height = max(44.0, 24.0 + len(lines) * 22.0)
    return width, height


def _node_seed(node_id: str) -> int:
    return int(hashlib.sha1(node_id.encode("utf-8")).hexdigest()[:8], 16)


def _frame_seed(frame_id: str) -> int:
    return int(hashlib.sha1(frame_id.encode("utf-8")).hexdigest()[:8], 16)


def _node_center(node: dict[str, Any]) -> tuple[float, float]:
    width, height = measure_node(node)
    x = float(node.get("x", 0.0))
    y = float(node.get("y", 0.0))
    if "width" in node and "height" in node:
        width = float(node["width"])
        height = float(node["height"])
    return x + width / 2.0, y + height / 2.0


def _frame_box(frame: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, float]:
    if all(key in frame for key in ("x", "y", "width", "height")):
        return {
            "x": float(frame["x"]),
            "y": float(frame["y"]),
            "width": float(frame["width"]),
            "height": float(frame["height"]),
        }

    if not nodes:
        return {"x": 100.0, "y": 100.0, "width": 360.0, "height": 240.0}

    min_x = min(float(node.get("x", 0.0)) for node in nodes)
    min_y = min(float(node.get("y", 0.0)) for node in nodes)
    max_x = max(float(node.get("x", 0.0)) + measure_node(node)[0] for node in nodes)
    max_y = max(float(node.get("y", 0.0)) + measure_node(node)[1] for node in nodes)

    padding_x = 72.0
    padding_y = 88.0
    header_space = 32.0
    return {
        "x": min_x - padding_x,
        "y": min_y - padding_y - header_space,
        "width": (max_x - min_x) + padding_x * 2.0,
        "height": (max_y - min_y) + padding_y + header_space,
    }


def _starting_positions(
    frame: dict[str, Any],
    nodes: list[dict[str, Any]],
    bounds: dict[str, float],
) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    center_x = bounds["x"] + bounds["width"] / 2.0
    center_y = bounds["y"] + bounds["height"] / 2.0
    spread_x = max(60.0, bounds["width"] * 0.28)
    spread_y = max(48.0, bounds["height"] * 0.22)
    rng = random.Random(_frame_seed(frame["id"]))

    for index, node in enumerate(nodes):
        width, height = measure_node(node)
        if "x" in node and "y" in node:
            x = float(node["x"])
            y = float(node["y"])
        else:
            angle = (2.0 * math.pi * index) / max(1, len(nodes))
            radius_x = spread_x * (0.75 + rng.random() * 0.25)
            radius_y = spread_y * (0.75 + rng.random() * 0.25)
            x = center_x + math.cos(angle) * radius_x - width / 2.0
            y = center_y + math.sin(angle) * radius_y - height / 2.0
        positions[node["id"]] = (x, y)

    return positions


def _frame_padding(bounds: dict[str, float]) -> tuple[float, float, float, float]:
    left = bounds["x"] + 24.0
    top = bounds["y"] + 40.0
    right = bounds["x"] + bounds["width"] - 24.0
    bottom = bounds["y"] + bounds["height"] - 24.0
    return left, top, right, bottom


def _edge_pairs(edges: list[dict[str, Any]], node_ids: set[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for edge in edges:
        start = edge.get("from")
        end = edge.get("to")
        if start in node_ids and end in node_ids:
            pairs.append((start, end))
    return pairs


def relax_nodes_in_frame(
    frame: dict[str, Any],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    iterations: int = 220,
) -> tuple[dict[str, tuple[float, float]], dict[str, float]]:
    """
    Force-based relaxation for a single frame.

    Nodes are modeled as point masses with:
    - pairwise repulsion
    - spring attraction along edges
    - boundary repulsion from the frame edges
    """
    if not nodes:
        return {}, _frame_box(frame, nodes)

    bounds = _frame_box(frame, nodes)
    positions = _starting_positions(frame, nodes, bounds)
    velocities = {node["id"]: [0.0, 0.0] for node in nodes}
    sizes = {node["id"]: measure_node(node) for node in nodes}
    node_ids = {node["id"] for node in nodes}
    edge_pairs = _edge_pairs(edges, node_ids)
    center_x = bounds["x"] + bounds["width"] / 2.0
    center_y = bounds["y"] + bounds["height"] / 2.0

    # Tuned for stability over a small number of nodes.
    repulsion_k = 22000.0
    spring_k = 0.012
    rest_length = 150.0
    wall_k = 0.08
    center_k = 0.0015
    damping = 0.88
    max_step = 18.0

    for _ in range(iterations):
        forces = {node["id"]: [0.0, 0.0] for node in nodes}

        # Repel every node from every other node.
        for i, left in enumerate(nodes):
            left_id = left["id"]
            left_x, left_y = positions[left_id]
            left_w, left_h = sizes[left_id]
            left_cx = left_x + left_w / 2.0
            left_cy = left_y + left_h / 2.0
            for right in nodes[i + 1 :]:
                right_id = right["id"]
                right_x, right_y = positions[right_id]
                right_w, right_h = sizes[right_id]
                right_cx = right_x + right_w / 2.0
                right_cy = right_y + right_h / 2.0

                dx = right_cx - left_cx
                dy = right_cy - left_cy
                dist_sq = dx * dx + dy * dy
                if dist_sq < 1.0:
                    angle = (_node_seed(left_id) ^ _node_seed(right_id)) % 360
                    dx = math.cos(math.radians(angle))
                    dy = math.sin(math.radians(angle))
                    dist_sq = 1.0
                dist = math.sqrt(dist_sq)
                force = repulsion_k / dist_sq
                fx = force * dx / dist
                fy = force * dy / dist
                forces[left_id][0] -= fx
                forces[left_id][1] -= fy
                forces[right_id][0] += fx
                forces[right_id][1] += fy

        # Edge springs pull connected nodes together.
        for start_id, end_id in edge_pairs:
            start_x, start_y = positions[start_id]
            end_x, end_y = positions[end_id]
            start_w, start_h = sizes[start_id]
            end_w, end_h = sizes[end_id]
            start_cx = start_x + start_w / 2.0
            start_cy = start_y + start_h / 2.0
            end_cx = end_x + end_w / 2.0
            end_cy = end_y + end_h / 2.0

            dx = end_cx - start_cx
            dy = end_cy - start_cy
            dist = math.sqrt(dx * dx + dy * dy) or 1.0
            delta = dist - rest_length
            force = spring_k * delta
            fx = force * dx / dist
            fy = force * dy / dist
            forces[start_id][0] += fx
            forces[start_id][1] += fy
            forces[end_id][0] -= fx
            forces[end_id][1] -= fy

        # Frame walls repel nodes back inside.
        left_wall, top_wall, right_wall, bottom_wall = _frame_padding(bounds)
        for node in nodes:
            node_id = node["id"]
            x, y = positions[node_id]
            width, height = sizes[node_id]
            cx = x + width / 2.0
            cy = y + height / 2.0

            if x < left_wall:
                forces[node_id][0] += wall_k * (left_wall - x) ** 2
            if x + width > right_wall:
                forces[node_id][0] -= wall_k * (x + width - right_wall) ** 2
            if y < top_wall:
                forces[node_id][1] += wall_k * (top_wall - y) ** 2
            if y + height > bottom_wall:
                forces[node_id][1] -= wall_k * (y + height - bottom_wall) ** 2

            # Gentle pull toward the center keeps the cloud compact.
            forces[node_id][0] += center_k * (center_x - cx)
            forces[node_id][1] += center_k * (center_y - cy)

        # Integrate.
        for node in nodes:
            node_id = node["id"]
            vx, vy = velocities[node_id]
            fx, fy = forces[node_id]
            vx = (vx + fx) * damping
            vy = (vy + fy) * damping
            vx = max(-max_step, min(max_step, vx))
            vy = max(-max_step, min(max_step, vy))
            x, y = positions[node_id]
            positions[node_id] = (x + vx, y + vy)
            velocities[node_id] = [vx, vy]

        # Clamp after each step so nodes never leave the frame.
        left_wall, top_wall, right_wall, bottom_wall = _frame_padding(bounds)
        for node in nodes:
            node_id = node["id"]
            width, height = sizes[node_id]
            x, y = positions[node_id]
            x = max(left_wall, min(x, right_wall - width))
            y = max(top_wall, min(y, bottom_wall - height))
            positions[node_id] = (x, y)

    # Recompute the frame around the final layout with a little breathing room.
    min_x = min(positions[node["id"]][0] for node in nodes)
    min_y = min(positions[node["id"]][1] for node in nodes)
    max_x = max(positions[node["id"]][0] + sizes[node["id"]][0] for node in nodes)
    max_y = max(positions[node["id"]][1] + sizes[node["id"]][1] for node in nodes)

    final_bounds = {
        "x": min_x - 28.0,
        "y": min_y - 48.0,
        "width": (max_x - min_x) + 56.0,
        "height": (max_y - min_y) + 72.0,
    }

    # Normalize the settled layout into a positive canvas region so Excalidraw
    # opens it cleanly without leaving the cluster far off-screen.
    target_x = 120.0
    target_y = 120.0
    shift_x = target_x - final_bounds["x"] if final_bounds["x"] < target_x else 0.0
    shift_y = target_y - final_bounds["y"] if final_bounds["y"] < target_y else 0.0

    if shift_x or shift_y:
        final_bounds["x"] += shift_x
        final_bounds["y"] += shift_y
        positions = {
            node_id: (x + shift_x, y + shift_y)
            for node_id, (x, y) in positions.items()
        }

    # Ensure the frame still contains the nodes after the final bounds shift.
    final_left, final_top, final_right, final_bottom = _frame_padding(final_bounds)
    clamped_positions: dict[str, tuple[float, float]] = {}
    for node in nodes:
        node_id = node["id"]
        width, height = sizes[node_id]
        x, y = positions[node_id]
        x = max(final_left, min(x, final_right - width))
        y = max(final_top, min(y, final_bottom - height))
        clamped_positions[node_id] = (x, y)

    return clamped_positions, final_bounds

"""
Shared helpers for shortening IR identifiers into model-friendly aliases.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:6]


def node_alias(node: dict[str, Any]) -> str:
    text = str(node.get("text", "node"))
    return f"{_short_hash(node['id'])}_{_slugify(text)}"


def edge_alias(edge: dict[str, Any], node_aliases: dict[str, str]) -> str:
    from_alias = node_aliases.get(edge.get("from", ""), "unknown")
    to_alias = node_aliases.get(edge.get("to", ""), "unknown")
    return f"{_short_hash(edge['id'])}_{from_alias}_to_{to_alias}"


def frame_alias(frame: dict[str, Any]) -> str:
    name = str(frame.get("name", "frame"))
    return f"{_short_hash(frame['id'])}_{_slugify(name)}"


def build_alias_maps(ir_data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    node_alias_by_id = {node["id"]: node_alias(node) for node in ir_data.get("nodes", [])}
    edge_alias_by_id = {edge["id"]: edge_alias(edge, node_alias_by_id) for edge in ir_data.get("edges", [])}
    frame_alias_by_id = {frame["id"]: frame_alias(frame) for frame in ir_data.get("frames", [])}
    return node_alias_by_id, edge_alias_by_id, frame_alias_by_id


def build_lookup_maps(
    ir_data: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str], dict[str, str], dict[str, str]]:
    nodes_by_id = {node["id"]: node for node in ir_data.get("nodes", [])}
    edges_by_id = {edge["id"]: edge for edge in ir_data.get("edges", [])}
    frames_by_id = {frame["id"]: frame for frame in ir_data.get("frames", [])}
    node_alias_by_id, edge_alias_by_id, frame_alias_by_id = build_alias_maps(ir_data)
    return nodes_by_id, edges_by_id, frames_by_id, node_alias_by_id, edge_alias_by_id, frame_alias_by_id


def resolve_node_ref(ir_data: dict[str, Any], ref: str) -> str | None:
    nodes_by_id, _, _, node_alias_by_id, _, _ = build_lookup_maps(ir_data)
    if ref in nodes_by_id:
        return ref
    for node_id, alias in node_alias_by_id.items():
        if alias == ref:
            return node_id
    return None


def resolve_edge_ref(ir_data: dict[str, Any], ref: str) -> str | None:
    _, edges_by_id, _, _, edge_alias_by_id, _ = build_lookup_maps(ir_data)
    if ref in edges_by_id:
        return ref
    for edge_id, alias in edge_alias_by_id.items():
        if alias == ref:
            return edge_id
    return None


def resolve_frame_ref(ir_data: dict[str, Any], ref: str) -> str | None:
    _, _, frames_by_id, _, _, frame_alias_by_id = build_lookup_maps(ir_data)
    if ref in frames_by_id:
        return ref
    for frame_id, alias in frame_alias_by_id.items():
        if alias == ref:
            return frame_id
    return None


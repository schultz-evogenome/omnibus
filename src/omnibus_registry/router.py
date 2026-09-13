"""The router: one MCP server that reads ``registry.json``, picks the nodes
whose scope matches a query, fans the query out, merges the answers and
attaches each node's identity to every result.

This is the scaffold: scope matching and fan-out to nodes that expose a
``search_text`` (omnibus-node) or ``get_chunks_for_topic`` (corpus) tool.
Rank merging is reciprocal rank fusion over the per-node orderings, so
scores from different backends are never compared directly.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from .registry import read


def _tokens(text: str) -> list[str]:
    return [w for w in "".join(c if c.isalnum() else " " for c in text.lower()).split() if len(w) > 3]


def _same_stem(a: str, b: str) -> bool:
    """``ctenophore`` and ``ctenophora``, ``chromosome`` and ``chromosomes``:
    equal, or sharing their first five letters."""
    return a == b or (len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5])


def match_scope(node: dict, query: str) -> bool:
    words = _tokens(query)
    for term in node.get("scope", []):
        if term.lower() in query.lower():
            return True
        if any(_same_stem(w, t) for w in words for t in _tokens(term)):
            return True
    return False


def candidates(registry: dict, query: str, include_stale: bool = False) -> list[dict]:
    out = []
    for node in registry.get("nodes", []):
        if node.get("status") == "planned" or not node.get("endpoint"):
            continue
        if node.get("status") == "stale" and not include_stale:
            continue
        if match_scope(node, query):
            out.append(node)
    return out


async def _query_node(node: dict, query: str, k: int, token: str | None) -> list[dict]:
    from .checks import open_client, text_payload, tool_names

    async with open_client(node["endpoint"], node.get("transport") or "streamable-http", token) as client:
        tools = set(tool_names(await client.list_tools()))
        if "search_text" in tools:
            result = await client.call_tool("search_text", {"query": query, "k": k})
        elif "get_chunks_for_topic" in tools:
            result = await client.call_tool("get_chunks_for_topic", {"query": query, "k": k})
        else:
            return []
        hits = text_payload(result)
        if hits is None:
            return []
        if isinstance(hits, str):
            return [{"snippet": hits[:400]}]
        if isinstance(hits, dict):
            hits = hits.get("results") or hits.get("chunks") or hits.get("hits") or []
        return hits if isinstance(hits, list) else []


def fuse(per_node: dict[str, list[dict]], k: int = 10, c: int = 60) -> list[dict]:
    """Reciprocal rank fusion: score = sum over nodes of 1/(c + rank)."""
    scored: dict[str, float] = defaultdict(float)
    items: dict[str, dict] = {}
    for node_name, hits in per_node.items():
        for rank, hit in enumerate(hits, start=1):
            ident = f"{node_name}:{hit.get('key') or hit.get('paper_hash') or ''}:{hit.get('paragraph', hit.get('chunk_id', rank))}"
            scored[ident] += 1.0 / (c + rank)
            if ident not in items:
                items[ident] = {"node": node_name, **hit}
    ordered = sorted(scored.items(), key=lambda kv: kv[1], reverse=True)[:k]
    return [{**items[i], "fused_score": round(s, 5)} for i, s in ordered]


def route(registry_path: str, query: str, k: int = 10, token: str | None = None, dry_run: bool = False) -> dict:
    registry = read(registry_path)
    nodes = candidates(registry, query)
    result: dict = {"query": query, "candidates": [n["name"] for n in nodes], "results": []}
    if dry_run or not nodes:
        return result

    async def gather() -> dict[str, list[dict]]:
        per: dict[str, list[dict]] = {}
        for node in nodes:
            try:
                per[node["name"]] = await asyncio.wait_for(_query_node(node, query, k, token), 60)
            except Exception as exc:  # noqa: BLE001 - a dead node is a result, not a crash
                per[node["name"]] = []
                result.setdefault("errors", []).append({"node": node["name"], "error": f"{type(exc).__name__}: {str(exc)[:120]}"})
        return per

    per_node = asyncio.run(gather())
    by_name = {n["name"]: n for n in nodes}
    for hit in fuse(per_node, k):
        node = by_name.get(hit["node"], {})
        hit["node_maintainer"] = node.get("maintainer")
        hit["node_bundle_doi"] = node.get("bundle_doi")
        result["results"].append(hit)
    return result

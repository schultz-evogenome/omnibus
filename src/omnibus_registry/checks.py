"""What the registry verifies about a node beyond its manifest's shape:
the ORCID and DOI resolve, and the endpoint answers as an MCP server.

Each check returns a dict with ``ok`` and a one-line ``detail``. Network
failures are reported, not raised, so a pull-request check can print every
result at once.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlsplit

import requests

from . import __version__
from .manifest import Manifest

UA = f"omnibus-registry/{__version__} (+https://github.com/schultz-evogenome/omnibus)"
TIMEOUT = 30


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def check_orcid(orcid: str, session: requests.Session | None = None) -> dict:
    session = session or _session()
    try:
        r = session.get(f"https://pub.orcid.org/v3.0/{orcid}/person", timeout=TIMEOUT)
    except requests.RequestException as exc:
        return {"check": "orcid", "ok": False, "detail": f"request failed: {type(exc).__name__}"}
    if r.status_code != 200:
        return {"check": "orcid", "ok": False, "detail": f"HTTP {r.status_code} from pub.orcid.org"}
    try:
        name = r.json().get("name") or {}
        given = (name.get("given-names") or {}).get("value", "")
        family = (name.get("family-name") or {}).get("value", "")
    except ValueError:
        return {"check": "orcid", "ok": False, "detail": "unreadable response from pub.orcid.org"}
    return {"check": "orcid", "ok": True, "detail": f"{given} {family}".strip() or "resolves"}


def check_doi(doi: str, session: requests.Session | None = None) -> dict:
    session = session or _session()
    try:
        r = session.get(f"https://doi.org/api/handles/{doi}", timeout=TIMEOUT)
    except requests.RequestException as exc:
        return {"check": "doi", "ok": False, "detail": f"request failed: {type(exc).__name__}"}
    if r.status_code != 200:
        return {"check": "doi", "ok": False, "detail": f"HTTP {r.status_code} from doi.org"}
    try:
        data = r.json()
    except ValueError:
        return {"check": "doi", "ok": False, "detail": "unreadable response from doi.org"}
    if data.get("responseCode") != 1:
        return {"check": "doi", "ok": False, "detail": f"handle responseCode {data.get('responseCode')}"}
    urls = [v["data"]["value"] for v in data.get("values", []) if v.get("type") == "URL"]
    return {"check": "doi", "ok": True, "detail": urls[0] if urls else "resolves"}


def check_server_card(endpoint: str, session: requests.Session | None = None) -> dict:
    """The draft MCP Server Card at /.well-known/mcp.json (SEP-2127). Optional."""
    session = session or _session()
    parts = urlsplit(endpoint)
    url = f"{parts.scheme}://{parts.netloc}/.well-known/mcp.json"
    try:
        r = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return {"check": "server-card", "ok": False, "optional": True, "detail": f"request failed: {type(exc).__name__}"}
    if r.status_code != 200:
        return {"check": "server-card", "ok": False, "optional": True, "detail": f"HTTP {r.status_code} for {url}"}
    try:
        card = r.json()
    except ValueError:
        return {"check": "server-card", "ok": False, "optional": True, "detail": "not JSON"}
    return {"check": "server-card", "ok": True, "optional": True, "detail": json.dumps(card)[:200]}


def open_client(endpoint: str, transport: str, token: str | None):
    """An ``mcp.Client`` for a node. A URL string means Streamable HTTP; SSE
    and bearer tokens go through the transport classes."""
    from mcp import Client

    headers = {"Authorization": f"Bearer {token}"} if token else None
    if transport == "sse":
        from mcp.client.sse import sse_client

        return Client(sse_client(endpoint, headers=headers))
    if headers:
        from mcp.client.streamable_http import StreamableHTTPTransport

        return Client(StreamableHTTPTransport(endpoint, headers=headers))
    return Client(endpoint)


def tool_names(listed) -> list[str]:
    tools = getattr(listed, "tools", listed)
    return [t.name for t in tools]


def text_payload(result) -> dict | list | str | None:
    content = getattr(result, "content", result)
    texts = [c.text for c in content if getattr(c, "type", None) == "text"]
    if not texts:
        return None
    try:
        return json.loads(texts[0])
    except ValueError:
        return texts[0]


async def _probe_mcp(endpoint: str, transport: str, token: str | None) -> dict:
    async with open_client(endpoint, transport, token) as client:
        names = tool_names(await client.list_tools())
        info: dict = {}
        for probe in ("bundle_info", "node_info"):
            if probe in names:
                payload = text_payload(await client.call_tool(probe, {}))
                info = payload if isinstance(payload, dict) else {"raw": str(payload)[:300]}
                info["_tool"] = probe
                break
        return {"tools": len(names), "info": info}


def check_endpoint(manifest: Manifest, token: str | None = None) -> dict:
    if manifest.endpoint is None:
        return {"check": "endpoint", "ok": True, "detail": "no endpoint (planned node)"}
    try:
        result = asyncio.run(asyncio.wait_for(_probe_mcp(str(manifest.endpoint), manifest.transport or "streamable-http", token), TIMEOUT * 2))
    except Exception as exc:  # noqa: BLE001 - every failure mode is a finding here
        return {"check": "endpoint", "ok": False, "detail": f"{type(exc).__name__}: {str(exc)[:160]}"}
    info = result.get("info") or {}
    detail = f"reachable, tools={result.get('tools')}"
    if info:
        detail += f" {info.get('_tool')}={{" + ", ".join(f"{k}={v}" for k, v in info.items() if k != "_tool" and not isinstance(v, (dict, list)))[:200] + "}"
    return {"check": "endpoint", "ok": True, "detail": detail, "info": info}


def check_all(manifest: Manifest, token: str | None = None, session: requests.Session | None = None) -> list[dict]:
    session = session or _session()
    results = [check_orcid(manifest.maintainer, session)]
    if manifest.bundle_doi:
        results.append(check_doi(manifest.bundle_doi, session))
    results.append(check_endpoint(manifest, token))
    if manifest.endpoint is not None:
        results.append(check_server_card(str(manifest.endpoint), session))
    return results

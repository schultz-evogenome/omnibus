"""``registry.json``: every manifest under ``nodes/``, validated, with the
status the nightly check assigns. This is what the router reads."""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import __version__
from .manifest import Manifest, load


def load_all(nodes_dir: str | Path) -> tuple[list[Manifest], list[tuple[Path, str]]]:
    manifests: list[Manifest] = []
    errors: list[tuple[Path, str]] = []
    for path in sorted(Path(nodes_dir).glob("*.yaml")) + sorted(Path(nodes_dir).glob("*.yml")):
        try:
            m = load(path)
        except Exception as exc:  # noqa: BLE001 - collect every problem
            errors.append((path, str(exc).splitlines()[0] if str(exc) else type(exc).__name__))
            continue
        if path.stem != m.name:
            errors.append((path, f"file is {path.name} but name is {m.name}; they must match"))
            continue
        manifests.append(m)
    names = [m.name for m in manifests]
    for n in sorted({n for n in names if names.count(n) > 1}):
        errors.append((Path(nodes_dir) / f"{n}.yaml", f"duplicate node name {n}"))
    return manifests, errors


def build(nodes_dir: str | Path, previous: dict | None = None, statuses: dict[str, str] | None = None) -> dict:
    """The registry document. ``statuses`` (name -> planned/active/stale) come
    from the nightly check; otherwise the manifest's own status is kept."""
    manifests, errors = load_all(nodes_dir)
    if errors:
        raise ValueError("; ".join(f"{p.name}: {e}" for p, e in errors))
    prev_nodes = {n["name"]: n for n in (previous or {}).get("nodes", [])}
    nodes = []
    for m in manifests:
        node = json.loads(m.model_dump_json(exclude_none=True))
        if statuses and m.name in statuses:
            node["status"] = statuses[m.name]
        old = prev_nodes.get(m.name, {})
        if "first_registered" in old:
            node["first_registered"] = old["first_registered"]
        else:
            node["first_registered"] = _dt.date.today().isoformat()
        if "last_checked" in old and not (statuses and m.name in statuses):
            node["last_checked"] = old["last_checked"]
        elif statuses and m.name in statuses:
            node["last_checked"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        nodes.append(node)
    return {
        "schema": "https://raw.githubusercontent.com/schultz-evogenome/omnibus/main/schema/node.schema.json",
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": f"omnibus-registry {__version__}",
        "nodes": sorted(nodes, key=lambda n: n["name"]),
    }


def write(doc: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"nodes": []}
    return json.loads(p.read_text(encoding="utf-8"))

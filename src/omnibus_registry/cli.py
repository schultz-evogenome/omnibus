"""The ``omnibus`` command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, manifest as manifest_mod, registry as registry_mod

COMMONS_LICENSES = ("CC-BY-4.0", "CC0-1.0")


def cmd_validate(a: argparse.Namespace) -> int:
    bad = 0
    for p in a.paths:
        try:
            m = manifest_mod.load(p)
        except Exception as exc:  # noqa: BLE001
            print(f"invalid  {p}: {str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__}")
            for line in str(exc).splitlines()[1:8]:
                if line.strip():
                    print(f"           {line.strip()}")
            bad += 1
            continue
        if Path(p).stem != m.name:
            print(f"invalid  {p}: file name must be {m.name}.yaml")
            bad += 1
            continue
        print(f"valid    {p}: {m.name} ({m.status}, {len(m.scope)} scope terms, {len(m.serves)} kinds served)")
    return 1 if bad else 0


def cmd_schema(a: argparse.Namespace) -> int:
    text = json.dumps(manifest_mod.json_schema(), indent=2) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text, end="")
    return 0


def cmd_check_node(a: argparse.Namespace) -> int:
    from .checks import check_all

    m = manifest_mod.load(a.path)
    results = check_all(m, token=a.token)
    failed = 0
    for r in results:
        mark = "ok  " if r["ok"] else ("warn" if r.get("optional") else "FAIL")
        print(f"{mark} {r['check']:<12} {r['detail']}")
        if not r["ok"] and not r.get("optional"):
            failed += 1
    if a.json:
        print(json.dumps(results, indent=2))
    return 1 if failed else 0


def cmd_registry_build(a: argparse.Namespace) -> int:
    previous = registry_mod.read(a.out)
    statuses: dict[str, str] | None = None
    if a.check:
        from .checks import check_endpoint

        statuses = {}
        manifests, errors = registry_mod.load_all(a.nodes)
        if errors:
            for p, e in errors:
                print(f"invalid  {p.name}: {e}")
            return 1
        for m in manifests:
            if m.endpoint is None:
                statuses[m.name] = "planned"
                continue
            r = check_endpoint(m, token=a.token)
            statuses[m.name] = "active" if r["ok"] else "stale"
            print(f"{'active' if r['ok'] else 'stale '} {m.name:<24} {r['detail']}")
    try:
        doc = registry_mod.build(a.nodes, previous=previous, statuses=statuses)
    except ValueError as exc:
        print(f"invalid: {exc}")
        return 1
    registry_mod.write(doc, a.out)
    print(f"wrote {a.out}: {len(doc['nodes'])} node(s)")
    return 0


def cmd_route(a: argparse.Namespace) -> int:
    from .router import route

    result = route(a.registry, a.query, k=a.k, token=a.token, dry_run=a.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_commons_check(a: argparse.Namespace) -> int:
    """Every commons entry needs front matter with a title, authors, date and an open license."""
    import yaml

    bad = 0
    paths = [Path(p) for p in a.paths] or sorted(Path("commons").rglob("*.md"))
    for p in paths:
        if p.name.upper() == "README.MD":
            continue
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            print(f"invalid  {p}: no front matter")
            bad += 1
            continue
        end = text.find("\n---\n", 4)
        try:
            front = yaml.safe_load(text[4:end]) or {}
        except yaml.YAMLError as exc:
            print(f"invalid  {p}: front matter is not YAML ({exc})")
            bad += 1
            continue
        problems = []
        for key in ("title", "authors", "date", "license", "node"):
            if not front.get(key):
                problems.append(f"missing {key}")
        if front.get("license") and front["license"] not in COMMONS_LICENSES:
            problems.append(f"license must be one of {', '.join(COMMONS_LICENSES)}")
        authors = front.get("authors") or []
        if isinstance(authors, list) and not any(isinstance(x, dict) and x.get("orcid") for x in authors):
            problems.append("at least one author needs an orcid")
        if problems:
            print(f"invalid  {p}: {'; '.join(problems)}")
            bad += 1
        else:
            print(f"valid    {p}: {front['title']} ({front['license']})")
    return 1 if bad else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="omnibus", description="The Omnibus registry of lab knowledge servers.")
    p.add_argument("--version", action="version", version=f"omnibus-registry {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="validate node manifests against the schema")
    s.add_argument("paths", nargs="+")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("schema", help="print or write the JSON schema generated from the manifest model")
    s.add_argument("--out")
    s.set_defaults(func=cmd_schema)

    s = sub.add_parser("check-node", help="resolve the maintainer ORCID and bundle DOI, probe the endpoint")
    s.add_argument("path")
    s.add_argument("--token", help="bearer token for a token-authenticated endpoint")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_check_node)

    r = sub.add_parser("registry", help="registry.json operations")
    rs = r.add_subparsers(dest="registry_cmd", required=True)
    s = rs.add_parser("build", help="write registry.json from nodes/")
    s.add_argument("--nodes", default="nodes")
    s.add_argument("--out", default="registry.json")
    s.add_argument("--check", action="store_true", help="probe every endpoint and set active/stale")
    s.add_argument("--token")
    s.set_defaults(func=cmd_registry_build)

    s = sub.add_parser("route", help="fan a query out to the nodes whose scope matches")
    s.add_argument("query")
    s.add_argument("--registry", default="registry.json")
    s.add_argument("-k", type=int, default=10)
    s.add_argument("--token")
    s.add_argument("--dry-run", action="store_true", help="only list the candidate nodes")
    s.set_defaults(func=cmd_route)

    s = sub.add_parser("commons-check", help="validate the front matter and license of commons/ entries")
    s.add_argument("paths", nargs="*")
    s.set_defaults(func=cmd_commons_check)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

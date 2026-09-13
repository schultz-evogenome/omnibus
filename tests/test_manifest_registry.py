import datetime as dt
import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibus_registry import registry
from omnibus_registry.cli import main
from omnibus_registry.manifest import Manifest, json_schema, load, orcid_checksum_ok
from omnibus_registry.router import candidates, fuse, match_scope

GOOD = {
    "name": "test-lab",
    "maintainer": "0000-0002-1825-0097",
    "organization": "Test Lab",
    "endpoint": None,
    "transport": None,
    "auth": "public",
    "server": "omnibus-node",
    "scope": ["Ctenophora", "chromosome evolution"],
    "serves": ["open-access-papers", "figures"],
    "license_default": "CC-BY-4.0",
    "bundle_doi": None,
    "status": "planned",
    "last_verified": dt.date.today().isoformat(),
}


def test_orcid_checksum():
    assert orcid_checksum_ok("0000-0002-1825-0097")
    assert orcid_checksum_ok("0000-0003-1190-1122")
    assert not orcid_checksum_ok("0000-0002-1825-0098")


def test_valid_manifest():
    m = Manifest.model_validate(GOOD)
    assert m.name == "test-lab" and m.status == "planned" and m.endpoint is None


@pytest.mark.parametrize(
    "change, message",
    [
        ({"name": "Test Lab"}, "lowercase"),
        ({"maintainer": "0000-0002-1825-0098"}, "checksum"),
        ({"endpoint": "https://x.example/mcp"}, "transport"),
        ({"endpoint": "https://x.example/mcp", "transport": "sse"}, "planned"),
        ({"status": "active"}, "needs an endpoint"),
        ({"scope": []}, "scope"),
        ({"serves": ["everything"]}, "serves"),
        ({"license_default": "GPL"}, "license_default"),
        ({"bundle_doi": "zenodo.123"}, "bare DOI"),
        ({"last_verified": (dt.date.today() + dt.timedelta(days=30)).isoformat()}, "future"),
        ({"extra_field": 1}, "extra"),
        ({"scope": ["Ctenophora", "ctenophora"]}, "duplicate"),
    ],
)
def test_invalid_manifests(change, message):
    data = {**GOOD, **change}
    with pytest.raises(ValidationError) as exc:
        Manifest.model_validate(data)
    assert message.lower() in str(exc.value).lower()


def test_active_manifest_with_endpoint():
    m = Manifest.model_validate({**GOOD, "endpoint": "https://x.example/mcp", "transport": "streamable-http", "status": "active"})
    assert str(m.endpoint).startswith("https://")


def test_schema_has_required_fields():
    schema = json_schema()
    assert schema["title"] == "Omnibus node manifest"
    assert {"name", "maintainer", "license_default", "last_verified"} <= set(schema["required"])


def test_registry_build_and_previous(tmp_path):
    nodes = tmp_path / "nodes"
    nodes.mkdir()
    (nodes / "test-lab.yaml").write_text(yaml.safe_dump(GOOD))
    (nodes / "other-lab.yaml").write_text(yaml.safe_dump({**GOOD, "name": "other-lab", "scope": ["Porifera"]}))
    doc = registry.build(nodes)
    assert [n["name"] for n in doc["nodes"]] == ["other-lab", "test-lab"]
    assert all(n["first_registered"] for n in doc["nodes"])
    doc["nodes"][1]["first_registered"] = "2020-01-01"
    doc2 = registry.build(nodes, previous=doc, statuses={"test-lab": "planned"})
    assert doc2["nodes"][1]["first_registered"] == "2020-01-01"
    assert doc2["nodes"][1]["last_checked"]
    (nodes / "wrong-name.yaml").write_text(yaml.safe_dump(GOOD))
    manifests, errors = registry.load_all(nodes)
    assert len(manifests) == 2 and any("must match" in e for _, e in errors)
    with pytest.raises(ValueError):
        registry.build(nodes)


def test_router_matching_and_fusion():
    reg = {
        "nodes": [
            {"name": "a", "status": "active", "endpoint": "https://a/mcp", "scope": ["Ctenophora", "macrosynteny"]},
            {"name": "b", "status": "stale", "endpoint": "https://b/mcp", "scope": ["Ctenophora"]},
            {"name": "c", "status": "planned", "endpoint": None, "scope": ["Ctenophora"]},
            {"name": "d", "status": "active", "endpoint": "https://d/mcp", "scope": ["Drosophila"]},
        ]
    }
    assert match_scope(reg["nodes"][0], "ctenophore chromosome macrosynteny")
    assert not match_scope(reg["nodes"][3], "ctenophore chromosomes")
    assert [n["name"] for n in candidates(reg, "ctenophore macrosynteny")] == ["a"]
    assert [n["name"] for n in candidates(reg, "ctenophore macrosynteny", include_stale=True)] == ["a", "b"]
    fused = fuse({"a": [{"key": "X", "paragraph": 1}, {"key": "Y", "paragraph": 2}], "b": [{"key": "Y", "paragraph": 2}]}, k=5)
    assert fused[0]["node"] in ("a", "b") and fused[0]["fused_score"] >= fused[1]["fused_score"]
    assert len(fused) == 3


def test_cli(tmp_path, capsys):
    nodes = tmp_path / "nodes"
    nodes.mkdir()
    good = nodes / "test-lab.yaml"
    good.write_text(yaml.safe_dump(GOOD))
    bad = nodes / "bad-lab.yaml"
    bad.write_text(yaml.safe_dump({**GOOD, "name": "bad-lab", "maintainer": "nope"}))
    assert main(["validate", str(good)]) == 0
    assert main(["validate", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "valid    " in out and "invalid  " in out and "ORCID" in out
    bad.unlink()
    assert main(["registry", "build", "--nodes", str(nodes), "--out", str(tmp_path / "registry.json")]) == 0
    reg = json.loads((tmp_path / "registry.json").read_text())
    assert reg["nodes"][0]["name"] == "test-lab"
    capsys.readouterr()
    assert main(["route", "ctenophores", "--registry", str(tmp_path / "registry.json"), "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["candidates"] == []  # planned nodes are not routed to
    assert main(["schema", "--out", str(tmp_path / "s.json")]) == 0
    assert json.loads((tmp_path / "s.json").read_text())["title"] == "Omnibus node manifest"

    commons = tmp_path / "entry.md"
    commons.write_text("---\ntitle: T\nauthors:\n  - name: A\n    orcid: 0000-0002-1825-0097\ndate: 2026-01-01\nlicense: CC-BY-4.0\nnode: test-lab\n---\n\nText.\n")
    assert main(["commons-check", str(commons)]) == 0
    commons.write_text("---\ntitle: T\nauthors:\n  - name: A\ndate: 2026-01-01\nlicense: GPL-3.0\nnode: test-lab\n---\n\nText.\n")
    assert main(["commons-check", str(commons)]) == 1
    out = capsys.readouterr().out
    assert "license must be" in out and "orcid" in out


def test_repository_manifest_and_commons_are_valid():
    root = Path(__file__).resolve().parent.parent
    for p in sorted((root / "nodes").glob("*.yaml")):
        m = load(p)
        assert m.name == p.stem
    assert main(["commons-check", *[str(p) for p in (root / "commons").rglob("*.md") if p.name != "README.md"]]) == 0


def test_committed_schema_is_current():
    root = Path(__file__).resolve().parent.parent
    committed = json.loads((root / "schema" / "node.schema.json").read_text())
    assert committed == json_schema()

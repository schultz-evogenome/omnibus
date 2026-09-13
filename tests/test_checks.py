from omnibus_registry import checks
from omnibus_registry.manifest import Manifest


class _Resp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data

    def json(self):
        if self._data is None:
            raise ValueError("no json")
        return self._data


class _Session:
    def __init__(self, routes):
        self.routes = routes
        self.headers = {}

    def get(self, url, **kw):
        for prefix, resp in self.routes.items():
            if url.startswith(prefix):
                return resp
        return _Resp(404)


def test_orcid_and_doi_checks():
    session = _Session(
        {
            "https://pub.orcid.org/v3.0/0000-0002-1825-0097": _Resp(200, {"name": {"given-names": {"value": "Josiah"}, "family-name": {"value": "Carberry"}}}),
            "https://doi.org/api/handles/10.5281/zenodo.1": _Resp(200, {"responseCode": 1, "values": [{"type": "URL", "data": {"value": "https://zenodo.org/1"}}]}),
            "https://doi.org/api/handles/10.5281/zenodo.404": _Resp(404),
        }
    )
    assert checks.check_orcid("0000-0002-1825-0097", session) == {"check": "orcid", "ok": True, "detail": "Josiah Carberry"}
    assert not checks.check_orcid("0000-0002-1825-0098", session)["ok"]
    assert checks.check_doi("10.5281/zenodo.1", session)["detail"] == "https://zenodo.org/1"
    assert "HTTP 404" in checks.check_doi("10.5281/zenodo.404", session)["detail"]


def test_planned_node_endpoint_check_passes():
    m = Manifest.model_validate(
        {
            "name": "x-lab",
            "maintainer": "0000-0002-1825-0097",
            "scope": ["Porifera"],
            "serves": ["notes"],
            "license_default": "CC0-1.0",
            "last_verified": "2026-01-01",
        }
    )
    r = checks.check_endpoint(m)
    assert r["ok"] and "planned" in r["detail"]


def test_unreachable_endpoint_is_a_finding():
    m = Manifest.model_validate(
        {
            "name": "x-lab",
            "maintainer": "0000-0002-1825-0097",
            "endpoint": "https://127.0.0.1:9/mcp",
            "transport": "streamable-http",
            "status": "active",
            "scope": ["Porifera"],
            "serves": ["notes"],
            "license_default": "CC0-1.0",
            "last_verified": "2026-01-01",
        }
    )
    r = checks.check_endpoint(m)
    assert not r["ok"] and r["check"] == "endpoint"

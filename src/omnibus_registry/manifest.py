"""The node manifest: one YAML file per node under ``nodes/``.

The model is the single definition; ``schema/node.schema.json`` is generated
from it (``omnibus schema``) so that tools in other languages can validate
the same thing.
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

SERVES = (
    "accepted-manuscripts",
    "preprints",
    "open-access-papers",
    "theses",
    "protocols",
    "pipelines",
    "negative-results",
    "notes",
    "figures",
    "figure-assets",
    "code",
    "data",
    "taxonomy",
)
LICENSES = ("CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "MIT", "Apache-2.0", "mixed")
SERVERS = ("corpus", "omnibus-node", "other")


def orcid_checksum_ok(orcid: str) -> bool:
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    remainder = total % 11
    check = (12 - remainder) % 11
    expected = "X" if check == 10 else str(check)
    return digits[-1] == expected


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Registry name: lowercase letters, digits, hyphens. Unique.")
    maintainer: str = Field(description="ORCID of the person answering for this node.")
    maintainer_name: Optional[str] = None
    organization: Optional[str] = Field(default=None, description="Lab and institution.")
    homepage: Optional[HttpUrl] = None
    endpoint: Optional[HttpUrl] = Field(default=None, description="The MCP endpoint. Null while the node is planned.")
    transport: Optional[Literal["streamable-http", "sse"]] = None
    auth: Literal["public", "token"] = "public"
    server: Literal[SERVERS] = "omnibus-node"  # type: ignore[valid-type]
    scope: list[str] = Field(default_factory=list, description="Taxa, topics, methods the node covers.")
    serves: list[Literal[SERVES]] = Field(default_factory=list)  # type: ignore[valid-type]
    license_default: Literal[LICENSES]  # type: ignore[valid-type]
    bundle_doi: Optional[str] = Field(default=None, description="Zenodo DOI of the archived bundle, so the node can be re-hosted.")
    repository: Optional[HttpUrl] = Field(default=None, description="Public repository of the served view, when there is one.")
    status: Literal["planned", "active", "stale"] = "planned"
    last_verified: _dt.date

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not NAME_RE.match(v):
            raise ValueError("name must be lowercase letters, digits and hyphens, 2 to 63 characters")
        return v

    @field_validator("maintainer")
    @classmethod
    def _orcid(cls, v: str) -> str:
        if not ORCID_RE.match(v):
            raise ValueError("maintainer must be an ORCID like 0000-0002-1825-0097")
        if not orcid_checksum_ok(v):
            raise ValueError("ORCID checksum does not match; check the digits")
        return v

    @field_validator("bundle_doi")
    @classmethod
    def _doi(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.replace("https://doi.org/", "")
        if not DOI_RE.match(v):
            raise ValueError("bundle_doi must be a bare DOI like 10.5281/zenodo.1234567")
        return v

    @field_validator("scope")
    @classmethod
    def _scope(cls, v: list[str]) -> list[str]:
        cleaned = [" ".join(s.split()) for s in v if s and s.strip()]
        if len(set(x.lower() for x in cleaned)) != len(cleaned):
            raise ValueError("scope has duplicate terms")
        return cleaned

    @field_validator("last_verified")
    @classmethod
    def _date(cls, v: _dt.date) -> _dt.date:
        if v > _dt.date.today() + _dt.timedelta(days=1):
            raise ValueError("last_verified is in the future")
        return v

    @model_validator(mode="after")
    def _endpoint_rules(self) -> "Manifest":
        if self.endpoint is not None:
            if str(self.endpoint).startswith("http://") and "localhost" not in str(self.endpoint):
                raise ValueError("endpoint must be https")
            if self.transport is None:
                raise ValueError("transport is required when endpoint is set")
            if self.status == "planned":
                raise ValueError("status cannot be planned when an endpoint is set; use active")
        else:
            if self.status == "active":
                raise ValueError("status active needs an endpoint")
        if not self.scope:
            raise ValueError("scope must name at least one taxon, topic or method")
        if not self.serves:
            raise ValueError("serves must list at least one kind of content")
        return self


def load(path: str | Path) -> Manifest:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a mapping")
    return Manifest.model_validate(data)


def json_schema() -> dict:
    schema = Manifest.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://raw.githubusercontent.com/schultz-evogenome/omnibus/main/schema/node.schema.json"
    schema["title"] = "Omnibus node manifest"
    return schema

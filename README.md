# Omnibus

A community registry of lab knowledge servers.

Each lab runs a node: a server that exposes what the lab has done, how it
does things, and what it is working on, over the Model Context Protocol
(MCP), the standard that Claude Code, Claude Desktop and other clients use to
reach external data. Omnibus is the one repository where labs register their
nodes by pull request, the checks that keep the registry honest, and a router
that lets an agent query every registered node at once and get answers with
a DOI or stable identifier on every result.

The model is bioconda: one repository, a small manifest per entry, a check
on every pull request, a core team that merges. The name is Latin for "for
all"; an omnibus volume collects works by many authors.

Two things make it hold. Every lab runs its node for its own benefit, and
sharing is a flag in a config file. And every node serves only what its lab
holds rights to: accepted manuscripts, preprints, open-access papers,
protocols, code, negative results. Nothing on the network is anyone else's to
take down.

## Joining

1. Run a node. The reference implementations are
   [corpus](https://github.com/caseywdunn/corpus) for a literature corpuscle
   and [omnibus-node](https://github.com/schultz-evogenome/omnibus-node) for
   a lab's own work with sharing tiers. Either answers `bundle_info` or
   `node_info`.
2. Add `nodes/<name>.yaml` (see [`nodes/schultz-evogenome.yaml`](nodes/schultz-evogenome.yaml)
   and [`schema/node.schema.json`](schema/node.schema.json)) and open a pull
   request. The check validates the manifest, resolves the maintainer's ORCID
   and the bundle DOI, and calls the endpoint. A core member merges.
3. A lab with no server can still contribute text to [`commons/`](commons/):
   protocols, methods, negative results, pipeline notes, CC-BY-4.0 or CC0.

A node may be registered as `planned` before its endpoint exists. The
nightly check marks unreachable nodes `stale`; it never deletes them, since
the archived bundle lets anyone re-host.

## Using it

`registry.json` is regenerated nightly from `nodes/`. The router reads it:

```sh
pip install git+https://github.com/schultz-evogenome/omnibus
omnibus route "ctenophore chromosome fusion" --dry-run     # which nodes would answer
omnibus route "ctenophore chromosome fusion"               # fan out, merge, attach node identity
```

Results from different nodes are merged by reciprocal rank fusion, so
scores from different backends are never compared directly. A hosted router
with a one-line client setup (`claude mcp add omnibus ...`) follows once
there are nodes to route to.

## Layout

| Path | What |
| --- | --- |
| `nodes/` | one manifest per node |
| `schema/node.schema.json` | the manifest schema, generated from `src/omnibus_registry/manifest.py` |
| `registry.json` | generated nightly; what the router reads |
| `commons/` | open text contributed directly, one file per entry |
| `src/omnibus_registry/` | `omnibus validate`, `schema`, `check-node`, `registry build`, `route`, `commons-check` |
| `docs/omnibus-design.md` | the design brief: motivation, prior art, rights, roadmap |
| `.github/workflows/` | the pull-request check and the nightly re-check |

## Status

Registry seed. One node is registered, as planned; its served view is
public in its repository. The Dunn lab's public corpuscles
(github.com/caseywdunn/corpus) are the natural second node. See the design
brief for the roadmap and the open questions.

## Governance

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Code is MIT; `commons/` entries carry their own license, CC-BY-4.0 by
default.

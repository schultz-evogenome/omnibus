# Omnibus

Community registry of lab knowledge servers, served over the Model Context Protocol. Bioconda model: one repo, one manifest per node, CI on every pull request, a router that fans queries out to registered nodes.

Read `docs/omnibus-design.md` before doing any work in this repo. It holds the design, the prior art to study, the rules on rights and attribution, and the roadmap.

Conventions:
- Build on corpus (github.com/caseywdunn/corpus). Where its vocabulary applies, use it: library, bundle, `bundle_info`. The whole thing a lab runs is a node. Do not reinvent what corpus already does. The lab-side software lives in github.com/schultz-evogenome/omnibus-node; this repository is the registry only.
- Default closed. Nothing is served or committed that the contributor does not hold rights to.
- Every entry carries who and when.
- Propose layouts and schemas before writing code. Ask before adding dependencies.
- Plain declarative prose in all docs. No marketing language.
- `src/omnibus_registry/manifest.py` is the one definition of a manifest; `schema/node.schema.json` is generated from it with `omnibus schema --out schema/node.schema.json` and must be regenerated in the same change.

# Contributing

Omnibus works the way bioconda does: contributions are pull requests, a
check runs on every one, and a core member merges. Read the
[code of conduct](CODE_OF_CONDUCT.md) first.

## Adding a node

1. Fork the repository and add `nodes/<name>.yaml`. The file name and the
   `name` field must match. Copy `nodes/schultz-evogenome.yaml` and change
   every field; the schema is `schema/node.schema.json`.
2. Run the checks yourself:

   ```sh
   pip install -e .
   omnibus validate nodes/<name>.yaml
   omnibus check-node nodes/<name>.yaml     # ORCID, DOI, endpoint
   ```

3. Open a pull request titled `Add node <name>`. The pull-request check runs
   the same commands. It fails when the manifest is invalid, the ORCID does
   not resolve, the bundle DOI does not resolve, or the endpoint does not
   answer as an MCP server. A node with no endpoint yet is registered with
   `status: planned` and `endpoint: null`.
4. A core member reviews and merges. After the merge, the nightly check
   probes the endpoint and publishes `registry.json`.

To change a node, open a pull request titled `Update node <name>` and bump
`last_verified` to the day you confirmed the manifest is right.

What a manifest promises:

- `maintainer` is a person, identified by ORCID, who answers for the node.
- `serves` names only content the lab holds rights to serve.
- `license_default` is what applies when a served item carries no license of
  its own. Per-item licenses live in the node, not here.
- `bundle_doi`, when set, is a Zenodo record from which the node can be
  re-hosted if its server disappears.

## Adding to the commons

`commons/<node>/<slug>.md`, one entry per file, with the front matter
described in [`commons/README.md`](commons/README.md). `license` must be
CC-BY-4.0 or CC0-1.0. Run `omnibus commons-check commons/<node>/<slug>.md`
before opening the pull request; the check does the same. Title the pull
request `Add commons: <short title>`.

What never goes in the repository: PDFs, embeddings, anyone else's text,
unpublished collaborator results, raw data, credentials.

## Code

Changes to `src/` need tests. `ruff check src tests` and `pytest` must pass.
If a change alters the manifest model, regenerate the schema
(`omnibus schema --out schema/node.schema.json`) in the same pull request;
the check fails when the committed schema is out of date.

## Review and merging

Anyone may review. Core members merge. A pull request that passes the check
and has no open review comments is merged within a week; if it has not
been, ping `@schultz-evogenome/omnibus-core` in a comment.

The core team is listed in `.github/CODEOWNERS`. It should have at least
two members who are not from the same lab; while it does not, that is a
known gap, not a policy. To join, say so in a pull request or issue after
having contributed a node or a few commons entries.

## Questions

Open an issue. There is no chat channel yet.

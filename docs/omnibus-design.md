# Omnibus: design brief

Status: draft, 2026-09-12. Written from a design conversation. Nothing here is built yet. Treat every claim about external projects as something to verify before relying on it.

## One paragraph

Omnibus is a community registry of lab knowledge servers. Each lab runs a server (a node) that exposes what the lab has done, how it does things, and what it is working on, over the Model Context Protocol (MCP), the standard that Claude Code, Claude Desktop, and other clients use to reach external data. Omnibus is the one repository where labs register their nodes by pull request (PR), the continuous-integration (CI) checks that keep the registry honest, and a router that lets an agent query every registered node at once and get answers with a Digital Object Identifier (DOI) attached to every chunk. The model is bioconda: one repo, a small manifest per entry, a bot that lints every PR, a core team that merges. The name is Latin for "for all." An omnibus volume collects works by many authors.

## Why

The motivation is to build on existing research instead of reinventing it. Published papers are the lossiest record of a lab's work. The parameter that didn't work, the assembly that failed quality control, the reason one aligner replaced another, none of it reaches the paper. A lab brain holds that material and makes it queryable. A network of lab brains makes it queryable across labs.

The larger ambition is Aaron Swartz's: humanity's science, shared. The design constraint that makes this buildable is that every node serves only what its lab holds rights to. Accepted manuscripts, preprints, open-access papers, code, data, protocols, negative results. Nothing on the network is anyone else's to take down. The network is the open shadow of science, and it grows every time a lab keeps its rights.

Earlier decentralized-science efforts died because hosting was altruism. Dat and ScienceFair (2017 to 2019) had a good protocol and no reason for anyone to keep a node running after a grant ended. The blockchain DeSci wave solved a problem nobody had. Nanopublications survived by being small and useful. Omnibus differs in one way: every lab runs its node for its own benefit, and sharing is a flag in a config file. The reader is an agent, which will traverse two hundred small servers in a way no human would.

## Principles

1. Self-interested hosting. A lab runs its node because it is the lab's own brain. Sharing costs nothing extra.
2. Rights-based federation. Serve only what you can lawfully redistribute. Default closed.
3. Attribution on everything. Every entry carries who and when. Every retrieved chunk carries a DOI or a stable identifier.
4. Persistence outlives servers. Every node archives its bundle to Zenodo on release, so anyone can re-host from the DOI when a lab's server dies.
5. Build on corpus, don't compete with it. Use its vocabulary and bundle format. Ship as a corpus plugin where possible.
6. Capture is automatic. Nobody writes to a knowledge base by hand for more than three weeks.
7. The client is one line. Joining is a PR; using it is `claude mcp add omnibus`.

## What already exists (read before building)

- **corpus** (Church, Mańko, Zapata & Dunn, 2026; DOI 10.5281/zenodo.19964909; MIT; github.com/caseywdunn/corpus). Turns a folder of PDFs into a queryable knowledge base served over MCP. Built for taxonomic literature: OCR of old scans, figure extraction, bibliography reconciliation, Darwin Core synonymy. Has a served-bundle format with a manifest, a `bundle_info` tool, per-paper `license` and `serve` fields in the BibTeX, an `instructions.md` injected at session start, a project-scoped `.mcp.json`, and a plan for a skills/plugin directory (issue #178). The Dunn lab hosts public corpuscles on AWS. This is node one. Talk to Casey Dunn and Sam Church before building anything they may already have on their roadmap (dev_docs/PLAN.md).
- **callosum** (github.com/cliffworkman/callosum). Local-first scholarly research environment that keeps literature, evidence, methods, manuscripts, and provenance connected. Built with Claude Code. Single-lab, not federated. The closest existing thing to the lab-brain half of this design. Study it.
- **seren-corpus-callosum** (PyPI). Read-only fan that federates several memory stores into one rank-merged recall surface using reciprocal rank fusion. Small, but it is the router pattern.
- **PaperQA2** (Skarlinski et al. 2024, arXiv:2409.13740). Retrieval-augmented generation over a local folder of PDFs; evaluated against subject-matter experts on retrieval, summarization, and contradiction detection. The contradiction-detection idea, pointed inward at one lab's own papers, is a possible research result.
- **Nanopublications** (Knowledge Pixels; nanopub.space). Decentralized server network of tiny machine-readable findings with provenance, running since about 2014, now agent-facing with a Claude skill. This is the findings layer that Omnibus's document layer could feed.
- **Zotero MCP servers** (several), NotebookLM, Claude Projects. Retrieval over a personal library. No write path, no shared serving.
- **Benchling**. The closest commercial lab brain, but it is an electronic lab notebook, so it models wet-lab experiments and samples, not code, pipelines, or papers. Worth using for the wet side of the Schultz lab regardless.
- **Bioconda** (Grüning et al. 2018, Nature Methods). The governance and contribution model to copy exactly.
- The MCP specification now includes server discovery via `.well-known` URLs. Use it.

## Part 1: the lab node (the Schultz lab brain)

A lab brain is three different memories, and each wants a different mechanism.

### What the lab has done
Papers, theses, internal reports, dead ends, and the accepted-manuscript sources (LaTeX or docx, not publisher PDFs) for the lab's own work. Colleagues' papers only where the lab has rights to serve them. This is the corpus-shaped layer: retrieval, read-mostly, rebuilt when documents are added. It is the only layer that needs a pipeline, and it is not needed until there are a few hundred PDFs.

### How the lab does things
Pipeline runbooks with pinned environments, wet-lab protocols, animal-facility procedures, how to order reagents, how to get onto the cluster, how collaborators upload data. This is skills-shaped: markdown in git, read whole by whoever or whatever needs it. Retrieval is wrong for this layer; an exemplar set is small and you want whole documents in context. This layer is what stops wheel reinvention.

### What is happening now
Who is working on what, decisions and why, open questions, what was tried last week and failed. Changes daily. Needs a write path. Without it the brain is a library.

### Stack for the Schultz lab
- One git repo in the `conchoecia` GitHub organization is the source of truth: `people/`, `projects/`, `protocols/`, `decisions/`, `dead-ends/`, and a `.bib` pointing at the PDFs. Same shape as a persistent memory store, but shared.
- The lab's Mac mini M4 serves the repo over MCP on Tailscale. Lab members already reach the workstation this way.
- The Minisforum N5 Pro NAS (RAIDZ2) holds PDFs and built corpuscle bundles.
- Lehigh's Sol cluster (H100 node) builds corpuscles when there are enough PDFs to justify it.
- A lab plugin, installed in every member's Claude Code, carries the skills and the MCP config. This is the corpus/dunnlab_code pattern. A new student gets the whole procedural layer on day one.

### Capture
- A session-end hook in Claude Code appends a dated, attributed entry to the repo: project, what was tried, what failed, what was decided.
- A `record_dead_end` tool on the MCP server logs a failed run the moment it fails.
- The week's entries are reviewed as a PR. If everyone in the lab writes, the review step exists from day one.
- Test: when a student leaves, their year of context should already be in the brain. If it isn't, capture failed.

### Rules
- Every entry carries who and when.
- Raw data and unpublished collaborator results stay out unless the collaborator agreed.
- Serve only PDFs the lab can lawfully redistribute: its own accepted manuscripts and the open-access subset.

## Part 2: the registry (Omnibus)

### Manifest
One YAML file per node, submitted by PR. Draft schema:

```yaml
name: schultz-evogenome
maintainer: 0000-0003-1190-1122      # ORCID
endpoint: https://brain.evogeno.me/mcp
transport: streamable-http           # or sse
auth: public                         # or token
scope: [Ctenophora, Porifera, chromosome evolution, bioluminescence]
serves: [accepted-manuscripts, preprints, protocols, negative-results, code]
license_default: CC-BY-4.0
bundle_doi: 10.5281/zenodo.XXXXXXX
last_verified: 2026-09-12
```

### CI on every PR
- Validate the manifest against a JSON schema.
- Resolve the DOI and the ORCID.
- Call the endpoint's `bundle_info` tool; confirm it is reachable and that what it reports matches the manifest.
- Require a license on every entry, as bioconda requires one on every recipe.

### Nightly
- Re-check every node. Mark dead nodes stale, never delete them; the Zenodo bundle still lets anyone re-host.
- Publish one `registry.json` from the manifests. This is what the router reads.

### Commons
A `commons/` directory where labs PR small, fully open text directly: protocols, methods snippets, negative results, pipeline notes. CC-BY or CC0 as a condition of merging. The repo itself is then a queryable brain: anyone can clone it and point corpus or a skill at it. CI builds a corpuscle from `commons/` on each release and pushes it to Zenodo. This is the biocontainers half of the model, automated builds from recipes, and it covers the zero-hosting case: a lab with no server can still be in the network with just a PR.

What never goes in the repo: PDFs, embeddings, anything the contributor doesn't hold rights to.

### Router
One MCP server. Reads `registry.json`, fans a query out to the nodes whose scope matches, merges results, and attaches the DOI or stable identifier to every chunk it returns. This can be a subcommand of corpus rather than a new binary. Discovery via `.well-known`.

### Rights model
Default closed. A node serves nothing it hasn't marked shareable. Per-document `license` and `serve` fields, as corpus already has.

### Governance
- At least two maintainers who are not Darrin. Casey Dunn and Sam Church are the obvious first two.
- Contribution guide, code of conduct, and a bot that does the first review, all copied from bioconda.
- First community: taxonomy, because corpuscles already exist there and the pain (scattered, old literature) is shared. Not "all of science."

## Roadmap

1. Lab repo and plugin for the Schultz lab. An afternoon. Needed next week regardless.
2. Capture hook and `record_dead_end` tool. Everything downstream depends on capture.
3. corpus over the lab's PDFs, once there are a few hundred and a reason to query them.
4. Provenance layer: resolve each methods step in each paper to a repository, commit, environment file, data accession, and parameter values. Report what resolves and what doesn't. This is where a tools paper comes from (GigaScience, PLOS Computational Biology, or a Bioinformatics application note; Patterns if the reproducibility framing leads). The Dunn lab lists a code repository next to its papers going back to 2005, so their back catalog plus the Schultz lab's is the evaluation set.
5. Registry seed: two nodes and a registry. The Dunn lab has one node. The Schultz lab is the second. That is a federation.
6. Paper on the network once there are about ten nodes across three communities and a reviewer can query it and get an answer with a DOI on it.

## Open questions

- Who writes to the lab brain: only Darrin, or everyone? If everyone, the review step starts on day one.
- Is provenance already on the corpus roadmap? If yes, contribute it there and share authorship rather than running a parallel project.
- Default license for `commons/`: CC-BY or CC0.
- Where the community router runs and who pays for it. The reference deploy for corpus is AWS behind a load balancer.
- Whether the lab-node software is corpus with a plugin, or a thin wrapper around corpus plus a markdown-repo server.

## Name and collisions

Omnibus: Latin "for all"; an omnibus volume collects works by many authors. Chef's `omnibus` packaging tool exists in the devops world. Check the GitHub org, PyPI, the MCP registry, and the domain before writing the README. The artifact is a repo plus `registry.json`, so a package-name collision matters less; `omnibus-registry` is the fallback PyPI name. Rejected names and why: `reef` (an existing agent-runtime project with a `reef` CLI), `bommie` and `atoll` (Indigenous and Dhivehi loanwords), `callosum` and other brain anatomy (six claimants, two in this exact space), `stolon`, `shoal`, `terrane` (existing projects).

## Suggested first tasks for Claude Code

1. Read this document. Propose a repository layout for Omnibus and for the Schultz lab repo. Do not write code until the layout is approved.
2. Write the manifest JSON schema and a validator.
3. Write the GitHub Actions workflows: PR validation, nightly health check, `registry.json` publication.
4. Write CONTRIBUTING.md and a code of conduct, adapted from bioconda's.
5. Scaffold an `omnibus` command with `init`, `validate`, and `route` subcommands, or propose the same as corpus subcommands.
6. Draft the Schultz lab manifest and the first `commons/` entry.

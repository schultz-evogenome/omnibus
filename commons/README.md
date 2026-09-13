# commons

Small, fully open text that labs contribute directly, by pull request:
protocols, methods snippets, negative results, pipeline notes. Anyone can
clone this directory and point corpus or a skill at it, and a lab with no
server is still in the network with one file here.

Layout: `commons/<node-name>/<slug>.md`, one entry per file. Every entry
starts with front matter:

```yaml
---
title: What the entry is
authors:
  - name: Person Name
    orcid: 0000-0002-1825-0097
date: 2026-09-13
license: CC-BY-4.0        # or CC0-1.0
node: schultz-evogenome   # the contributing node, from nodes/
type: protocol            # protocol | methods | negative-result | pipeline-note | dataset-note
keywords: [a, few, terms]
---
```

`license` is required and must be CC-BY-4.0 or CC0-1.0; the pull-request
check refuses anything else. CC-BY-4.0 is the default for new entries.

What never goes here: PDFs, embeddings, anyone else's text, unpublished
collaborator results, raw data.

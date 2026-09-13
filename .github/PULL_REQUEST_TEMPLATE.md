Describe the pull request here.

----

- Adding a node: title the pull request `Add node <name>`; updating one: `Update node <name>`; a commons entry: `Add commons: <short title>`.
- Run `omnibus validate nodes/<name>.yaml` and `omnibus check-node nodes/<name>.yaml` (or `omnibus commons-check <file>`) before opening it; the check runs the same.
- Confirm the node serves only content the lab holds rights to serve, and that every commons entry carries a CC-BY-4.0 or CC0-1.0 license.
- When the check is green and there are no open comments, a core member merges. If nothing has happened in a week, ping `@schultz-evogenome/omnibus-core`.

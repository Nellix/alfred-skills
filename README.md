# Alfred Skills Registry

This repository is the public, reviewable skill catalog for
[Alfred](https://github.com/Nellix/alfred), a local-first Android AI agent.

Every shared skill and multi-step workflow is ordinary JSON. Every change is a pull request. The Android application pulls
the generated catalog directly from GitHub, verifies its revision, paths, SHA-256 digests, schema,
parameters, actions, and safety constraints, then atomically replaces its local downloaded catalog.
There is no registry server, container, Kubernetes cluster, or database.

## Repository layout

```text
skills/
  android/settings/       Android system settings skills
  google/maps/            Google Maps and navigation skills
  google/youtube/         YouTube skills
workflows/                Device-verified reusable task graphs
registry/index.json       Generated catalog consumed by Alfred
schema/skill.schema.json  Human- and tool-readable format
schema/workflow.schema.json Workflow graph format
scripts/build_registry.py Validation and deterministic index builder
docs/                     Format, governance, and security documentation
```

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). A contribution must:

1. contain a generalized intent template rather than a real user's prompt or data;
2. use typed placeholders for destinations, queries, recipients, or other values;
3. stay inside Alfred's bounded action vocabulary;
4. require confirmation for interactive actions;
5. pass `python3 scripts/build_registry.py --check` in CI;
6. be reviewed and merged through a pull request.

Workflows additionally declare an acyclic tree/DAG of screen-matched nodes and device-verification
evidence. This lets Alfred reuse an entire successful plan while still re-planning a missing edge
when the UI diverges.

## Local validation

```bash
python3 scripts/build_registry.py --check
```

To add or update a skill and rebuild revision 2:

```bash
python3 scripts/build_registry.py --write --revision 2
python3 scripts/build_registry.py --check
```

## Trust model

GitHub branch protection, mandatory pull-request review, HTTPS delivery, and per-file SHA-256
verification form the initial trust boundary. Digests prevent partial or inconsistent downloads;
they do not protect against a compromised repository maintainer account. Signed release manifests
are planned before production use. See [docs/security.md](docs/security.md).

Licensed under Apache-2.0.

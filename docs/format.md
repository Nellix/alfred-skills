# Skills and workflow formats

Each skill document has schema version `1` and these fields:

- `id`: stable dotted identifier;
- `version`: positive integer, increased when behavior changes;
- `canonical_intent`: generalized semantic intent;
- `title` and `description`: human-facing explanation;
- `match.goal_template`: normalized natural-language template;
- `match.parameter_types`: placeholder names mapped to `string`, `integer`, or `boolean`;
- `match.source_screen`: `*` or the required semantic screen ID;
- `safety`: `safe` or `confirm`;
- `terminal`: whether the plan completes the request;
- `actions`: one to eight bounded Alfred device actions.

Supported actions are `launch_app`, `open_deep_link`, `click`, `set_text`, `scroll`, `back`, `wait`,
and `stop`. Interactive targets use `label:<semantic label>`. Text-entry values must be placeholders,
not literal personal data. Deep links are limited to `https`, `geo`, and `mailto` schemes.

The generated `registry/index.json` contains only catalog metadata and a SHA-256 digest for every
skill file. Clients download the index first and reject rollback, same-revision equivocation,
unexpected paths, digest mismatches, invalid schemas, and unsafe actions before committing an
update.

## Workflow format

A workflow is a reviewed, acyclic task graph under `workflows/`. It has the same identity,
intent-template, parameter, action, and safety rules as a skill, plus:

- `entry_node`: the first node ID;
- `nodes[].source_screen`: an exact semantic screen ID, `*`, or a prefix ending in `*`;
- `nodes[].children`: possible next nodes selected by the next observed screen;
- `nodes[].terminal`: terminal nodes have no children; non-terminal nodes have at least one;
- `verification`: device-test evidence (`device_verified`, successful run count, and replay model calls).

The builder rejects cycles, unreachable nodes, missing children, invalid wildcard placement, and
unverified workflows. A workflow contains generalized templates and semantic labels only—never raw
prompts, screenshots, accessibility trees, account data, or concrete parameter values.

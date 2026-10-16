#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
WORKFLOWS = ROOT / "workflows"
INDEX = ROOT / "registry" / "index.json"
ID = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
PARAMETER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
PACKAGE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")
PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
ACTION_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:\|(url))?\}")
DANGEROUS = re.compile(
    r"\b(send|delete|remove|purchase|buy|pay|transfer|install|uninstall|factory reset)\b",
    re.IGNORECASE,
)
ALLOWED_ACTIONS = {
    "launch_app",
    "open_deep_link",
    "click",
    "set_text",
    "scroll",
    "back",
    "wait",
    "stop",
}
INTERACTIVE = {"click", "set_text"}
PARAMETER_TYPES = {"string", "integer", "boolean"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def object_keys(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unexpected = set(value) - allowed
    require(not unexpected, f"{context}: unexpected fields: {sorted(unexpected)}")


def validate_actions(
    actions: Any,
    *,
    relative: str,
    safety: str,
    parameter_types: dict[str, Any],
) -> None:
    require(isinstance(actions, list) and 1 <= len(actions) <= 8, f"{relative}: invalid action count")
    for position, action in enumerate(actions):
        context = f"{relative}: action {position + 1}"
        require(isinstance(action, dict), f"{context}: must be an object")
        object_keys(action, {"action", "target", "value", "package", "uri"}, context)
        name = action.get("action")
        require(name in ALLOWED_ACTIONS, f"{context}: unsupported action")
        package = action.get("package")
        if package is not None:
            require(isinstance(package, str) and PACKAGE.fullmatch(package) is not None, f"{context}: invalid package")
        uri = action.get("uri")
        if uri is not None:
            require(isinstance(uri, str) and uri.split(":", 1)[0].lower() in {"https", "geo", "mailto"}, f"{context}: unsafe URI")
        if name in {"click", "set_text", "scroll"}:
            target = action.get("target")
            require(isinstance(target, str) and target.startswith("label:"), f"{context}: interactive target must use label:")
            require(DANGEROUS.search(target) is None, f"{context}: destructive target")
        if name in INTERACTIVE:
            require(safety == "confirm", f"{context}: interactive action requires safety=confirm")
        if name == "set_text":
            value = action.get("value")
            require(isinstance(value, str) and "${" in value, f"{context}: text value must be parameterized")
        for field in ("target", "value", "package", "uri"):
            value = action.get(field)
            if value is None:
                continue
            references = ACTION_PLACEHOLDER.findall(value)
            require(
                all(parameter_name in parameter_types for parameter_name, _ in references),
                f"{context}: {field} references an undeclared parameter",
            )
            require(
                "${" not in ACTION_PLACEHOLDER.sub("", value),
                f"{context}: {field} contains an invalid parameter expression",
            )


def validate_skill(path: Path) -> dict[str, Any]:
    relative = path.relative_to(ROOT).as_posix()
    raw = path.read_bytes()
    require(len(raw) <= 256 * 1024, f"{relative}: file is too large")
    try:
        skill = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{relative}: invalid JSON: {exc}") from exc
    require(isinstance(skill, dict), f"{relative}: root must be an object")
    object_keys(
        skill,
        {
            "schema_version",
            "id",
            "version",
            "canonical_intent",
            "title",
            "description",
            "match",
            "safety",
            "terminal",
            "actions",
        },
        relative,
    )
    require(skill.get("schema_version") == 1, f"{relative}: unsupported schema")
    skill_id = skill.get("id")
    require(isinstance(skill_id, str) and ID.fullmatch(skill_id) is not None, f"{relative}: invalid id")
    version = skill.get("version")
    require(isinstance(version, int) and not isinstance(version, bool) and version >= 1, f"{relative}: invalid version")
    intent = skill.get("canonical_intent")
    require(isinstance(intent, str) and ID.fullmatch(intent) is not None, f"{relative}: invalid canonical_intent")
    title = skill.get("title")
    description = skill.get("description")
    require(isinstance(title, str) and 3 <= len(title.strip()) <= 80, f"{relative}: invalid title")
    require(isinstance(description, str) and 10 <= len(description.strip()) <= 300, f"{relative}: invalid description")

    match = skill.get("match")
    require(isinstance(match, dict), f"{relative}: match must be an object")
    object_keys(match, {"goal_template", "parameter_types", "source_screen"}, f"{relative}: match")
    template = match.get("goal_template")
    require(isinstance(template, str) and 3 <= len(template.strip()) <= 240, f"{relative}: invalid goal_template")
    types = match.get("parameter_types")
    require(isinstance(types, dict), f"{relative}: parameter_types must be an object")
    for name, parameter_type in types.items():
        require(isinstance(name, str) and PARAMETER.fullmatch(name) is not None, f"{relative}: invalid parameter name")
        require(parameter_type in PARAMETER_TYPES, f"{relative}: invalid parameter type for {name}")
    placeholders = set(PLACEHOLDER.findall(template))
    require(placeholders == set(types), f"{relative}: template placeholders and parameter_types differ")
    source_screen = match.get("source_screen")
    require(isinstance(source_screen, str) and 1 <= len(source_screen) <= 240, f"{relative}: invalid source_screen")

    safety = skill.get("safety")
    require(safety in {"safe", "confirm"}, f"{relative}: invalid safety")
    require(isinstance(skill.get("terminal"), bool), f"{relative}: terminal must be boolean")
    validate_actions(skill.get("actions"), relative=relative, safety=safety, parameter_types=types)

    return {
        "id": skill_id,
        "version": version,
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def validate_workflow(path: Path) -> dict[str, Any]:
    relative = path.relative_to(ROOT).as_posix()
    raw = path.read_bytes()
    require(len(raw) <= 256 * 1024, f"{relative}: file is too large")
    try:
        workflow = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{relative}: invalid JSON: {exc}") from exc
    require(isinstance(workflow, dict), f"{relative}: root must be an object")
    object_keys(
        workflow,
        {
            "schema_version", "id", "version", "canonical_intent", "title", "description",
            "match", "safety", "entry_node", "nodes", "verification",
        },
        relative,
    )
    require(workflow.get("schema_version") == 1, f"{relative}: unsupported schema")
    workflow_id = workflow.get("id")
    require(isinstance(workflow_id, str) and ID.fullmatch(workflow_id) is not None, f"{relative}: invalid id")
    version = workflow.get("version")
    require(isinstance(version, int) and not isinstance(version, bool) and version >= 1, f"{relative}: invalid version")
    intent = workflow.get("canonical_intent")
    require(isinstance(intent, str) and ID.fullmatch(intent) is not None, f"{relative}: invalid canonical_intent")
    title = workflow.get("title")
    description = workflow.get("description")
    require(isinstance(title, str) and 3 <= len(title.strip()) <= 80, f"{relative}: invalid title")
    require(isinstance(description, str) and 10 <= len(description.strip()) <= 300, f"{relative}: invalid description")

    match = workflow.get("match")
    require(isinstance(match, dict), f"{relative}: match must be an object")
    object_keys(match, {"goal_template", "parameter_types"}, f"{relative}: match")
    template = match.get("goal_template")
    require(isinstance(template, str) and 3 <= len(template.strip()) <= 240, f"{relative}: invalid goal_template")
    types = match.get("parameter_types")
    require(isinstance(types, dict), f"{relative}: parameter_types must be an object")
    for name, parameter_type in types.items():
        require(isinstance(name, str) and PARAMETER.fullmatch(name) is not None, f"{relative}: invalid parameter name")
        require(parameter_type in PARAMETER_TYPES, f"{relative}: invalid parameter type for {name}")
    require(set(PLACEHOLDER.findall(template)) == set(types), f"{relative}: template placeholders and parameter_types differ")

    safety = workflow.get("safety")
    require(safety in {"safe", "confirm"}, f"{relative}: invalid safety")
    entry_node = workflow.get("entry_node")
    require(isinstance(entry_node, str) and ID.fullmatch(entry_node) is not None, f"{relative}: invalid entry_node")
    nodes = workflow.get("nodes")
    require(isinstance(nodes, list) and 1 <= len(nodes) <= 64, f"{relative}: invalid node count")
    node_ids: set[str] = set()
    children: dict[str, list[str]] = {}
    for position, node in enumerate(nodes):
        context = f"{relative}: node {position + 1}"
        require(isinstance(node, dict), f"{context}: must be an object")
        object_keys(node, {"id", "source_screen", "actions", "children", "terminal"}, context)
        node_id = node.get("id")
        require(isinstance(node_id, str) and ID.fullmatch(node_id) is not None, f"{context}: invalid id")
        require(node_id not in node_ids, f"{context}: duplicate id")
        node_ids.add(node_id)
        source_screen = node.get("source_screen")
        require(isinstance(source_screen, str) and 1 <= len(source_screen) <= 240, f"{context}: invalid source_screen")
        require("*" not in source_screen[:-1], f"{context}: wildcard is allowed only as the final character")
        terminal = node.get("terminal")
        require(isinstance(terminal, bool), f"{context}: terminal must be boolean")
        node_children = node.get("children")
        require(isinstance(node_children, list) and len(node_children) <= 16, f"{context}: invalid children")
        require(all(isinstance(child, str) and ID.fullmatch(child) for child in node_children), f"{context}: invalid child id")
        require(len(node_children) == len(set(node_children)), f"{context}: duplicate child")
        require((terminal and not node_children) or (not terminal and node_children), f"{context}: terminal/children mismatch")
        validate_actions(node.get("actions"), relative=context, safety=safety, parameter_types=types)
        children[node_id] = node_children

    require(entry_node in node_ids, f"{relative}: entry_node does not exist")
    require(all(child in node_ids for values in children.values() for child in values), f"{relative}: unknown child node")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        require(node_id not in visiting, f"{relative}: workflow graph contains a cycle")
        if node_id in visited:
            return
        visiting.add(node_id)
        for child in children[node_id]:
            visit(child)
        visiting.remove(node_id)
        visited.add(node_id)

    visit(entry_node)
    require(visited == node_ids, f"{relative}: workflow contains unreachable nodes")

    verification = workflow.get("verification")
    require(isinstance(verification, dict), f"{relative}: verification must be an object")
    object_keys(verification, {"status", "verified_runs", "replay_model_calls"}, f"{relative}: verification")
    require(verification.get("status") == "device_verified", f"{relative}: workflow must be device_verified")
    verified_runs = verification.get("verified_runs")
    replay_model_calls = verification.get("replay_model_calls")
    require(isinstance(verified_runs, int) and not isinstance(verified_runs, bool) and verified_runs >= 1, f"{relative}: invalid verified_runs")
    require(isinstance(replay_model_calls, int) and not isinstance(replay_model_calls, bool) and replay_model_calls >= 0, f"{relative}: invalid replay_model_calls")

    return {
        "id": workflow_id,
        "version": version,
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def expected_index(revision: int) -> dict[str, Any]:
    require(revision >= 1, "registry revision must be positive")
    entries = [validate_skill(path) for path in sorted(SKILLS.rglob("*.json"))]
    require(len(entries) <= 256, "registry contains too many skills")
    ids = [entry["id"] for entry in entries]
    require(len(ids) == len(set(ids)), "registry contains duplicate skill ids")
    workflows = [validate_workflow(path) for path in sorted(WORKFLOWS.rglob("*.json"))]
    require(len(workflows) <= 128, "registry contains too many workflows")
    workflow_ids = [entry["id"] for entry in workflows]
    require(len(workflow_ids) == len(set(workflow_ids)), "registry contains duplicate workflow ids")
    return {
        "schema_version": 1,
        "revision": revision,
        "skills": sorted(entries, key=lambda item: item["id"]),
        "workflows": sorted(workflows, key=lambda item: item["id"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and build the Alfred static registry")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate skills and require an up-to-date index")
    mode.add_argument("--write", action="store_true", help="write a deterministic index")
    parser.add_argument("--revision", type=int, help="positive revision required with --write")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.write:
            require(args.revision is not None, "--revision is required with --write")
            document = expected_index(args.revision)
            INDEX.parent.mkdir(parents=True, exist_ok=True)
            INDEX.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"wrote {INDEX.relative_to(ROOT)} revision {args.revision} with {len(document['skills'])} skills")
            return 0

        require(args.revision is None, "--revision is only valid with --write")
        require(INDEX.exists(), "registry/index.json is missing")
        current = json.loads(INDEX.read_text(encoding="utf-8"))
        require(isinstance(current, dict), "registry index must be an object")
        object_keys(current, {"schema_version", "revision", "skills", "workflows"}, "registry/index.json")
        require(current.get("schema_version") == 1, "unsupported registry index schema")
        revision = current.get("revision")
        require(isinstance(revision, int) and not isinstance(revision, bool), "invalid registry revision")
        expected = expected_index(revision)
        require(current == expected, "registry/index.json is stale; rebuild it with --write")
        print(
            f"validated revision {revision} with {len(expected['skills'])} skills "
            f"and {len(expected['workflows'])} workflows"
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"registry validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

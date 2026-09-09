"""Exact native skill catalogs derived from pinned built-ins and declared trial inputs."""

import re
import tomllib
from pathlib import PurePosixPath

import yaml

from .records import digest, parse_json

DISABLED_FEATURES = ("plugins", "remote_plugin", "apps")


def validate_features(config: bytes, effective: str) -> None:
    configured = tomllib.loads(config.decode("utf-8")).get("features", {})
    lines = [line.split() for line in effective.splitlines()]
    actual = {line[0]: line[-1] for line in lines if len(line) >= 3}
    if any(
        configured.get(name) is not False or actual.get(name) != "false"
        for name in DISABLED_FEATURES
    ):
        raise ValueError("native plugins, remote_plugin and apps must be explicitly disabled")


def verify_builtins(files: dict[str, bytes], pins: dict) -> None:
    actual = {
        name.removeprefix("builtin-skills/"): digest(data)
        for name, data in files.items()
        if name.startswith("builtin-skills/") and "__pycache__" not in name.split("/")
    }
    if pins.get("schema_version") != 1 or actual != pins["files"]:
        raise ValueError("native built-in skill bytes differ from the pinned runtime profile")


def expected_catalog(builtins: dict[str, bytes], inputs: dict[str, bytes]) -> list[dict]:
    entries = []
    for files, prefix, installed in (
        (builtins, "builtin-skills/", "/home/runtime/codex/skills/.system/"),
        (inputs, ".agents/skills/", "/work/.agents/skills/"),
    ):
        for path, raw in sorted(files.items()):
            relative = path.removeprefix(prefix)
            if not path.startswith(prefix) or not re.fullmatch(r"[^/]+/SKILL.md", relative):
                continue
            metadata = (
                yaml.safe_load(
                    files.get(
                        prefix + relative.removesuffix("SKILL.md") + "agents/openai.yaml", b"{}"
                    )
                )
                or {}
            )
            if metadata.get("policy", {}).get("allow_implicit_invocation", True) is False:
                continue
            text = raw.decode("utf-8").replace("\r\n", "\n")
            if not text.startswith("---\n") or "\n---" not in text[4:]:
                raise ValueError("declared skill requires YAML frontmatter")
            header = yaml.safe_load(text[4:].split("\n---", 1)[0])
            name, description = header["name"], header["description"]
            if not isinstance(name, str) or not isinstance(description, str):
                raise ValueError("declared skill requires textual name and description")
            entries.append(
                {
                    "name": name,
                    "description": " ".join(description.split()),
                    "path": installed + relative,
                }
            )
    return sorted(entries, key=lambda entry: entry["path"])


def compare_catalog(text: str, expected: list[dict]) -> dict:
    roots = dict(re.findall(r"^- `(r\d+)` = `([^`]+)`$", text, re.M))
    actual, errors = [], []
    for line in text.splitlines():
        if not line.startswith("- ") or "(file:" not in line:
            continue
        match = re.fullmatch(r"- (.+?): (.*) \(file: ([^)]+)\)", line)
        if not match:
            errors.append("malformed skill entry: " + line)
            continue
        name, description, reference = match.groups()
        alias, _, tail = reference.partition("/")
        path = roots[alias] + "/" + tail if alias in roots else reference
        if not path.startswith("/") or ".." in PurePosixPath(path).parts:
            errors.append("unresolved skill path: " + reference)
        actual.append({"name": name, "description": " ".join(description.split()), "path": path})
    actual.sort(key=lambda entry: entry["path"])
    return {
        "passed": not errors and actual == expected,
        "actual": actual,
        "errors": errors,
        "missing": [e for e in expected if e not in actual],
        "unexpected": [e for e in actual if e not in expected],
    }


def check_prompt(raw: bytes, expected: list[dict]) -> dict:
    messages = parse_json(raw)
    catalogs = [
        c["text"]
        for message in messages
        if message.get("role") == "developer"
        for c in message.get("content", [])
        if "<skills_instructions>" in c.get("text", "")
    ]
    checks = [compare_catalog(text, expected) for text in catalogs]
    return {"passed": bool(checks) and all(c["passed"] for c in checks), "catalogs": checks}


def check_sessions(files: dict[str, bytes], expected: list[dict]) -> dict:
    sessions, errors, seen = [], [], set()
    for path, raw in sorted(files.items()):
        if not path.startswith("sessions/"):
            continue
        try:
            rows = [parse_json(line) for line in raw.splitlines() if line.strip()]
            meta = [r["payload"] for r in rows if r.get("type") == "session_meta"]
            if len(meta) != 1 or not meta[0].get("id") or meta[0]["id"] in seen:
                raise ValueError("missing, repeated or duplicate session identity")
            seen.add(meta[0]["id"])
            catalogs = [
                c["text"]
                for row in rows
                if row.get("type") == "response_item" and row["payload"].get("role") == "developer"
                for c in row["payload"].get("content", [])
                if "<skills_instructions>" in c.get("text", "")
            ]
            checks = [compare_catalog(text, expected) for text in catalogs]
            sessions.append(
                {
                    "path": path,
                    "id": meta[0]["id"],
                    "source": meta[0].get("source"),
                    "passed": bool(checks) and all(c["passed"] for c in checks),
                    "catalogs": checks,
                }
            )
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            errors.append({"path": path, "error": str(error)})
    roots = [s for s in sessions if s["source"] == "exec"]
    if len(roots) != 1:
        errors.append({"error": "expected exactly one native exec root session"})
    for session in sessions:
        if session["source"] == "exec":
            continue
        try:
            parent = session["source"]["subagent"]["thread_spawn"]["parent_thread_id"]
            if parent not in seen or parent == session["id"]:
                raise ValueError("subagent parent is absent or self-referential")
        except (KeyError, TypeError, ValueError) as error:
            errors.append({"path": session["path"], "error": str(error)})
    return {
        "passed": bool(sessions) and not errors and all(s["passed"] for s in sessions),
        "sessions": sessions,
        "errors": errors,
    }

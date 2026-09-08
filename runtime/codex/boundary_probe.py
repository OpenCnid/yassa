"""Runs inside Codex's command sandbox. Never prints credential contents."""

import json
import os
import socket
from pathlib import Path


def readable(path):
    try:
        with open(path, "rb") as source:
            source.read(1)
        return True
    except OSError:
        return False


def writable(path):
    try:
        with open(path, "ab"):
            pass
        return True
    except OSError:
        return False


try:
    with socket.create_connection(("1.1.1.1", 443), timeout=3):
        network = True
except OSError:
    network = False

checks = {
    "credential_read_denied": not readable("/home/runtime/codex/auth.json"),
    "input_readable": readable("/work/input/boundary.txt"),
    "input_write_denied": not writable("/work/input/boundary.txt"),
    "skill_readable": readable("/work/.agents/skills/boundary/SKILL.md"),
    "skill_write_denied": not writable("/work/.agents/skills/boundary/SKILL.md"),
    "config_write_denied": not writable("/home/runtime/codex/config.toml"),
    "workspace_writable": writable("/work/output/probe.txt"),
    "direct_network_denied": not network,
    "host_repository_absent": not Path("/host-repository").exists(),
    "heldout_mount_absent": not Path("/heldout").exists(),
    "no_docker_socket": not Path("/var/run/docker.sock").exists(),
    "non_root": os.getuid() != 0,
}
print(json.dumps(checks, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)

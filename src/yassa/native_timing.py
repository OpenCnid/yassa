"""Controller monotonic observations at public eval/solver/sandbox boundaries."""

import time


class Lifecycle:
    def __init__(self, clock=None):
        self.clock = clock or time.monotonic
        self.origin = self.clock()
        self.phases = {}

    def start(self, name):
        started = self.clock()
        self.phases[name] = {
            "start_offset_seconds": started - self.origin,
            "end_offset_seconds": None,
            "duration_seconds": None,
            "status": "running",
        }
        return started

    def finish(self, name, status="completed"):
        phase = self.phases[name]
        ended = self.clock() - self.origin
        phase.update(
            end_offset_seconds=ended,
            duration_seconds=ended - phase["start_offset_seconds"],
            status=status,
        )
        return phase["duration_seconds"]

    def finish_open(self, status):
        for name, phase in self.phases.items():
            if phase["status"] == "running":
                self.finish(name, status)

    def record(self):
        phases = dict(self.phases)
        for name in (
            "evaluation",
            "adapter_setup",
            "native_command",
            "capture_acceptance",
            "sandbox_provisioning",
            "sandbox_cleanup",
        ):
            phases.setdefault(
                name,
                {
                    "start_offset_seconds": None,
                    "end_offset_seconds": None,
                    "duration_seconds": None,
                    "status": "unavailable",
                    "reason": "framework-owned phase has no separate adapter hook"
                    if name.startswith("sandbox_")
                    else "boundary not reached",
                },
            )
        return {
            "version": "native-lifecycle-v1",
            "clock": "controller monotonic offsets",
            "phases": phases,
            "boundaries": {
                "evaluation": (
                    "immediately around inspect_ai.eval; includes framework "
                    "setup/cleanup and logging"
                ),
                "adapter_setup": (
                    "solver entry through input installation, boundary probe "
                    "and root catalog preflight"
                ),
                "native_command": (
                    "sandbox.exec start to return/cancellation; existing native duration"
                ),
                "capture_acceptance": (
                    "after native return through independent captures "
                    "and recorded root/child acceptance"
                ),
            },
            "additivity": "evaluation encloses adapter phases; do not sum overlapping durations",
        }

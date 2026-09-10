"""Execute saved Python artifacts against a held-out pytest suite in Inspect Docker."""

import xml.etree.ElementTree as ET
from pathlib import Path

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_ai.solver import solver
from inspect_ai.util import ComposeConfig, ComposeService, SandboxEnvironmentSpec, sandbox

from .evidence import safe_name, write_new
from .records import canonical, digest


def junit_cases(raw):
    if len(raw) > 5_000_000 or b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        raise ValueError("invalid or oversized JUnit document")
    cases = {}
    for node in ET.fromstring(raw).iter("testcase"):
        key = node.attrib.get("classname", "") + "::" + node.attrib["name"]
        if key in cases:
            raise ValueError("duplicate JUnit case")
        status = next(
            (s for s in ("error", "failure", "skipped") if node.find(s) is not None), "pass"
        )
        cases[key] = status
    return cases


def compare_cases(reference, candidate):
    """Keep every reference-collected test in the denominator, including missing tests."""
    rows = {n: candidate.get(n, "missing") for n in reference}
    return {
        "passed": sum(s == "pass" for s in rows.values()),
        "total": len(reference),
        "cases": rows,
        "unexpected": sorted(set(candidate) - set(reference)),
    }


def test_artifact(destination, image, project, tests, timeout):
    """No model, credentials, host mounts, network, or candidate installation hooks."""
    destination.mkdir(parents=True, exist_ok=False)
    for names in (project, tests):
        for name in names:
            safe_name(name)
    record = {
        "image": image,
        "timeout_seconds": timeout,
        "project": {n: digest(b) for n, b in project.items()},
        "tests": {n: digest(b) for n, b in tests.items()},
        "status": "harness_failure",
        "cases": {},
    }

    @solver
    def run_tests():
        async def solve(state, generate):
            sb = sandbox()
            setup = await sb.exec(
                ["mkdir", "-p", "/tmp/yassa/project", "/tmp/yassa/evaluator"],
                timeout=30,
                timeout_retry=False,
            )
            if not setup.success:
                raise RuntimeError(setup.stderr)
            for prefix, files in (("project", project), ("evaluator", tests)):
                for name, body in files.items():
                    await sb.write_file("/tmp/yassa/" + prefix + "/" + name, body)
            # Default container user is root for setup only. Candidate code runs as UID 1000.
            protected = await sb.exec(
                ["chmod", "-R", "a-w,a+rX", "/tmp/yassa/project", "/tmp/yassa/evaluator"],
                timeout=30,
                timeout_retry=False,
            )
            if not protected.success:
                raise RuntimeError(protected.stderr)
            command = [
                "python3",
                "-m",
                "pytest",
                "-c",
                "/tmp/yassa/evaluator/pyproject.toml",
                "--confcutdir=/tmp/yassa/evaluator/tests",
                "-p",
                "no:cacheprovider",
                "--junitxml=/tmp/results.xml",
                "/tmp/yassa/evaluator/tests",
            ]
            record["command"] = command
            try:
                result = await sb.exec(
                    command,
                    cwd="/tmp/yassa/evaluator",
                    user="1000:1000",
                    env={
                        "PYTHONPATH": "/tmp/yassa/project/src:/tmp/yassa/project",
                        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                        "PYTHONNOUSERSITE": "1",
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "OMP_NUM_THREADS": "2",
                        "MKL_NUM_THREADS": "2",
                    },
                    timeout=timeout,
                    timeout_retry=False,
                )
                record.update(status="tested", exit_code=result.returncode)
                write_new(destination / "stdout.txt", result.stdout.encode())
                write_new(destination / "stderr.txt", result.stderr.encode())
            except TimeoutError:
                record.update(status="timeout", exit_code=None)
            try:
                raw = await sb.read_file("/tmp/results.xml", text=False)
                write_new(destination / "results.xml", raw)
                record["cases"] = junit_cases(raw)
            except (FileNotFoundError, ValueError, ET.ParseError, KeyError) as error:
                record["junit_error"] = str(error)
            state.completed = True
            return state

        return solve

    config = ComposeConfig(
        services={
            "default": ComposeService(
                image=image,
                init=True,
                command=["sleep", "infinity"],
                working_dir="/work",
                user="0:0",
                network_mode="none",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                mem_limit="4g",
                cpus=2.0,
            )
        }
    )
    inert = get_model("mockllm/model", memoize=False)
    task = Task(
        name="artifact-pytest",
        dataset=[Sample(input="Run the frozen pytest oracle.")],
        solver=run_tests(),
        model=inert,
        sandbox=SandboxEnvironmentSpec("docker", config),
    )
    try:
        logs = eval(
            task,
            model=inert,
            log_dir=str(destination / "inspect"),
            sandbox_prebuilt=True,
            display="none",
            notification=False,
            ctl_server=False,
            log_shared=False,
            log_realtime=False,
            score=False,
            epochs=1,
            retry_on_error=0,
            fail_on_error=False,
            max_samples=1,
            max_tasks=1,
            time_limit=timeout + 180,
        )
        log = logs[0]
        record["inspect_status"] = log.status
        record["inspect_log"] = Path(log.location).relative_to(destination).as_posix()
        sample = log.samples[0] if log.samples else None
        error = sample.error if sample and sample.error else log.error
        if log.status != "success" or error:
            record["status"] = "harness_failure"
            record["error"] = error.message if error else "Inspect did not complete"
    except Exception as error:
        record.update(status="harness_failure", error=str(error))
    write_new(destination / "result.json", canonical(record))
    return record

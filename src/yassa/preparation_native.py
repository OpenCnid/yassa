"""Preparation via the same Inspect-owned native boundary used by measured attempts."""

import io
import re
import zipfile

from .evidence import EvidenceStore, inventory, read_regular, write_new
from .native_capture import recorded_native_files
from .native_execution import RUNTIME, execute_native
from .native_resources import usage_evidence
from .records import canonical, digest


def native_response(settings, directory, messages, model, auth_path):
    if auth_path is None:
        raise ValueError("native preparation requires --auth-file; credentials are never frozen")
    config = read_regular(RUNTIME / "config.toml").decode()
    config = re.sub(r"^model = .*$", f'model = "{model}"', config, flags=re.M)
    config = re.sub(
        r"^model_reasoning_effort = .*$",
        f'model_reasoning_effort = "{settings.reasoning_effort}"',
        config,
        flags=re.M,
    ).encode()
    write_new(directory / "config.toml", config)
    prompt = (
        "Read input/instructions.txt and input/request.json. Follow the preparation "
        "instructions and write the one JSON response to output/response.json. "
        "The files contain all context for this operation. Use local tools to verify "
        "your JSON if helpful. Finish with a brief status; the response file is authoritative."
    )
    result = execute_native(
        directory / "native",
        "prepare",
        prompt,
        {
            "input/instructions.txt": messages[0].content.encode(),
            "input/request.json": messages[1].content.encode(),
        },
        image=settings.image,
        auth_path=auth_path,
        config=config,
        timeout=settings.timeout_seconds,
    )
    raw = recorded_native_files(EvidenceStore(directory / "native"), result)
    try:
        usage = usage_evidence(raw)
    except ValueError as error:
        usage = {"unavailable": str(error)}
    write_new(
        directory / "native-response.json",
        canonical(
            {
                "result": result,
                "usage": usage,
                "limits": {
                    "native_command_seconds": settings.timeout_seconds,
                    "accepted_output_bytes": settings.max_output_bytes,
                    "hard_token_cap": None,
                    "hard_spend_cap": None,
                    "setup_export_included": False,
                },
            }
        ),
    )
    completion = raw.get("output/response.json")
    if completion is not None:
        write_new(directory / "response.json", completion)
    if result["status"] != "completed" or result.get("rejected_paths"):
        raise ValueError(
            "native preparation failed or exhausted its deadline; see retained attempt"
        )
    if completion is None or len(completion) > settings.max_output_bytes:
        raise ValueError("native preparation response missing or exceeds accepted output byte cap")
    return completion


def archive_native_calls(destination, number, files):
    """Freeze compressed exact native evidence; original files remain in each draft.

    Archives are evidence only and are never extracted or executed by the product.
    Keeping each call in one archive avoids Windows path depth and manifest-count limits.
    """
    prefixes = []
    for root in sorted((destination / "calls" / f"{number:03d}").glob("*/native")):
        entries = inventory(root)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for entry in entries:
                info = zipfile.ZipInfo(entry["path"])
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, read_regular(root / entry["path"]))
        name = f"history/{number:03d}-native-{root.parent.name}.zip"
        files[name] = output.getvalue()
        files[name + ".json"] = canonical(
            {
                "original_path": root.relative_to(destination).as_posix(),
                "archive_sha256": digest(files[name]),
                "files": entries,
            }
        )
        prefixes.append(root.relative_to(destination).as_posix() + "/")
    return tuple(prefixes)

"""An allowlist boundary: only these messages can reach the API-only subject."""

from .records import canonical, digest
from .scoring import CONTRACT
from .study import Case, Materials

SYSTEM = "Complete the supplied synthetic fixture request. Return only the requested JSON."


def common_input(role: str, materials: Materials, case: Case | None = None) -> str:
    if role == "build":
        common = {
            "stage": "build",
            "contract": CONTRACT,
            "brief": materials.brief,
            "development": [item.model_dump(mode="json") for item in materials.development],
            "submission": "Return exactly {files: {path: UTF-8 text}} as valid JSON. "
            "Include SKILL.md and any text resources; no executable code.",
        }
    else:
        if case is None:
            raise ValueError("execution requires its current case")
        common = {
            "stage": "execute",
            "contract": CONTRACT,
            "rows": [row.model_dump() for row in case.rows],
        }
    return canonical(common).decode("utf-8")


def binding(
    trial: dict,
    common: str,
    treatment: dict[str, bytes],
    treatment_id: str,
    study_id: str,
    plan_id: str,
    parent_attempt: str | None = None,
) -> dict:
    treatment_text = {name: data.decode("utf-8") for name, data in sorted(treatment.items())}
    payload = canonical({"common": common, "treatment": treatment_text}).decode("utf-8")
    return {
        "schema_version": 1,
        "trial_id": trial["id"],
        "study_id": study_id,
        "plan_id": plan_id,
        "role": trial["role"],
        "common_sha256": digest(common.encode()),
        "treatment_id": treatment_id,
        "parent_attempt": parent_attempt,
        "profile": "simulated-api-v1",
        "loading": "explicit complete text-package in request",
        "tools": [],
        "subject_filesystem": None,
        "subject_network": None,
        "host_added_context": [],
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": payload}],
    }

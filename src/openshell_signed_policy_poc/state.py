from __future__ import annotations

import json
from pathlib import Path


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {"schema_version": 1, "subjects": {}}
    with state_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_last_sequence(state: dict, subject: str) -> int | None:
    record = state.get("subjects", {}).get(subject)
    if not record:
        return None
    return int(record["last_sequence"])


def get_subject_record(state: dict, subject: str) -> dict | None:
    return state.get("subjects", {}).get(subject)


def update_state(
    state: dict,
    subject: str,
    sequence: int,
    bundle_id: str,
    bundle_sha256: str,
    key_id: str,
    verified_at: str,
) -> dict:
    state.setdefault("subjects", {})
    state["subjects"][subject] = {
        "last_sequence": sequence,
        "bundle_id": bundle_id,
        "bundle_sha256": bundle_sha256,
        "key_id": key_id,
        "verified_at": verified_at,
    }
    return state


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")

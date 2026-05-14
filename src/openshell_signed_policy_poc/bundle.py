from __future__ import annotations

import base64
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Dict


REQUIRED_BUNDLE_FILES = (
    "metadata.json",
    "policy.yaml",
    "manifest.json",
    "signature.json",
)


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signature_b64(signature: bytes) -> str:
    return base64.b64encode(signature).decode("ascii")


def signature_from_b64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def build_manifest(named_payloads: Dict[str, bytes]) -> dict:
    return {
        "schema_version": 1,
        "files": {
            name: {
                "sha256": sha256_hex(data),
                "size": len(data),
            }
            for name, data in sorted(named_payloads.items())
        },
    }


def compose_signed_payload(metadata: dict, manifest: dict) -> bytes:
    return canonical_json_bytes(
        {
            "manifest": manifest,
            "metadata": metadata,
        }
    )


def load_bundle(bundle_path: Path) -> Dict[str, bytes]:
    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = sorted(archive.namelist())
        expected = sorted(REQUIRED_BUNDLE_FILES)
        if names != expected:
            raise ValueError(
                f"bundle contents must be exactly {expected}, found {names}"
            )

        return {name: archive.read(name) for name in names}


def write_bundle(bundle_path: Path, files: Dict[str, bytes]) -> None:
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED_BUNDLE_FILES:
            archive.writestr(name, files[name])


def load_json_bytes(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))

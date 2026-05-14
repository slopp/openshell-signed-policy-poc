from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bundle import (
    compose_signed_payload,
    load_bundle,
    load_json_bytes,
    sha256_hex,
    signature_from_b64,
)
from .crypto import compute_key_id, verify_signature
from .state import get_last_sequence, get_subject_record, load_state, save_state, update_state
from .timeutil import isoformat_z, now_utc, parse_timestamp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify a signed policy bundle.")
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--trusted-key", required=True, type=Path)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--revocation-file", type=Path)
    parser.add_argument("--no-state-update", action="store_true")
    return parser


def _assert_manifest_entry(manifest: dict, name: str, content: bytes) -> None:
    files = manifest.get("files", {})
    entry = files.get(name)
    if not entry:
        raise ValueError(f"manifest is missing entry for {name}")

    if entry.get("sha256") != sha256_hex(content):
        raise ValueError(f"manifest digest mismatch for {name}")

    if int(entry.get("size", -1)) != len(content):
        raise ValueError(f"manifest size mismatch for {name}")


def main() -> int:
    args = build_parser().parse_args()

    bundle_path = args.bundle_dir / "bundle.ospb"
    bundle = load_bundle(bundle_path)
    metadata = load_json_bytes(bundle["metadata.json"])
    manifest = load_json_bytes(bundle["manifest.json"])
    signature_json = load_json_bytes(bundle["signature.json"])

    _assert_manifest_entry(manifest, "metadata.json", bundle["metadata.json"])
    _assert_manifest_entry(manifest, "policy.yaml", bundle["policy.yaml"])

    if signature_json.get("algorithm") != "ed25519-openssl-pkeyutl":
        raise SystemExit(
            f"unsupported signature algorithm: {signature_json.get('algorithm')}"
        )

    if metadata.get("subject") != args.subject:
        raise SystemExit(f"subject mismatch: expected {args.subject}, got {metadata.get('subject')}")

    expires_at = parse_timestamp(metadata["expires_at"])
    if expires_at <= now_utc():
        raise SystemExit(f"bundle expired at {metadata['expires_at']}")

    signature_key_id = signature_json["key_id"]
    public_key_pem = args.trusted_key.read_bytes()
    computed_key_id = compute_key_id(public_key_pem)
    if computed_key_id != signature_key_id:
        raise SystemExit(
            f"trusted key mismatch: bundle says {signature_key_id}, computed {computed_key_id}"
        )

    if metadata.get("signing_key_id") != signature_key_id:
        raise SystemExit("metadata signing_key_id does not match signature key_id")

    signed_payload = compose_signed_payload(metadata, manifest)
    if signature_json.get("payload_sha256") != sha256_hex(signed_payload):
        raise SystemExit("signed payload digest mismatch")

    signature = signature_from_b64(signature_json["signature_b64"])
    if not verify_signature(public_key_pem, signed_payload, signature):
        raise SystemExit("signature verification failed")

    if args.revocation_file:
        with args.revocation_file.open("r", encoding="utf-8") as handle:
            revoked = json.load(handle)
        if signature_key_id in set(revoked.get("revoked_key_ids", [])):
            raise SystemExit(f"signing key is revoked: {signature_key_id}")

    state_file = args.state_dir / "verification-state.json"
    state = load_state(state_file)
    sequence = int(metadata["sequence"])
    last_sequence = get_last_sequence(state, args.subject)
    bundle_sha256 = sha256_hex(bundle_path.read_bytes())
    policy_sha256 = sha256_hex(bundle["policy.yaml"])
    subject_record = get_subject_record(state, args.subject) or {}
    last_bundle_sha256 = subject_record.get("bundle_sha256")
    if last_sequence is not None:
        if sequence < last_sequence:
            raise SystemExit(
                f"sequence rollback detected: last={last_sequence}, incoming={sequence}"
            )
        if sequence == last_sequence and last_bundle_sha256 != bundle_sha256:
            raise SystemExit(
                "sequence collision detected: identical sequence with different bundle content"
            )

    verified_at = isoformat_z(now_utc())
    extract_dir = args.state_dir / "verified-bundles" / metadata["bundle_id"]
    extract_dir.mkdir(parents=True, exist_ok=True)
    policy_path = extract_dir / "policy.yaml"
    policy_path.write_bytes(bundle["policy.yaml"])

    if not args.no_state_update:
        updated = update_state(
            state,
            subject=args.subject,
            sequence=sequence,
            bundle_id=metadata["bundle_id"],
            bundle_sha256=bundle_sha256,
            key_id=signature_key_id,
            verified_at=verified_at,
        )
        save_state(state_file, updated)

    print(
        json.dumps(
            {
                "ok": True,
                "bundle_id": metadata["bundle_id"],
                "bundle_sha256": bundle_sha256,
                "subject": args.subject,
                "issuer": metadata.get("issuer", ""),
                "policy_name": metadata.get("policy_name", ""),
                "policy_path": str(policy_path),
                "policy_sha256": policy_sha256,
                "sequence": sequence,
                "key_id": signature_key_id,
                "verified_at": verified_at,
                "expires_at": metadata["expires_at"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

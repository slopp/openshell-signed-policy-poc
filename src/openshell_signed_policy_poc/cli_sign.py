from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from .bundle import (
    build_manifest,
    compose_signed_payload,
    pretty_json_bytes,
    sha256_hex,
    signature_b64,
    write_bundle,
)
from .crypto import compute_key_id, read_public_key, sign_payload
from .timeutil import isoformat_z, now_utc, parse_timestamp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and sign a policy bundle.")
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--bundle-out", required=True, type=Path)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--policy-name", required=True)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--sequence", required=True, type=int)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--bundle-id", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.sequence < 1:
        raise SystemExit("sequence must be >= 1")

    issued_at = now_utc()
    expires_at = parse_timestamp(args.expires_at)
    if expires_at <= issued_at:
        raise SystemExit("expires-at must be in the future")

    public_key_pem = read_public_key(args.public_key)
    key_id = compute_key_id(public_key_pem)

    metadata = {
        "schema_version": 1,
        "bundle_id": args.bundle_id or str(uuid.uuid4()),
        "subject": args.subject,
        "policy_name": args.policy_name,
        "issuer": args.issuer,
        "sequence": args.sequence,
        "issued_at": isoformat_z(issued_at),
        "expires_at": isoformat_z(expires_at),
        "signing_key_id": key_id,
    }

    policy_bytes = args.policy.read_bytes()
    metadata_bytes = pretty_json_bytes(metadata)
    manifest = build_manifest(
        {
            "metadata.json": metadata_bytes,
            "policy.yaml": policy_bytes,
        }
    )
    manifest_bytes = pretty_json_bytes(manifest)

    signed_payload = compose_signed_payload(metadata, manifest)
    signature = sign_payload(args.private_key, signed_payload)
    signature_json = {
        "schema_version": 1,
        "algorithm": "ed25519-openssl-pkeyutl",
        "key_id": key_id,
        "signed_at": isoformat_z(now_utc()),
        "payload_sha256": sha256_hex(signed_payload),
        "signature_b64": signature_b64(signature),
    }
    signature_bytes = pretty_json_bytes(signature_json)

    write_bundle(
        args.bundle_out,
        {
            "metadata.json": metadata_bytes,
            "policy.yaml": policy_bytes,
            "manifest.json": manifest_bytes,
            "signature.json": signature_bytes,
        },
    )

    print(f"bundle={args.bundle_out}")
    print(f"bundle_id={metadata['bundle_id']}")
    print(f"subject={args.subject}")
    print(f"policy_name={args.policy_name}")
    print(f"sequence={args.sequence}")
    print(f"signing_key_id={key_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

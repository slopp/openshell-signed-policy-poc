from __future__ import annotations

import argparse
import json
from pathlib import Path

from .crypto import compute_key_id, generate_keypair, read_public_key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a signing keypair.")
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--label", default="openshell-policy-signer")
    parser.add_argument("--trust-store-out", type=Path)
    parser.add_argument("--allow-subject", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()

    generate_keypair(args.private_key, args.public_key)
    public_key_pem = read_public_key(args.public_key)
    key_id = compute_key_id(public_key_pem)

    if args.trust_store_out:
        args.trust_store_out.parent.mkdir(parents=True, exist_ok=True)
        trust_store = {
            "schema_version": 1,
            "keys": [
                {
                    "key_id": key_id,
                    "label": args.label,
                    "public_key_pem": public_key_pem.decode("utf-8"),
                    "allowed_subjects": sorted(set(args.allow_subject)),
                }
            ],
        }
        with args.trust_store_out.open("w", encoding="utf-8") as handle:
            json.dump(trust_store, handle, indent=2, sort_keys=True)
            handle.write("\n")

    print(f"key_id={key_id}")
    print(f"private_key={args.private_key}")
    print(f"public_key={args.public_key}")
    if args.trust_store_out:
        print(f"trust_store={args.trust_store_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

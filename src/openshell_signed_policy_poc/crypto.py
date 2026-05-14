from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path


def _run_openssl(args: list[str]) -> bytes:
    completed = subprocess.run(
        ["openssl", *args],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def generate_keypair(private_key_path: Path, public_key_path: Path) -> None:
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private_key_path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "openssl",
            "pkey",
            "-in",
            str(private_key_path),
            "-pubout",
            "-out",
            str(public_key_path),
        ],
        check=True,
        capture_output=True,
    )


def read_public_key(public_key_path: Path) -> bytes:
    return public_key_path.read_bytes()


def public_key_to_der(public_key_pem: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        pem_path = Path(tmpdir) / "public.pem"
        pem_path.write_bytes(public_key_pem)
        return _run_openssl(
            ["pkey", "-pubin", "-in", str(pem_path), "-outform", "DER"]
        )


def compute_key_id(public_key_pem: bytes) -> str:
    digest = hashlib.sha256(public_key_to_der(public_key_pem)).hexdigest()
    return f"ed25519:{digest[:16]}"


def sign_payload(private_key_path: Path, payload: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        payload_path = Path(tmpdir) / "payload.bin"
        signature_path = Path(tmpdir) / "signature.bin"
        payload_path.write_bytes(payload)
        subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                str(private_key_path),
                "-in",
                str(payload_path),
                "-out",
                str(signature_path),
            ],
            check=True,
            capture_output=True,
        )
        return signature_path.read_bytes()


def verify_signature(public_key_pem: bytes, payload: bytes, signature: bytes) -> bool:
    with tempfile.TemporaryDirectory() as tmpdir:
        public_key_path = Path(tmpdir) / "public.pem"
        payload_path = Path(tmpdir) / "payload.bin"
        signature_path = Path(tmpdir) / "signature.bin"

        public_key_path.write_bytes(public_key_pem)
        payload_path.write_bytes(payload)
        signature_path.write_bytes(signature)

        completed = subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-verify",
                "-rawin",
                "-pubin",
                "-inkey",
                str(public_key_path),
                "-in",
                str(payload_path),
                "-sigfile",
                str(signature_path),
            ],
            capture_output=True,
        )
        return completed.returncode == 0

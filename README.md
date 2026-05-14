# OpenShell Signed Policy POC

This repository is a minimal MVP for shipping signed OpenShell policy bundles. It provides Python CLIs for key generation, bundle signing, and host-side verification with rollback protection, and it is shaped to plug into an OpenShell gateway mode that requires verified host-managed policy.

Paired OpenShell gateway branch / draft PR:

- https://github.com/slopp/OpenShell/pull/1

## What it includes

- `osp-keygen`: generates an Ed25519 keypair.
- `osp-sign`: builds a `.ospb` zip bundle containing `metadata.json`, `policy.yaml`, `manifest.json`, and `signature.json`.
- `osp-verify`: validates bundle integrity, signature validity, trusted signer, expiry, subject binding, and sequence monotonicity via a local state directory and emits JSON the OpenShell gateway can consume.
- Example policy and walkthrough for `nemoclaw-community / personal-community-sentiment-triage`.
- `scripts/mock_fleet_install.sh`: copies a bundle into a mock host path and runs verification there.

## Bundle format

Each bundle is a zip archive with these required entries:

- `metadata.json`: bundle identity and deployment constraints.
- `policy.yaml`: the policy payload.
- `manifest.json`: SHA-256 digests and byte sizes for `metadata.json` and `policy.json`.
- `signature.json`: signer key id, payload digest, and detached Ed25519 signature.

The signature covers the canonical JSON payload:

```json
{
  "manifest": { "...": "..." },
  "metadata": { "...": "..." }
}
```

The policy is protected indirectly through the signed manifest.

## Verification model

Verification is intentionally strict:

- The signer key id in `signature.json` must match the trusted public key.
- The signature must verify against the trusted public key.
- `metadata.subject` must match `--subject`.
- `metadata.expires_at` must still be in the future.
- `metadata.sequence` must be greater than the last accepted sequence for that subject in the state file.

The state file is local to the host and prevents replaying an older valid bundle after a newer one has already been accepted.

## Quickstart

Use the repo-local wrapper scripts:

```bash
scripts/osp-keygen --help
scripts/osp-sign --help
scripts/osp-verify --help
```

Full demo commands are in [docs/demo.md](docs/demo.md).

## Omnistation proof of life

This POC was validated end to end on Omnistation host `omni-lsn-mmcth` against
the real `nemoclaw-community/examples/personal-community-sentiment-triage`
OpenShell policy.

The exercised flow was:

1. Generate a mock signer keypair.
2. Sign the real NemoClaw `policy.yaml` into a `.ospb` bundle.
3. Copy the bundle and trusted public key to the host as a stand-in for Fleet.
4. Run `osp-verify` on-host and point a patched OpenShell gateway at:
   - the current bundle directory
   - the trusted public key
   - the verifier executable
   - a local verification state directory
5. Create the NemoClaw sandbox without supplying `--policy`, so the sandbox
   must fetch policy from the verified host bundle.
6. Confirm host-side tampering is rejected:
   - `openshell policy set`
   - `openshell policy delete`
   - `openshell rule approve* / reject*`
   - `openshell sandbox create --policy ...`

See [docs/demo.md](docs/demo.md) for the local signing flow and
[docs/omnistation-mmcth.md](docs/omnistation-mmcth.md) for the host-side
validation runbook.

## How this maps to a real implementation

This repository deliberately mocks two production roles:

- `3S` or another signing authority:
  - In this POC, `osp-keygen` and `osp-sign` stand in for the real signer.
  - In production, signing should happen in a controlled service or CI path,
    not on an operator laptop.
- `Fleet` or another host configuration system:
  - In this POC, a human copies the bundle to the host or runs
    `scripts/mock_fleet_install.sh`.
  - In production, a fleet system would place the bundle, trusted key material,
    and immutable OpenShell config on the host.

The OpenShell integration is intentionally narrow:

- the gateway does not implement PKI itself
- it shells out to a verifier and consumes a machine-readable verification
  result
- signed mode disables mutable policy operations and requires sandboxes to use
  the verified host bundle

That keeps the MVP aligned with a future standalone verifier architecture while
still enforcing the part OpenShell can enforce today.

# OpenShell Signed Policy POC

This repository is a minimal MVP for shipping signed OpenShell policy bundles.
It provides Python CLIs for key generation, bundle signing, and host-side
verification with rollback protection. It is designed to pair with a patched
OpenShell gateway mode that requires verified host-managed policy.

Paired OpenShell gateway branch / draft PR:

- https://github.com/slopp/OpenShell/pull/1

This repo does not enforce signed mode by itself. Enforcement happens in the
paired OpenShell gateway branch, which adds `signed_policy_required` mode and
uses this repo's verifier as an external trust decision.

## What it includes

- `osp-keygen`: generates an Ed25519 keypair.
- `osp-sign`: builds a `.ospb` zip bundle containing `metadata.json`,
  `policy.yaml`, `manifest.json`, and `signature.json`.
- `osp-verify`: validates bundle integrity, signature validity, trusted signer,
  expiry, subject binding, and sequence monotonicity via a local state
  directory and emits JSON the OpenShell gateway can consume.
- `examples/weather-hermes`: a small Hermes sandbox and policy that allows only:
  - `curl`
  - `python3`
  - `hermes`
  to read `https://wttr.in`.
- `scripts/mock_fleet_install.sh`: copies a bundle into a mock target-host
  layout and runs verification there.

## Bundle format

Each bundle is a zip archive with these required entries:

- `metadata.json`: bundle identity and deployment constraints.
- `policy.yaml`: the policy payload.
- `manifest.json`: SHA-256 digests and byte sizes for `metadata.json` and
  `policy.yaml`.
- `signature.json`: signer key id, payload digest, and detached Ed25519
  signature.

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
- `metadata.sequence` must be greater than the last accepted sequence for that
  subject in the state file.

The state file is local to the target host and prevents replaying an older
valid bundle after a newer one has already been accepted.

## Roles in the POC

The POC uses two explicit roles:

- `central signer host`
  - holds the private signing key
  - signs `policy.yaml` into a `.ospb` bundle
  - stands in for 3S or another controlled signing service
- `target host`
  - runs the patched OpenShell gateway
  - stores the signed bundle, trusted public key, and verifier state
  - stands in for a Fleet-managed Omnistation or workstation

Fleet is mocked by copying files from the central signer host to the target
host. In a real deployment, Fleet would place:

- the signed bundle
- the trusted public key
- the verifier
- the immutable gateway configuration that turns on signed-only mode

## How signed mode is enforced

The standalone verifier in this repo is only one half of the MVP. The actual
enforcement point is the patched OpenShell gateway in the paired fork/PR.

On the target host, the gateway is launched with these settings:

- `OPENSHELL_SIGNED_POLICY_REQUIRED=true`
- `OPENSHELL_SIGNED_POLICY_BUNDLE_DIR=<target-host-root>/current`
- `OPENSHELL_SIGNED_POLICY_VERIFIER=<verifier-repo>/scripts/osp-verify`
- `OPENSHELL_SIGNED_POLICY_TRUSTED_KEY=<target-host-root>/keys/weather-signer.pub.pem`
- `OPENSHELL_SIGNED_POLICY_SUBJECT=omnistation-prod/weather-hermes`
- `OPENSHELL_SIGNED_POLICY_STATE_DIR=<target-host-root>/state`

When those are set, the patched gateway:

- shells out to `osp-verify`
- serves only the verified host-managed policy bundle to sandboxes
- rejects mutable host-side policy operations:
  - `openshell policy set`
  - `openshell policy delete`
  - draft rule approval / rejection flows
- rejects sandbox creation when inline `--policy` is supplied

That is the core verified-only behavior. The verifier decides whether the
bundle is valid; the gateway decides whether unverified or mutable policy paths
are allowed.

## Quickstart

Use the repo-local wrapper scripts:

```bash
scripts/osp-keygen --help
scripts/osp-sign --help
scripts/osp-verify --help
```

Full walkthrough:

- central signer host: [docs/demo.md](docs/demo.md)
- target host / signed gateway: [docs/target-host.md](docs/target-host.md)

## MVP validation flow

The current proof-of-life uses `examples/weather-hermes` and validates the same
behavior twice:

1. unsigned sandbox on a normal gateway
2. signed bundle on a signed-only gateway

The exercised flow is:

1. Build a minimal Hermes sandbox from `examples/weather-hermes/Dockerfile`.
2. Apply `examples/weather-hermes/policy.yaml` directly and prove:
   - `curl https://wttr.in/?format=3` works
   - Python HTTPS fetch to `wttr.in` works
   - unrelated outbound traffic such as `https://api.github.com/zen` is denied
   - `hermes chat` can answer a weather prompt when told to use `curl`
3. Sign the same `policy.yaml` into a `.ospb` bundle on the central signer
   host.
4. Copy the bundle and trusted public key to the target host as a stand-in for
   Fleet.
5. Launch the patched OpenShell gateway on the target host in
   `signed_policy_required` mode.
6. Create the same sandbox without supplying `--policy`, so it must fetch
   policy from the verified host bundle.
7. Repeat the allow/deny/Hermes checks.
8. Confirm host-side tampering is rejected:
   - `openshell policy delete --global`
   - `openshell rule approve-all`
   - `openshell sandbox create --policy ...`

This flow was validated on a live Omnistation target host, but the commands in
this repo are written with relative paths so the setup can be reviewed and
repeated elsewhere.

## How this maps to a real implementation

This repository deliberately mocks two production roles:

- `3S` or another signing authority:
  - In this POC, `osp-keygen` and `osp-sign` stand in for the real signer.
  - In production, signing should happen in a controlled service or CI path,
    not on an operator laptop.
- `Fleet` or another host configuration system:
  - In this POC, a human copies the bundle to the target host or runs
    `scripts/mock_fleet_install.sh`.
  - In production, Fleet would place the bundle, trusted key material,
    verifier path, and immutable OpenShell gateway config on the host.

The OpenShell integration is intentionally narrow:

- the gateway does not implement PKI itself
- it shells out to a verifier and consumes a machine-readable verification
  result
- signed mode disables mutable policy operations and requires sandboxes to use
  the verified host bundle

That keeps the MVP aligned with a future standalone verifier architecture while
still enforcing the part OpenShell can enforce today.

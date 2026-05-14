# Omnistation runbook: `omni-lsn-mmcth`

This note captures the concrete host-side proof of life for the signed-policy
MVP using the real NemoClaw demo on `omni-lsn-mmcth`.

## What was deployed

- Standalone verifier repo:
  - `/home/slopp/work/openshell-signed-policy-poc`
- Patched OpenShell tree:
  - `/home/slopp/work/OpenShell-signed-policy`
- Signed bundle root on host:
  - `/home/slopp/poc-signed-policy-mmcth`
- Signed gateway endpoint:
  - `http://127.0.0.1:19080`

The signed bundle used the real NemoClaw example policy:

- source policy:
  - `/home/slopp/work/omnistation-investigation/nemoclaw-community/examples/personal-community-sentiment-triage/policy.yaml`
- verified subject:
  - `omnistation-prod/nemoclaw-personal-community-sentiment-triage`

## Gateway configuration shape

The patched gateway was started with the normal Docker driver plus these
signed-policy settings:

- `OPENSHELL_SIGNED_POLICY_REQUIRED=true`
- `OPENSHELL_SIGNED_POLICY_BUNDLE_DIR=/home/slopp/poc-signed-policy-mmcth/current`
- `OPENSHELL_SIGNED_POLICY_VERIFIER=/home/slopp/work/openshell-signed-policy-poc/scripts/osp-verify`
- `OPENSHELL_SIGNED_POLICY_TRUSTED_KEY=/home/slopp/poc-signed-policy-mmcth/keys/demo-signer.pub.pem`
- `OPENSHELL_SIGNED_POLICY_SUBJECT=omnistation-prod/nemoclaw-personal-community-sentiment-triage`
- `OPENSHELL_SIGNED_POLICY_STATE_DIR=/home/slopp/poc-signed-policy-mmcth/state`

## What was proven

The following behaviors were observed on the signed gateway:

1. `policy get --global` returned the signed-bundle-backed policy hash.
2. `policy delete --global` was rejected with `FailedPrecondition`.
3. `rule approve-all` was rejected with `FailedPrecondition`.
4. `sandbox create --policy ...` was rejected with `FailedPrecondition`.
5. A NemoClaw sandbox created without `--policy` reached `Ready`.
6. The live sandbox logs showed:
   - `Fetching sandbox policy via gRPC`
   - provider env fetched from gateway
   - inference route bundle fetched from gateway
   - traffic to `host.openshell.internal:19080`

That is the core MVP claim:

- host receives signed bundle
- verifier approves bundle
- OpenShell serves only verified policy
- host-side policy mutation is blocked
- NemoClaw runs from the verified policy path

## Rough edges noted

- The patched CLI/gateway path still emitted:
  - `gateway returned invalid SSH session response: connect_path is empty`
  during sandbox create, even though the sandbox was successfully created and
  became `Ready`.
- The example's stock `03-sandbox.sh` assumes mutable policy operations and
  needs a signed-mode variant that:
  - omits `--policy` at create time
  - omits follow-up `openshell policy set --wait`

Those are packaging/UX issues, not blockers to the signed-policy enforcement
model itself.

# Demo: NemoClaw / Omnistation signed policy bundle

This walkthrough signs the existing demo policy at:

`/Users/slopp/work/nemoclaw-community/examples/personal-community-sentiment-triage/policy.yaml`

## 1. Generate a signing keypair

```bash
mkdir -p demo-out/keys demo-out/dist demo-out/state

PYTHONPATH=src python3 -m openshell_signed_policy_poc.cli_keygen \
  --private-key demo-out/keys/demo-signer.pem \
  --public-key demo-out/keys/demo-signer.pub.pem
```

## 2. Build a signed bundle

```bash
PYTHONPATH=src python3 -m openshell_signed_policy_poc.cli_sign \
  --policy /Users/slopp/work/nemoclaw-community/examples/personal-community-sentiment-triage/policy.yaml \
  --private-key demo-out/keys/demo-signer.pem \
  --public-key demo-out/keys/demo-signer.pub.pem \
  --bundle-out demo-out/dist/nemoclaw-community-personal-community-sentiment-triage-seq1.ospb \
  --subject omnistation-prod/nemoclaw-personal-community-sentiment-triage \
  --policy-name personal-community-sentiment-triage \
  --issuer 3s-mock \
  --sequence 1 \
  --expires-at 2026-12-31T23:59:59Z
```

## 3. Mock Fleet installs and verifies the bundle

```bash
scripts/mock_fleet_install.sh \
  demo-out/dist/nemoclaw-community-personal-community-sentiment-triage-seq1.ospb \
  demo-out/keys/demo-signer.pub.pem \
  omnistation-prod/nemoclaw-personal-community-sentiment-triage \
  /tmp/mock-host-a
```

That script lays down a host-like structure:

- `/tmp/mock-host-a/var/lib/openshell/policy-bundles/current/bundle.ospb`
- `/tmp/mock-host-a/var/lib/openshell/state/verification-state.json`
- `/tmp/mock-host-a/var/lib/openshell/state/verified-bundles/<bundle-id>/policy.yaml`

## 4. Verify directly with the machine-readable contract

```bash
PYTHONPATH=src python3 -m openshell_signed_policy_poc.cli_verify \
  --bundle-dir /tmp/mock-host-a/var/lib/openshell/policy-bundles/current \
  --trusted-key demo-out/keys/demo-signer.pub.pem \
  --subject omnistation-prod/nemoclaw-personal-community-sentiment-triage \
  --state-dir /tmp/mock-host-a/var/lib/openshell/state \
  --no-state-update
```

The verifier emits JSON that the patched OpenShell gateway consumes, including:

- `policy_path`
- `policy_sha256`
- `sequence`
- `subject`
- `key_id`

## 5. Demonstrate rollback prevention

Re-running verification without `--no-state-update` against the same sequence should fail once the state file already records that sequence. A higher sequence should succeed.

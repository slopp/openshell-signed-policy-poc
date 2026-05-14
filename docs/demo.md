# Central signer host walkthrough

This walkthrough covers the signing side of the MVP from a central signer host.
It uses the small weather/Hermes policy in:

`examples/weather-hermes/policy.yaml`

## 1. Generate a signing keypair

```bash
mkdir -p demo-out/keys demo-out/dist demo-out/state

PYTHONPATH=src python3 -m openshell_signed_policy_poc.cli_keygen \
  --private-key demo-out/keys/weather-signer.pem \
  --public-key demo-out/keys/weather-signer.pub.pem
```

## 2. Build a signed bundle

```bash
PYTHONPATH=src python3 -m openshell_signed_policy_poc.cli_sign \
  --policy examples/weather-hermes/policy.yaml \
  --private-key demo-out/keys/weather-signer.pem \
  --public-key demo-out/keys/weather-signer.pub.pem \
  --bundle-out demo-out/dist/weather-hermes-seq1.ospb \
  --subject omnistation-prod/weather-hermes \
  --policy-name weather-hermes \
  --issuer 3s-mock \
  --sequence 1 \
  --expires-at 2026-12-31T23:59:59Z
```

## 3. Mock Fleet installs and verifies the bundle into a target-host layout

```bash
scripts/mock_fleet_install.sh \
  demo-out/dist/weather-hermes-seq1.ospb \
  demo-out/keys/weather-signer.pub.pem \
  omnistation-prod/weather-hermes \
  ./mock-target-host
```

That script lays down a host-like structure:

- `./mock-target-host/var/lib/openshell/policy-bundles/current/bundle.ospb`
- `./mock-target-host/var/lib/openshell/state/verification-state.json`
- `./mock-target-host/var/lib/openshell/state/verified-bundles/<bundle-id>/policy.yaml`

## 4. Verify directly with the machine-readable contract

```bash
PYTHONPATH=src python3 -m openshell_signed_policy_poc.cli_verify \
  --bundle-dir ./mock-target-host/var/lib/openshell/policy-bundles/current \
  --trusted-key demo-out/keys/weather-signer.pub.pem \
  --subject omnistation-prod/weather-hermes \
  --state-dir ./mock-target-host/var/lib/openshell/state \
  --no-state-update
```

The verifier emits JSON that the patched OpenShell gateway consumes, including:

- `policy_path`
- `policy_sha256`
- `sequence`
- `subject`
- `key_id`

## 5. Demonstrate rollback protection

Run verification once without `--no-state-update`, then try the same sequence
again:

```bash
PYTHONPATH=src python3 -m openshell_signed_policy_poc.cli_verify \
  --bundle-dir ./mock-target-host/var/lib/openshell/policy-bundles/current \
  --trusted-key demo-out/keys/weather-signer.pub.pem \
  --subject omnistation-prod/weather-hermes \
  --state-dir ./mock-target-host/var/lib/openshell/state
```

The second attempt with the same sequence should fail because the local state
already records that sequence for the subject.

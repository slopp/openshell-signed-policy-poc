# Target host walkthrough

This walkthrough covers the enforcement side of the MVP from a target host that
runs the patched OpenShell gateway.

The central signer host is assumed to have already produced:

- `./dist/weather-hermes-seq1.ospb`
- `./keys/weather-signer.pub.pem`

The target host is assumed to have:

- a checkout of this verifier repo at `<verifier-repo>/`
- a build of the paired patched OpenShell gateway at `<openshell-build>/`

## 1. Prepare target-host directories

```bash
mkdir -p ./signed-weather/current ./signed-weather/keys ./signed-weather/state
```

## 2. Mock Fleet by copying the signed bundle and trusted key

Copy the central signer host artifacts into the target-host layout:

- `./signed-weather/current/bundle.ospb`
- `./signed-weather/keys/weather-signer.pub.pem`

In the POC, this copy is manual. In a real deployment, Fleet would place these
files on-host.

## 3. Launch the signed-only gateway

```bash
OPENSHELL_SIGNED_POLICY_REQUIRED=true \
OPENSHELL_SIGNED_POLICY_BUNDLE_DIR=./signed-weather/current \
OPENSHELL_SIGNED_POLICY_VERIFIER=<verifier-repo>/scripts/osp-verify \
OPENSHELL_SIGNED_POLICY_TRUSTED_KEY=./signed-weather/keys/weather-signer.pub.pem \
OPENSHELL_SIGNED_POLICY_SUBJECT=omnistation-prod/weather-hermes \
OPENSHELL_SIGNED_POLICY_STATE_DIR=./signed-weather/state \
<openshell-build>/openshell-gateway \
  --drivers docker \
  --disable-tls \
  --port 19080 \
  --docker-network-name openshell-signed \
  --sandbox-namespace docker-signed \
  --sandbox-image ghcr.io/nvidia/openshell-community/sandboxes/base:latest \
  --sandbox-image-pull-policy IfNotPresent \
  --grpc-endpoint http://host.openshell.internal:19080
```

The exact non-policy flags may vary with your local OpenShell installation. The
important part for the POC is that the gateway is started with the
`OPENSHELL_SIGNED_POLICY_*` settings above.

## 4. Configure the gateway inference route

If Hermes will use `inference.local`, configure the signed gateway with the
same inference provider and model that a normal working gateway uses.

Example:

```bash
export COMPATIBLE_API_KEY='<provider-api-key>'
export NEMOCLAW_ENDPOINT_URL='https://integrate.api.nvidia.com/v1'

openshell --gateway-endpoint http://127.0.0.1:19080 provider create \
  --name compatible-endpoint \
  --type openai \
  --credential OPENAI_API_KEY="$COMPATIBLE_API_KEY" \
  --config OPENAI_BASE_URL="$NEMOCLAW_ENDPOINT_URL"

openshell --gateway-endpoint http://127.0.0.1:19080 inference set \
  --provider compatible-endpoint \
  --model nvidia/nemotron-3-super-120b-a12b \
  --no-verify
```

Without this step, `hermes chat` may fail before it ever reaches the sandboxed
`curl` call because `inference.local` has no gateway route behind it.

## 5. Create the signed sandbox without inline policy

```bash
openshell --gateway-endpoint http://127.0.0.1:19080 sandbox create \
  --name weather-signed \
  --from examples/weather-hermes/Dockerfile \
  -- /bin/true
```

Do not pass `--policy`. In signed mode, the sandbox must fetch policy from the
verified host bundle.

## 6. Validate allow / deny behavior

Allowed weather access:

```bash
openshell --gateway-endpoint http://127.0.0.1:19080 sandbox exec -n weather-signed -- \
  bash -lc "curl -s https://wttr.in/?format=3"
```

Allowed Python HTTPS fetch:

```bash
openshell --gateway-endpoint http://127.0.0.1:19080 sandbox exec -n weather-signed -- \
  bash -lc 'env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH /usr/bin/python3.13 -c "import urllib.request; print(urllib.request.urlopen(\"https://wttr.in/?format=3\", timeout=20).read().decode())"'
```

Denied unrelated egress:

```bash
openshell --gateway-endpoint http://127.0.0.1:19080 sandbox exec -n weather-signed -- \
  bash -lc "curl -sS https://api.github.com/zen"
```

Hermes using the policy-approved path:

```bash
openshell --gateway-endpoint http://127.0.0.1:19080 sandbox exec -n weather-signed -- \
  bash -lc 'env HOME=/sandbox HERMES_HOME=/sandbox/.hermes hermes chat -q "Use curl to fetch https://wttr.in/?format=3 and reply with exactly the returned text and nothing else." -t terminal --yolo -Q'
```

## 7. Confirm tamper resistance

These operations should be rejected by the signed gateway:

```bash
openshell --gateway-endpoint http://127.0.0.1:19080 policy delete --global --yes
openshell --gateway-endpoint http://127.0.0.1:19080 rule approve-all weather-signed
openshell --gateway-endpoint http://127.0.0.1:19080 sandbox create \
  --name weather-inline \
  --from examples/weather-hermes/Dockerfile \
  --policy examples/weather-hermes/policy.yaml \
  -- /bin/true
```

Expected outcome:

- mutable global policy update is rejected
- bulk draft approval is rejected
- inline sandbox policy is rejected

## What this proves

If all of the above succeeds, the target host is enforcing the full MVP:

- OpenShell accepts only a verified host-managed policy bundle
- the same policy behavior matches the unsigned control case
- Hermes still functions inside the constrained sandbox
- host-side policy tampering paths are blocked

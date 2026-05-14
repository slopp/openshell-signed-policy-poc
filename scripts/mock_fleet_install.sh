#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <bundle.ospb> <trusted-key.pem> <expected-subject> <host-root>" >&2
  exit 2
fi

BUNDLE_PATH=$1
TRUSTED_KEY=$2
EXPECTED_SUBJECT=$3
HOST_ROOT=$4

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
HOST_BUNDLE_DIR="$HOST_ROOT/var/lib/openshell/policy-bundles/current"
HOST_STATE_DIR="$HOST_ROOT/var/lib/openshell/state"
HOST_BUNDLE_PATH="$HOST_BUNDLE_DIR/bundle.ospb"

mkdir -p "$HOST_BUNDLE_DIR" "$HOST_STATE_DIR"
cp "$BUNDLE_PATH" "$HOST_BUNDLE_PATH"

PYTHONPATH="$REPO_ROOT/src" python3 -m openshell_signed_policy_poc.cli_verify \
  --bundle-dir "$HOST_BUNDLE_DIR" \
  --trusted-key "$TRUSTED_KEY" \
  --subject "$EXPECTED_SUBJECT" \
  --state-dir "$HOST_STATE_DIR"

echo "bundle installed at $HOST_BUNDLE_PATH"

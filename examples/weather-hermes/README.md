# Weather Hermes example

This example is the smallest end-to-end target for the signed-policy MVP.

It uses:

- a minimal Hermes image with a baked config that points at `inference.local`
- a single OpenShell network policy that allows:
  - `curl`
  - `python3`
  - `hermes`
  to read from `https://wttr.in`

Everything else remains default-deny at the network layer.

The intended validation flow is:

1. Create an unsigned sandbox with `policy.yaml`.
2. Prove:
   - `curl https://wttr.in/?format=3` works
   - a Python HTTPS fetch to `wttr.in` works
   - an unrelated outbound request such as `https://api.github.com/zen` is denied
   - `hermes chat -q ...` can answer a weather question when explicitly told to use `curl`
3. Sign the same `policy.yaml`.
4. Install the signed bundle on the target host.
5. Recreate the sandbox through the signed-policy gateway without supplying `--policy`.
6. Repeat the same validation checks and verify host-side policy mutation is rejected.

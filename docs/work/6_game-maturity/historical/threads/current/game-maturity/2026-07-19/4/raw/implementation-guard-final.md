One HIGH finding remains:

- npm configuration can still execute caller-selected Node code before the guard starts. Live probe:

  `npm.cmd test --ignore-scripts "--node-options=--import=data:text/javascript,console.log('NODE_OPTIONS_BYPASS_SENTINEL')" -- --rejected`

  Output began with `NODE_OPTIONS_BYPASS_SENTINEL`, then the guard rejected the forwarded argument. Ambient `NODE_OPTIONS` has the same pre-main behavior. This contradicts the current “non-bypassable” and “caller input cannot become a Node CLI option” claims. A Node guard cannot repair this after startup; either the top-level Node/npm environment must be explicitly trusted and the claims narrowed, or a pre-Node trusted launcher is required.

The three direct fixes otherwise work:

- Forwarded import, file, and option operands are rejected before effects.
- Post-verification lock ownership is rechecked and token mutation rejects verification before spawn.
- Standard npm invocation suppresses its expanded command prelude and does not reflect rejected secret argv.
- Advisory child-time lock limitations are documented accurately.

Validation: 24/24 expanded guard/parser/playtest/lease tests and 13/13 pin/setup-contract tests passed; live direct and npm probes passed; no lock or transaction artifacts remain. No files were edited.

# Command Line Interface

`pymempool` provides both raw endpoint commands and terminal-native mempool views.

## Best first commands

### `pymempool overview`

Answers: how congested the mempool is, what fee band matters now, and how deep the backlog runs.

```bash
pymempool overview --precise-fees --blocks 6
```

Sample output:

```text
Overview
Txs: 12,345  VSize: 2.50 vMB  Backlog: 2.5 blocks  Fees: 7,654,321 sats
fast: 10.25 sat/vB  30m: 7.12 sat/vB  60m: 4.50 sat/vB  econ: 2.25 sat/vB  min: 1.00 sat/vB

Projected Blocks
#  Fill                Txs   Min  Median   Max Spread Depth
1  100% / 1.00 vMB   2,000  6.00  12.0   24.0  18.0   1.0

Interpretation
Congestion is front-loaded: the first projected blocks are materially more expensive than the backlog tail.
```

Options:

- `--precise-fees / --rounded-fees`: choose precise or rounded fee recommendations
- `--blocks`: choose how many projected blocks to show

### `pymempool pressure`

Answers: where the backlog sits across fee-rate bands.

```bash
pymempool pressure
```

Sample output:

```text
Fee Pressure
Band          vMB  Percent  Est. blocks  Note
>= 20 sat/vB  0.40  26.7%   0.4          hot zone
5-10 sat/vB   0.60  40.0%   0.6          queue building
1-2 sat/vB    0.50  33.3%   0.5          low urgency
```

### `pymempool ladder`

Answers: what the next projected blocks look like in a dense decision-first table.

```bash
pymempool ladder --limit 8
pymempool ladder --ascii
```

Options:

- `--limit`: number of projected blocks to show
- `--ascii`: switch to the legacy 3D block view

### `pymempool watch`

Answers: what is changing right now without scrolling event spam.

```bash
pymempool watch --rbf fullRbf --refresh-interval 1.0
```

Options:

- `--rbf`: `off`, `all`, or `fullRbf`
- `--refresh-interval`: refresh cadence in seconds
- `--no-color`: disable Rich color output
- `--verbose`: show extra live diagnostics

## Existing commands

### `pymempool blocks`

Display recent Bitcoin blocks as ASCII art with a summary table:

```bash
pymempool blocks --limit 5
```

### `pymempool mempool-blocks`

Display projected mempool blocks as ASCII art with aggregate statistics:

```bash
pymempool mempool-blocks --limit 4
```

### `pymempool fees`

Show fee recommendations and derived mempool statistics:

```bash
pymempool fees
pymempool fees --precise
```

### `pymempool mempool`

Show the raw mempool summary and fee histogram:

```bash
pymempool mempool
```

### `pymempool halving`

Show the next Bitcoin halving estimate:

```bash
pymempool halving
```

### `pymempool address`

Show address details:

```bash
pymempool address <address>
```

### `pymempool block`

Show block details:

```bash
pymempool block <block_hash>
```

### `pymempool stream`

Stream raw websocket events from a single websocket client lifecycle:

```bash
pymempool stream --want stats --want mempool-blocks
```

## Help

```bash
pymempool --help
pymempool watch --help
```

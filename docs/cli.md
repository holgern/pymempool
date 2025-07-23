# Command Line Interface

`pymempool` provides a command-line interface with various commands to interact with the mempool.space API.

## Available Commands

### Display Recent Blocks

Display recent Bitcoin blocks as ASCII art with statistics:

```bash
pymempool blocks --limit 5
```

### Display Mempool Blocks

Display mempool blocks as ASCII art with statistics:

```bash
pymempool mempool-blocks
```

### Get Halving Information

Get information about the next Bitcoin halving:

```bash
pymempool halving
```

### Get Mempool Information

Get current mempool information:

```bash
pymempool mempool
```

### Get Fee Recommendations

Get current fee recommendations:

```bash
pymempool fees
```

### Get Address Details

Get details about a specific Bitcoin address:

```bash
pymempool address <address>
```

### Get Block Details

Get details about a specific block:

```bash
pymempool block <block_hash>
```

### Stream Live Bitcoin Data

Stream live Bitcoin data from the WebSocket API:

```bash
pymempool stream
```

## Help Information

For more details on any command, use the `--help` option:

```bash
pymempool blocks --help
```

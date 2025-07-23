import json


class MempoolBlockParser:
    """
    Parses the mempool-blocks API output and exposes a list of blocks and helper
    methods.
    """

    def __init__(self, api_json):
        """
        api_json: str (JSON string) or list (already parsed)
        """
        if isinstance(api_json, str):
            self.data = json.loads(api_json)
        elif isinstance(api_json, list):
            self.data = api_json
        else:
            raise ValueError("Input must be a JSON string or a list.")
        self.blocks = [self._parse_block(block) for block in self.data]

    def _parse_block(self, block):
        """
        Returns a dict with the most relevant fields parsed and formatted.
        """
        min_fee = min(block["feeRange"])
        max_fee = max(block["feeRange"])
        median_fee = block["medianFee"]
        total_btc = round(block["totalFees"] / 1e8, 8)
        block_size_mb = round(block["blockSize"] / 1e6, 2)
        return {
            "min_fee": min_fee,
            "max_fee": max_fee,
            "median_fee": median_fee,
            "nTx": block["nTx"],
            "total_btc": total_btc,
            "block_size_mb": block_size_mb,
            "fee_range": block["feeRange"],
            "raw": block,
        }

    def __len__(self):
        return len(self.blocks)

    def __getitem__(self, idx):
        return self.blocks[idx]

    def formatted_lines(self, idx):
        """
        Returns a list of lines suitable for AsciiBlock for block at idx.
        """
        b = self.blocks[idx]
        return [
            f"{b['max_fee']:.2f}-{b['min_fee']:.2f} sat/vB",
            "",
            f"Median: {b['median_fee']:.2f}",
            f"{b['nTx']} TX",
            f"{b['total_btc']} BTC",
            f"{b['block_size_mb']} MB",
        ]

    def all_formatted_lines(self):
        """
        Returns a list of formatted lines for all blocks.
        """
        return [self.formatted_lines(i) for i in range(len(self))]

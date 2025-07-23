import datetime
import json


class BlockParser:
    """
    Parses the output from mempool.space blocks API and exposes a list of
    blocks with helper methods.
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
        # Calculate block size in MB
        block_size_mb = round(block["size"] / 1e6, 2)

        # Format timestamp to human-readable date
        timestamp = block["timestamp"]
        date_time = datetime.datetime.fromtimestamp(timestamp)
        formatted_date = date_time.strftime("%Y-%m-%d %H:%M")

        # Calculate block weight in MWU (Million Weight Units)
        weight_mwu = round(block["weight"] / 1e6, 2)

        # Calculate vsize (virtual size)
        vsize = round(block["weight"] / 4, 2)

        return {
            "height": block["height"],
            "id": block["id"],
            "timestamp": timestamp,
            "formatted_date": formatted_date,
            "tx_count": block["tx_count"],
            "size_mb": block_size_mb,
            "weight_mwu": weight_mwu,
            "vsize": vsize,
            "difficulty": block["difficulty"],
            "merkle_root": block["merkle_root"],
            "previousblockhash": block.get("previousblockhash", ""),
            "nonce": block["nonce"],
            "bits": block["bits"],
            "version": block["version"],
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
            f"Block #{b['height']}",
            "",
            f"{b['formatted_date']}",
            f"{b['tx_count']} transactions",
            f"{b['size_mb']} MB ({b['vsize']} vB)",
            f"Difficulty: {b['difficulty']:.2e}",
            f"Nonce: {b['nonce']}",
        ]

    def all_formatted_lines(self):
        """
        Returns a list of formatted lines for all blocks.
        """
        return [self.formatted_lines(i) for i in range(len(self))]


# Example usage:
if __name__ == "__main__":
    # Example API output string (replace with real API data)
    api_json = """[
        {
            "id": "0000000000000000000384f28cb3b9cf4377a39cfd6c29ae9466951de38c0529",
            "height": 730000,
            "version": 536870912,
            "timestamp": 1648829449,
            "tx_count": 1627,
            "size": 1210916,
            "weight": 3993515,
            "merkle_root":
                "efa344bcd6c0607f93b709515dd6dc5496178112d680338ebea459e3de7b4fbc",
            "previousblockhash":
                "00000000000000000008b6f6fb83f8d74512ef1e0af29e642dd20daddd7d318f",
            "mediantime": 1648827418,
            "nonce": 3580664066,
            "bits": 386521239,
            "difficulty": 28587155782195.14
        }
    ]"""

    parser = BlockParser(api_json)
    for block in parser.blocks:
        print(f"Block #{block['height']} - {block['formatted_date']}")
        print(f"Transactions: {block['tx_count']}")
        print(f"Size: {block['size_mb']} MB")
        print()

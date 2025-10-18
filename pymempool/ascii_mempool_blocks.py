from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymempool.block_parser import BlockParser
    from pymempool.mempool_block_parser import MempoolBlockParser
else:
    try:
        from pymempool.block_parser import BlockParser
    except ImportError:
        BlockParser = None

    try:
        from pymempool.mempool_block_parser import MempoolBlockParser
    except ImportError:
        MempoolBlockParser = None


class AsciiBlock:
    """
    Draws a single 3D ASCII block with centered text lines.
    """

    def __init__(self, width=24, height=9, depth=3):
        self.width = width
        self.height = height
        self.depth = depth

    def _center(self, text, width):
        text = str(text)
        if len(text) > width:
            text = text[: width - 2] + ".."  # Use ellipsis for truncated text
        pad = width - len(text)
        left = pad // 2
        right = pad - left
        return " " * left + text + " " * right

    def render(self, lines):
        w, h, d = self.width, self.height, self.depth
        main = []
        # Calculate the total width of each line to ensure consistency
        total_width = w + 2 + d + 1  # content width + borders + depth + right border

        # Top face - ensuring consistent width
        top_line = " " * d + "+" + "-" * w + "+"
        main.append(top_line.ljust(total_width))

        # Top 3D effect - fixed to ensure consistent side width
        for i in range(1, d):
            side_space = " " * (d - i)
            line = side_space + "/" + " " * w + "/" + " " * i + "|"
            main.append(line.ljust(total_width))

        # Sides and content
        for j in range(h):
            txt = self._center(lines[j], w) if j < len(lines) else " " * w
            line = "|" + txt + "|" + " " * d + "|"
            main.append(line.ljust(total_width))

        # Bottom 3D effect - fixed to ensure consistent width
        for i in range(1, d):
            line = "|" + " " * w + "|" + " " * (d - i) + "/"
            main.append(line.ljust(total_width))

        # Bottom face
        bottom_line = "+" + "-" * w + "+" + "-" * d + "/"
        main.append(bottom_line.ljust(total_width))

        return main


class AsciiMempoolBlocks:
    """
    Draws a row of ASCII blocks using mempool-blocks API output and MempoolBlockParser.
    """

    def __init__(self, block_width=24, block_height=9, block_depth=3, padding=2):
        self.block_width = block_width
        self.block_height = block_height
        self.block_depth = block_depth
        self.padding = padding

    def draw_from_api(self, api_json):
        """
        api_json: str or list, as returned from mempool-blocks API
        Returns: ASCII art string of all blocks in a row
        """
        parser = MempoolBlockParser(api_json)
        return self.draw_from_parser(parser)

    def draw_from_blocks_api(self, api_json):
        """
        api_json: str or list, as returned from blocks API
        Returns: ASCII art string of all blocks in a row
        """
        # Simple approach - use a separate function that doesn't rely on
        # BlockParser import but uses the same API pattern
        import json

        if isinstance(api_json, str):
            data = json.loads(api_json)
        elif isinstance(api_json, list):
            data = api_json
        else:
            raise ValueError("Input must be a JSON string or a list.")

        blocks_lines = []
        for block in data:
            # Format timestamp to human-readable date
            import datetime

            timestamp = block["timestamp"]
            date_time = datetime.datetime.fromtimestamp(timestamp)
            formatted_date = date_time.strftime("%Y-%m-%d %H:%M")

            # Calculate block size in MB
            block_size_mb = round(block["size"] / 1e6, 2)

            # Calculate vsize (virtual size)
            vsize = round(block["weight"] / 4, 2)

            lines = [
                f"Block #{block['height']}",
                "",
                f"{formatted_date}",
                f"{block['tx_count']} transactions",
                f"{block_size_mb} MB ({vsize} vB)",
                f"Difficulty: {block['difficulty']:.2e}",
                f"Nonce: {block['nonce']}",
            ]
            blocks_lines.append(lines)

        # Now use the standard block rendering with these lines
        blocks = []
        for lines in blocks_lines:
            # Ensure each block has the same number of lines
            padded_lines = lines.copy()
            while len(padded_lines) < self.block_height:
                padded_lines.append("")
            blocks.append(
                AsciiBlock(
                    self.block_width, self.block_height, self.block_depth
                ).render(padded_lines)
            )

        if not blocks:
            return ""
        lines_per_block = len(blocks[0])
        row_lines = []
        for k in range(lines_per_block):
            row_lines.append((" " * self.padding).join(block[k] for block in blocks))
        return "\n".join(row_lines)

    def draw_from_parser(self, parser):  # noqa: C901 - complex but refactoring would be a bigger change
        """
        parser: MempoolBlockParser or BlockParser instance
        Returns: ASCII art string
        """
        # Check if this is a valid parser object
        if not hasattr(parser, "all_formatted_lines"):
            if isinstance(parser, list):
                # Assume this is raw data and try to determine format
                if len(parser) > 0 and "blockSize" in parser[0]:
                    parser = MempoolBlockParser(parser)
                elif len(parser) > 0 and "size" in parser[0]:
                    if BlockParser is None:
                        raise ImportError("BlockParser module is not available")
                    parser = BlockParser(parser)
                else:
                    raise ValueError("Unknown data format")
            else:
                # Check if it's a BlockParser instance that's not from the import
                from importlib import import_module

                try:
                    if isinstance(
                        parser, import_module("pymempool.block_parser").BlockParser
                    ):
                        # It's a BlockParser but not recognized by hasattr check
                        # Use it directly with its methods
                        blocks_lines = []
                        for i in range(len(parser)):
                            blocks_lines.append(parser.formatted_lines(i))
                        # Skip to block creation with these lines
                        blocks = []
                        for lines in blocks_lines:
                            padded_lines = lines.copy()
                            while len(padded_lines) < self.block_height:
                                padded_lines.append("")
                            blocks.append(
                                AsciiBlock(
                                    self.block_width,
                                    self.block_height,
                                    self.block_depth,
                                ).render(padded_lines)
                            )

                        if not blocks:
                            return ""
                        lines_per_block = len(blocks[0])
                        row_lines = []
                        for k in range(lines_per_block):
                            row_lines.append(
                                (" " * self.padding).join(block[k] for block in blocks)
                            )
                        return "\n".join(row_lines)
                except (ImportError, AttributeError) as err:
                    # If we can't import or it's not a BlockParser, proceed with error
                    raise ValueError(
                        "Parser must have all_formatted_lines method"
                    ) from err

        blocks_lines = parser.all_formatted_lines()
        # Create uniform blocks with the same dimensions
        blocks = []
        for lines in blocks_lines:
            # Ensure each block has the same number of lines
            padded_lines = lines.copy()
            while len(padded_lines) < self.block_height:
                padded_lines.append("")
            blocks.append(
                AsciiBlock(
                    self.block_width, self.block_height, self.block_depth
                ).render(padded_lines)
            )

        if not blocks:
            return ""
        lines_per_block = len(blocks[0])
        row_lines = []
        for k in range(lines_per_block):
            row_lines.append((" " * self.padding).join(block[k] for block in blocks))
        return "\n".join(row_lines)


# Example usage:
if __name__ == "__main__":
    # Example API output string with mempool blocks
    mempool_api_json = (
        '[{"blockSize":1266018,"blockVSize":997988.25,"nTx":1188,"totalFees":2232795,'
        '"medianFee":2.0068373291590675,"feeRange":[2,2,2,2.0039635354736425,2.1354166666666665,'
        "4.049910873440285,151.02974828375287]},"
        '{"blockSize":2307789,"blockVSize":997977,"nTx":370,"totalFees":1909262,'
        '"medianFee":1.9102450387492722,"feeRange":[1.7168949771689497,1.7496503496503497,'
        "1.8570330514988471,1.9944392956441148,2,2.0035650623885917,2.0106951871657754]}]"
    )
    drawer = AsciiMempoolBlocks(
        block_width=23, block_height=7, block_depth=2, padding=3
    )
    print("Mempool Blocks:")
    print(drawer.draw_from_api(mempool_api_json))

    # Example API output from blocks API
    if BlockParser is not None:
        blocks_api_json = (
            '[{"id":"0000000000000000000384f28cb3b9cf4377a39cfd6c29ae9466951de38c0529",'
            '"height":730000,"version":536870912,"timestamp":1648829449,"tx_count":1627,'
            '"size":1210916,"weight":3993515,'
            '"merkle_root":"efa344bcd6c0607f93b709515dd6dc5496178112d680338ebea459e3de7b4fbc",'
            '"previousblockhash":"00000000000000000008b6f6fb83f8d74512ef1e0af29e642dd20daddd7d318f",'
            '"mediantime":1648827418,"nonce":3580664066,"bits":386521239,'
            '"difficulty":28587155782195.14}]'
        )
        print("\nBitcoin Blocks:")
        print(drawer.draw_from_blocks_api(blocks_api_json))

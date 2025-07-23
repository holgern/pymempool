#!/usr/bin/env python3

"""Make documentation with sphinx."""

import os
import sys
from pathlib import Path

if __name__ == "__main__":
    os.environ["PYTHONPATH"] = os.path.abspath(".")
    os.chdir("docs")
    try:
        os.system("sphinx-build -b html . _build/html")
        print("HTML documentation built successfully.")
        # Open the docs in the browser if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--open":
            import webbrowser

            webbrowser.open(Path("_build/html/index.html").absolute().as_uri())
    except Exception as e:
        print(f"Error building documentation: {e}")
        sys.exit(1)

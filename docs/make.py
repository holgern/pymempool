#!/usr/bin/env python3

"""Build the Sphinx documentation site."""

import os
import sys
from subprocess import CalledProcessError, run
from pathlib import Path

if __name__ == "__main__":
    os.environ["PYTHONPATH"] = os.path.abspath(".")
    os.chdir("docs")
    try:
        run(["sphinx-build", "-b", "html", ".", "_build/html"], check=True)
        print("HTML documentation built successfully.")
        # Open the docs in the browser if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--open":
            import webbrowser

            webbrowser.open(Path("_build/html/index.html").absolute().as_uri())
    except (CalledProcessError, OSError) as e:
        print(f"Error building documentation: {e}")
        sys.exit(1)

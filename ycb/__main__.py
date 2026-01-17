"""
YCB CLI Entry Point

This module enables running YCB CLI using: python -m ycb
"""

from .cli.main import cli

if __name__ == "__main__":
    cli()
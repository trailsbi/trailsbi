# SPDX-License-Identifier: Apache-2.0
"""Allows ``python -m trailsbi``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())

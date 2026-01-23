#!/usr/bin/env python3
"""
Convenience script to run the validator.

Usage:
    python validate.py specs/
    python validate.py specs/agents/product-goal-analyzer/v1/agent.yaml
    python validate.py --format json specs/
"""

import sys
from pathlib import Path

# Add the tools directory to path so we can import validate package
tools_dir = Path(__file__).parent
sys.path.insert(0, str(tools_dir))

from validate.cli import main

if __name__ == "__main__":
    sys.exit(main())

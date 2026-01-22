"""
Allow running orchestrator as a module:
  python -m orchestrator <command> [args]
"""

from .cli import main

if __name__ == "__main__":
    main()

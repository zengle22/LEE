"""
Allow running orchestrator as a module:
  python -m flowcore.orchestrator <command> [args]
"""

if __name__ == "__main__":
    from flowcore.orchestrator.cli import main
    main()

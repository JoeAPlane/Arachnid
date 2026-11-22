"""PyInstaller entry point for the same application used by python -m arachnid."""

from arachnid.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())

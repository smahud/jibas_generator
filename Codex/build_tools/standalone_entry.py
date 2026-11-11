"""Windowed entry point for the standalone distribution."""
import sys


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-check":
        from build_tools.frozen_smoke import main
        raise SystemExit(main(sys.argv[2]))
    import app
    app.main()

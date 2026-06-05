"""GUI entry point."""
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

from src.infrastructure.ui.gui.gui_app import run

if __name__ == "__main__":
    run()

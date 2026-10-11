"""Entry point for running the bot locally, e.g. from Windows Task Scheduler with pythonw.exe.

Reads TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from .env and logs to logs/bot.log.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "logs" / "bot.log"
MAX_LOG_BYTES = 1_000_000

sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MATCHI_BOT_ROOT", str(ROOT))

env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

# pythonw.exe has no console, so send all output to a log file instead.
if sys.stdout is None or not sys.stdout.isatty():
    LOG_FILE.parent.mkdir(exist_ok=True)
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_BYTES:
        LOG_FILE.replace(LOG_FILE.with_suffix(".old.log"))
    sys.stdout = sys.stderr = open(LOG_FILE, "a", encoding="utf-8")
    print(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===")
else:
    sys.stdout.reconfigure(encoding="utf-8")

from matchi_bot.__main__ import run  # noqa: E402

sys.exit(run())

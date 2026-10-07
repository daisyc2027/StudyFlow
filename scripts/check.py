"""Run required checks with separate, preserved logs and honest exit codes."""
import argparse
import os
import json
import time
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(root / ".browsers"))
parser = argparse.ArgumentParser()
parser.add_argument("--all", action="store_true")
parser.add_argument("--webkit", action="store_true", help="Also run the optional WebKit browser suite")
args = parser.parse_args()
commands = [("lint", [sys.executable, "-m", "ruff", "check", "studyflow", "tests", "scripts", "migrations"]),
            ("tests", [sys.executable, "-m", "pytest", "-q", "-m", "not browser"])]
commands.append(("benchmark", [sys.executable, "-m", "scripts.benchmark"]))
if args.all:
    commands.append(("chromium", [sys.executable, "-m", "pytest", "-q", "-m", "browser"]))
    commands.append(("fresh-launch", [sys.executable, "scripts/fresh_setup.py"]))
if args.webkit:
    commands.append(("webkit", [sys.executable, "-m", "pytest", "-q", "-m", "browser"]))
failed = False
results = []
for name, command in commands:
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                            env={**os.environ, "STUDYFLOW_BROWSER": "webkit" if name == "webkit" else "chromium"})
    output = result.stdout + result.stderr
    (root / "docs" / "evidence" / f"{name}.log").write_text(output)
    print(f"{name}: exit {result.returncode}\n{output}", flush=True)
    results.append({'check': name, 'command': command, 'exit_code': result.returncode,
                    'elapsed_seconds': round(time.monotonic() - started, 2)})
    failed |= result.returncode != 0
(root / 'docs' / 'evidence' / 'verification-summary.json').write_text(json.dumps(results, indent=2))
sys.exit(1 if failed else 0)

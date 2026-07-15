"""Run all requested manual store verifications sequentially."""

import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Použitie: verify_all_stores.py JOBS_JSON KRITERIA_JSON")
    jobs = json.loads(sys.argv[1])
    criteria_json = sys.argv[2]
    item_type = json.loads(criteria_json).get("item_type", "")
    for job in jobs:
        subprocess.run(
            [
                sys.executable, str(BASE_DIR / "verify_store.py"),
                job["store"], job["url"], item_type, criteria_json,
            ],
            cwd=BASE_DIR,
            check=False,
        )


if __name__ == "__main__":
    main()

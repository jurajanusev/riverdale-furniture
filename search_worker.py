"""Run a potentially slow multi-store search outside the web request."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from database import save_product
from scrapers import search_all


def write_status(path, **status):
    status["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Použitie: search_worker.py KRITERIA_JSON STATUS_SUBOR")
    criteria = json.loads(sys.argv[1])
    status_path = Path(sys.argv[2]).resolve()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    write_status(status_path, state="running", messages=[])
    try:
        products, messages = search_all(criteria)
        for product in products:
            save_product(product)
        write_status(
            status_path, state="complete", messages=messages,
            imported=len(products), error="",
        )
    except Exception as exc:
        write_status(
            status_path, state="error", messages=[], imported=0,
            error=(" ".join(str(exc).split())[:300] or "Neznáma chyba"),
        )


if __name__ == "__main__":
    main()

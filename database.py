import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from models import Product


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("RIVERDALE_DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "riverdale.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    space_id TEXT NOT NULL DEFAULT 'dom-betty',
    space_name TEXT NOT NULL DEFAULT 'Dom Betty',
    room TEXT NOT NULL DEFAULT 'spálňa / izba',
    main_category TEXT NOT NULL DEFAULT 'nabytok',
    item_type TEXT NOT NULL DEFAULT 'posteľ',
    store TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'Slovensko',
    frame_price REAL,
    original_price REAL,
    sale_price REAL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    mattress_width INTEGER,
    mattress_length INTEGER,
    total_dimensions TEXT DEFAULT 'Neoverené',
    color TEXT DEFAULT 'Neoverené',
    material TEXT DEFAULT 'Neoverené',
    slats_included INTEGER,
    mattress_included INTEGER DEFAULT 0,
    product_url TEXT NOT NULL,
    image_url TEXT DEFAULT '',
    additional_images TEXT DEFAULT '[]',
    local_image TEXT DEFAULT '',
    last_checked TEXT NOT NULL,
    availability TEXT DEFAULT 'Neoverené',
    notes TEXT DEFAULT '',
    approval_status TEXT NOT NULL DEFAULT 'unreviewed',
    style_match_score INTEGER NOT NULL DEFAULT 0 CHECK(style_match_score BETWEEN 0 AND 100),
    source TEXT DEFAULT '',
    verification_data TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_product_filters
ON products(store, country, frame_price, approval_status, availability);
CREATE TABLE IF NOT EXISTS share_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    space_id TEXT NOT NULL,
    room TEXT NOT NULL,
    architect_name TEXT NOT NULL DEFAULT 'Architekt',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS architect_choices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    share_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(share_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_share_context ON share_links(space_id, room, revoked);
CREATE INDEX IF NOT EXISTS idx_choice_share ON architect_choices(share_id, product_id);
"""


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connection() as conn:
        conn.executescript(SCHEMA)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(products)")}
        additions = {
            "space_id": "TEXT NOT NULL DEFAULT 'dom-betty'",
            "space_name": "TEXT NOT NULL DEFAULT 'Dom Betty'",
            "room": "TEXT NOT NULL DEFAULT 'spálňa / izba'",
            "main_category": "TEXT NOT NULL DEFAULT 'nabytok'",
            "item_type": "TEXT NOT NULL DEFAULT 'posteľ'",
        }
        for column, definition in additions.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE products ADD COLUMN {column} {definition}")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_context "
            "ON products(space_id, room, main_category, item_type)"
        )


def next_internal_id(conn):
    row = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 AS n FROM products"
    ).fetchone()
    return f"RIV-ITEM-{row['n']:04d}"


def list_products(filters=None, sort="store"):
    filters = filters or {}
    clauses, params = [], []
    exact = {
        "space_id", "room", "main_category", "item_type", "store", "country",
        "color", "material", "availability", "approval_status",
    }
    for key in exact:
        value = filters.get(key)
        if value:
            if key in {"color", "material"}:
                clauses.append(f"LOWER({key}) LIKE LOWER(?)")
                params.append(f"%{value}%")
            else:
                clauses.append(f"{key} = ?")
                params.append(value)
    if filters.get("max_price"):
        clauses.append("frame_price <= ?")
        params.append(float(filters["max_price"]))
    order = {
        "price_asc": "frame_price IS NULL, frame_price ASC",
        "price_desc": "frame_price IS NULL, frame_price DESC",
        "store": "store COLLATE NOCASE, name COLLATE NOCASE",
        "name": "name COLLATE NOCASE",
        "checked": "last_checked DESC",
    }.get(sort, "store COLLATE NOCASE, name COLLATE NOCASE")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connection() as conn:
        rows = conn.execute(f"SELECT * FROM products{where} ORDER BY {order}", params).fetchall()
    return [Product.from_row(row) for row in rows]


def get_product(product_id):
    with connection() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return Product.from_row(row) if row else None


def save_product(data):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection() as conn:
        existing = None
        if data.get("product_url"):
            existing = conn.execute(
                "SELECT id, internal_id, approval_status, notes FROM products "
                "WHERE product_url = ? AND space_id = ? AND room = ? AND item_type = ?",
                (
                    data["product_url"], data.get("space_id", "dom-betty"),
                    data.get("room", "spálňa / izba"), data.get("item_type", "posteľ"),
                ),
            ).fetchone()
        if existing:
            keep = {"approval_status": existing["approval_status"], "notes": existing["notes"]}
            data.update({k: data.get(k) or v for k, v in keep.items()})
            columns = [k for k in data if k not in {"id", "internal_id", "created_at", "updated_at"}]
            conn.execute(
                f"UPDATE products SET {', '.join(f'{c} = ?' for c in columns)}, updated_at = ? WHERE id = ?",
                [normalize(data[c]) for c in columns] + [now, existing["id"]],
            )
            return existing["id"]
        data["internal_id"] = data.get("internal_id") or next_internal_id(conn)
        data["created_at"] = data["updated_at"] = now
        allowed = set(Product.__dataclass_fields__) - {"id"}
        columns = [k for k in data if k in allowed]
        values = [normalize(data[k]) for k in columns]
        cur = conn.execute(
            f"INSERT INTO products ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            values,
        )
        return cur.lastrowid


def normalize(value):
    if isinstance(value, bool):
        return int(value)
    return value


def update_product(product_id, **changes):
    allowed = {"approval_status", "notes"}
    changes = {k: v for k, v in changes.items() if k in allowed and v is not None}
    if not changes:
        return False
    changes["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection() as conn:
        cur = conn.execute(
            f"UPDATE products SET {', '.join(f'{k} = ?' for k in changes)} WHERE id = ?",
            list(changes.values()) + [product_id],
        )
    return cur.rowcount > 0


def delete_product(product_id):
    with connection() as conn:
        cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    return cur.rowcount > 0


def distinct_values(column):
    allowed = {"space_id", "room", "main_category", "item_type", "store", "country", "color", "material", "availability", "approval_status"}
    if column not in allowed:
        return []
    with connection() as conn:
        rows = conn.execute(f"SELECT DISTINCT {column} AS value FROM products WHERE {column} <> '' ORDER BY value").fetchall()
    return [r["value"] for r in rows]


def create_share_link(token, space_id, room, architect_name, expires_at):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO share_links (token, space_id, room, architect_name, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (token, space_id, room, architect_name, now, expires_at),
        )
    return cur.lastrowid


def get_share_link(token, active_only=True):
    clauses = ["s.token = ?"]
    params = [token]
    if active_only:
        clauses.extend(["s.revoked = 0", "s.expires_at > ?"])
        params.append(datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with connection() as conn:
        row = conn.execute(
            "SELECT s.*, COUNT(c.id) AS selected_count FROM share_links s "
            "LEFT JOIN architect_choices c ON c.share_id = s.id "
            f"WHERE {' AND '.join(clauses)} GROUP BY s.id",
            params,
        ).fetchone()
    return dict(row) if row else None


def list_share_links(space_id, room):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection() as conn:
        rows = conn.execute(
            "SELECT s.*, COUNT(c.id) AS selected_count FROM share_links s "
            "LEFT JOIN architect_choices c ON c.share_id = s.id "
            "WHERE s.space_id = ? AND s.room = ? AND s.revoked = 0 AND s.expires_at > ? "
            "GROUP BY s.id ORDER BY s.created_at DESC",
            (space_id, room, now),
        ).fetchall()
    return [dict(row) for row in rows]


def revoke_share_link(token):
    with connection() as conn:
        cur = conn.execute("UPDATE share_links SET revoked = 1 WHERE token = ?", (token,))
    return cur.rowcount > 0


def architect_choice_ids(share_id):
    with connection() as conn:
        rows = conn.execute(
            "SELECT product_id FROM architect_choices WHERE share_id = ?", (share_id,),
        ).fetchall()
    return {row["product_id"] for row in rows}


def architect_choice_counts(space_id, room):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection() as conn:
        rows = conn.execute(
            "SELECT c.product_id, COUNT(*) AS count FROM architect_choices c "
            "JOIN share_links s ON s.id = c.share_id "
            "WHERE s.space_id = ? AND s.room = ? AND s.revoked = 0 AND s.expires_at > ? "
            "GROUP BY c.product_id",
            (space_id, room, now),
        ).fetchall()
    return {row["product_id"]: row["count"] for row in rows}


def set_architect_choice(share_id, product_id, selected):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection() as conn:
        if selected:
            conn.execute(
                "INSERT INTO architect_choices (share_id, product_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(share_id, product_id) DO UPDATE SET updated_at = excluded.updated_at",
                (share_id, product_id, now, now),
            )
        else:
            conn.execute(
                "DELETE FROM architect_choices WHERE share_id = ? AND product_id = ?",
                (share_id, product_id),
            )

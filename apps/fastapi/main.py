import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="devvpush FastAPI E2E")
RELEASE = "release-v1"
VOLUME_PATH = Path("/data/state/value.txt")
DATABASE_PATH = Path("/data/sqlite/db.sqlite")


class StorageValue(BaseModel):
    value: str


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (
        '<main data-fixture="fastapi" data-release="release-v1">'
        "<h1>devvpush FastAPI E2E</h1>"
        f"<p>{RELEASE}</p>"
        "</main>"
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "release": RELEASE}


@app.post("/storage")
async def write_storage(payload: StorageValue) -> dict[str, str]:
    VOLUME_PATH.parent.mkdir(parents=True, exist_ok=True)
    VOLUME_PATH.write_text(payload.value, encoding="utf-8")
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO state(value) VALUES (?)", (payload.value,))
        count = connection.execute("SELECT COUNT(*) FROM state").fetchone()[0]
    return {"value": payload.value, "database_rows": str(count)}


@app.get("/storage")
async def read_storage() -> dict[str, str | bool]:
    if not VOLUME_PATH.exists() or not DATABASE_PATH.exists():
        return {"available": False, "value": "", "database_rows": "0"}
    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute(
            "SELECT value, (SELECT COUNT(*) FROM state) FROM state ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "available": True,
        "value": VOLUME_PATH.read_text(encoding="utf-8"),
        "database_value": row[0] if row else "",
        "database_rows": str(row[1] if row else 0),
    }

import os
import sqlite3
from pathlib import Path
from urllib.parse import quote

import boto3
import httpx
from botocore.config import Config
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="devvpush FastAPI E2E")
RELEASE = "release-v1"
VOLUME_PATH = Path("/data/state/value.txt")
DATABASE_PATH = Path("/data/sqlite/db.sqlite")
OBJECT_PREFIX = "DEVPUSH_OBJECT_OBJECT_E2E"
OBJECT_KEY = "devpush-e2e/state.txt"
MEDIA_PREFIX = "DEVPUSH_MEDIA_MEDIA_E2E"


class StorageValue(BaseModel):
    value: str


def object_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ[f"{OBJECT_PREFIX}_ENDPOINT_URL"],
        region_name=os.environ[f"{OBJECT_PREFIX}_REGION"],
        aws_access_key_id=os.environ[f"{OBJECT_PREFIX}_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ[f"{OBJECT_PREFIX}_SECRET_ACCESS_KEY"],
        config=Config(
            signature_version="s3v4",
            s3={
                "addressing_style": (
                    "path"
                    if os.environ.get(f"{OBJECT_PREFIX}_FORCE_PATH_STYLE") == "true"
                    else "virtual"
                )
            },
        ),
    )


def media_public_id() -> str:
    folder = os.environ.get(f"{MEDIA_PREFIX}_FOLDER", "").strip("/")
    return f"{folder}/state" if folder else "devpush-e2e/state"


def media_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        auth=httpx.BasicAuth(
            os.environ[f"{MEDIA_PREFIX}_API_KEY"],
            os.environ[f"{MEDIA_PREFIX}_API_SECRET"],
        ),
        timeout=10,
    )


def media_base_url() -> str:
    return (
        f"{os.environ[f'{MEDIA_PREFIX}_API_BASE_URL']}/v1_1/"
        f"{os.environ[f'{MEDIA_PREFIX}_CLOUD_NAME']}"
    )


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


@app.post("/object-storage")
async def write_object(payload: StorageValue) -> dict[str, str]:
    bucket = os.environ[f"{OBJECT_PREFIX}_BUCKET"]
    object_client().put_object(
        Bucket=bucket,
        Key=OBJECT_KEY,
        Body=payload.value.encode(),
        ContentType="text/plain",
    )
    return {"bucket": bucket, "key": OBJECT_KEY, "value": payload.value}


@app.get("/object-storage")
async def read_object() -> dict[str, str]:
    bucket = os.environ[f"{OBJECT_PREFIX}_BUCKET"]
    response = object_client().get_object(Bucket=bucket, Key=OBJECT_KEY)
    body = response["Body"]
    try:
        value = body.read().decode()
    finally:
        body.close()
    return {"bucket": bucket, "key": OBJECT_KEY, "value": value}


@app.post("/media")
async def write_media(payload: StorageValue) -> dict[str, str]:
    public_id = media_public_id()
    async with media_client() as client:
        response = await client.post(
            f"{media_base_url()}/raw/upload",
            data={
                "public_id": public_id,
                "overwrite": "true",
                "context": f"devpush_value={payload.value}",
            },
            files={"file": ("state.txt", payload.value.encode(), "text/plain")},
        )
        response.raise_for_status()
        result = response.json()
    return {
        "public_id": str(result["public_id"]),
        "value": payload.value,
    }


@app.get("/media")
async def read_media() -> dict[str, str]:
    public_id = media_public_id()
    async with media_client() as client:
        response = await client.get(
            f"{media_base_url()}/resources/raw/upload/{quote(public_id, safe='')}"
        )
        response.raise_for_status()
        result = response.json()
    context = result.get("context") or {}
    custom = context.get("custom") if isinstance(context, dict) else {}
    return {
        "public_id": str(result["public_id"]),
        "value": str((custom or {}).get("devpush_value") or ""),
    }


@app.delete("/media")
async def delete_media() -> dict[str, str]:
    public_id = media_public_id()
    async with media_client() as client:
        response = await client.post(
            f"{media_base_url()}/raw/destroy",
            data={"public_id": public_id},
        )
        response.raise_for_status()
        result = response.json()
    return {"public_id": public_id, "result": str(result.get("result") or "")}


@app.get("/media/config")
async def media_config() -> dict[str, str | bool]:
    return {
        "cloud_name": os.environ[f"{MEDIA_PREFIX}_CLOUD_NAME"],
        "folder": os.environ.get(f"{MEDIA_PREFIX}_FOLDER", ""),
        "namespaced_secret": bool(os.environ.get(f"{MEDIA_PREFIX}_API_SECRET")),
        "cloudinary_url": bool(os.environ.get("CLOUDINARY_URL")),
        "conventional_secret": bool(os.environ.get("CLOUDINARY_API_SECRET")),
    }

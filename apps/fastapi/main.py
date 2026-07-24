from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="devvpush FastAPI E2E")
RELEASE = "release-v1"


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

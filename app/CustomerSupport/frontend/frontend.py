"""
Production FastAPI frontend for the CustomerSupport AgentCore agent.

Changes from workshop Flask prototype:
  - FastAPI + uvicorn (async, ASGI, proper concurrency)
  - Pydantic-validated config — no hardcoded secrets
  - Structured JSON logging with request IDs
  - /health and /ready endpoints for load-balancer probes
  - SessionMiddleware backed by configurable SECRET_KEY env var
  - httpx (async) replaces sync requests library
  - debug mode off by default — set DEBUG=true in .env for local dev
"""
from __future__ import annotations

import base64
import json
import logging
import re
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import settings

# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}',
)
logger = logging.getLogger("frontend")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CustomerSupport Agent",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=settings.https_only,
    max_age=3600,
)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
THINKING_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_runtime_arn() -> str:
    # Fast path: env var set directly (production / Docker)
    if settings.runtime_arn:
        return settings.runtime_arn

    # Slow path: read from agentcore CLI state file (local dev without Docker)
    state_path = (
        Path(__file__).parent
        .parent.parent.parent
        / "agentcore" / ".cli" / "deployed-state.json"
    )
    try:
        data = json.loads(state_path.read_text())
        runtimes = (
            data.get("targets", {})
                .get("default", {})
                .get("resources", {})
                .get("runtimes", {})
        )
        runtime = next(iter(runtimes.values()), {})
        arn = runtime.get("runtimeArn", "")
        if arn:
            return arn
        raise ValueError("runtimeArn not found in deployed-state.json")
    except Exception as exc:
        logger.warning('"Could not read deployed-state.json: %s"', exc)
        return "arn:aws:bedrock-agentcore:us-east-1:000000000000:runtime/unknown"


def _invoke_url(arn: str) -> str:
    return (
        f"https://bedrock-agentcore.{settings.region}.amazonaws.com"
        f"/runtimes/{quote(arn, safe='')}/invocations"
    )


def _decode_username(token: str) -> str:
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        return claims.get("email") or claims.get("username") or claims.get("sub", "user")
    except Exception:
        return "user"


async def _exchange_code(code: str) -> dict:
    token_url = f"{settings.cognito_domain}/oauth2/token"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.cognito_client_id,
                "code": code,
                "redirect_uri": settings.redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    resp.raise_for_status()
    return resp.json()


async def _call_agent(prompt: str, token: str, session_id: str) -> str:
    arn = _get_runtime_arn()
    url = _invoke_url(arn)

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url,
            json={"prompt": prompt},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Amzn-Bedrock-AgentCore-Session-Id": session_id,
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
        )

    if resp.status_code != 200:
        logger.error('"AgentCore error status=%d"', resp.status_code)
        raise HTTPException(status_code=resp.status_code, detail=f"Agent error {resp.status_code}")

    chunks: list[str] = []
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            raw = line[6:].strip()
            try:
                chunks.append(json.loads(raw))
            except json.JSONDecodeError:
                chunks.append(raw.strip('"'))

    return THINKING_RE.sub("", "".join(chunks)).strip()


# ---------------------------------------------------------------------------
# Ops
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"], include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/ready", tags=["ops"], include_in_schema=False)
async def ready() -> JSONResponse:
    arn = _get_runtime_arn()
    if "unknown" in arn:
        raise HTTPException(status_code=503, detail="Runtime ARN not resolved — deploy first")
    return JSONResponse({"status": "ready", "runtime_arn": arn})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    if not request.session.get("token"):
        login_url = (
            f"{settings.cognito_domain}/oauth2/authorize?"
            + urlencode({
                "response_type": "code",
                "client_id": settings.cognito_client_id,
                "redirect_uri": settings.redirect_uri,
                "scope": "openid email profile",
            })
        )
        return templates.TemplateResponse(request, "login.html", {"login_url": login_url})

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "runtime_arn": _get_runtime_arn(),
            "username": request.session.get("username", "user"),
        },
    )


@app.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code:
        logger.warning('"Cognito callback error=%s"', error)
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    try:
        tokens = await _exchange_code(code)
    except httpx.HTTPStatusError as exc:
        logger.error('"Token exchange failed status=%d"', exc.response.status_code)
        raise HTTPException(status_code=400, detail="Token exchange failed")

    access_token = tokens.get("access_token", "")
    request.session["token"] = access_token
    request.session["username"] = _decode_username(access_token)
    request.session["session_id"] = str(uuid.uuid4())
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    logout_url = (
        f"{settings.cognito_domain}/logout?"
        + urlencode({
            "client_id": settings.cognito_client_id,
            "logout_uri": settings.redirect_uri.rsplit("/callback", 1)[0] + "/",
        })
    )
    return RedirectResponse(url=logout_url, status_code=status.HTTP_302_FOUND)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat(request: Request) -> JSONResponse:
    token = request.session.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="prompt required")

    session_id = body.get("session_id") or request.session.get("session_id") or str(uuid.uuid4())
    req_id = str(uuid.uuid4())[:8]
    logger.info('"chat req_id=%s session=%s"', req_id, session_id)

    response = await _call_agent(prompt, token, session_id)
    logger.info('"chat done req_id=%s chars=%d"', req_id, len(response))
    return JSONResponse({"response": response, "session_id": session_id, "request_id": req_id})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "frontend:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )

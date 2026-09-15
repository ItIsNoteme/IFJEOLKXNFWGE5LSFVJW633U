import hashlib
import html
import json
import os
import re
import secrets
from pathlib import Path
from typing import cast

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import GameProgress, RedactionRecord, User

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
# Change this value when the developer wants to change the local login password.
DEVELOPER_PASSWORD = "MishaXP2026"
DEBUG = os.getenv("ARG_DEBUG", "false").casefold() in {"1", "true", "yes", "on"}
STATIC_DIR.mkdir(exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARG Desktop", version="1.0.0", debug=DEBUG)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def hash_password(password: str, salt: str | None = None) -> str:
    """Hash a password with PBKDF2 and return a portable salt/hash pair."""
    password_salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), password_salt.encode(), 120_000
    ).hex()
    return f"{password_salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Compare a submitted password against the stored salted hash."""
    try:
        salt, expected_hash = stored_hash.split("$", 1)
    except ValueError:
        return False
    actual_hash = hash_password(password, salt).split("$", 1)[1]
    return secrets.compare_digest(actual_hash, expected_hash)


def get_test_password() -> str:
    """Return the password configured by the developer in this module."""
    return DEVELOPER_PASSWORD


def ensure_test_user(db: Session) -> User:
    """Seed the single requested test account without duplicating it on restart."""
    user = db.query(User).filter(User.display_name == "Misha").first()
    if user is None:
        user = User(
            username="Misha",
            display_name="Misha",
            password_hash=hash_password(get_test_password()),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not verify_password(get_test_password(), cast(str, user.password_hash)):
        # Keep the local credential file and seeded database account aligned.
        setattr(user, "password_hash", hash_password(get_test_password()))
        db.commit()
    if cast(str, user.username) != "Misha":
        setattr(user, "username", "Misha")
        db.commit()
    return user


def get_logged_in_user(request: Request, db: Session) -> User | None:
    """Resolve the signed-in user from the simple local development cookie."""
    username = request.cookies.get("arg_user", "")
    if not username:
        return None
    return db.query(User).filter(User.username == username).first()


def redact_text(text: str) -> str:
    """Replace common sensitive identifiers while leaving ordinary prose readable."""
    redactions = (
        (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL REDACTED]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]"),
        (r"\b(?:\d[ -]*?){13,19}\b", "[CARD REDACTED]"),
            (r"(?<!\w)\+?\d[\d .()-]{7,}\d(?!\w)", "[PHONE REDACTED]"),
    )
    redacted = text
    for pattern, replacement in redactions:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_progress(progress: GameProgress | None):
    if progress is None:
        return {
            "player_name": "Player",
            "stage": "intro",
            "xp": 0,
            "coins": 0,
            "inventory": [],
            "progress_notes": "No save yet.",
        }

    inventory_raw = progress.inventory
    try:
        inventory = json.loads(str(inventory_raw) if inventory_raw is not None else "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        inventory = []

    updated_at = progress.updated_at
    return {
        "player_name": progress.player_name,
        "stage": progress.stage,
        "xp": progress.xp,
        "coins": progress.coins,
        "inventory": inventory,
        "progress_notes": progress.progress_notes,
        "updated_at": updated_at.isoformat() if updated_at is not None else None,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    test_user = ensure_test_user(db)
    logged_in_user = get_logged_in_user(request, db)
    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    payload = serialize_progress(progress)
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "progress": payload,
            "logged_in_user": logged_in_user.display_name if logged_in_user else "",
            "default_username": test_user.display_name,
        },
    )
    return response


@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Authenticate the seeded account and return the refreshed login panel."""
    form = await request.form()
    username = str(form.get("username") or "").strip()
    password = str(form.get("password") or "")

    if not username:
        return HTMLResponse("<div class='login-error'>Enter a username.</div>")

    if not password:
        return HTMLResponse("<div class='login-error'>Enter a password.</div>")

    user = ensure_test_user(db)
    username_matches = username.casefold() == user.username.casefold()
    if not username_matches or not verify_password(password, cast(str, user.password_hash)):
        return HTMLResponse(
            """
            <div id="auth-panel" class="login-panel">
              <h2>Windows XP Login</h2>
              <div class="login-error">Invalid username or password.</div>
              <form hx-post="/login" hx-target="#auth-panel" hx-swap="outerHTML">
                <label>Username<input type="text" name="username" value="Misha" required /></label>
                <label>Password<input type="password" name="password" required autofocus /></label>
                <button class="login-button" type="submit">Log in</button>
              </form>
            </div>
            """
        )

    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    if progress is None:
        progress = GameProgress(player_name=user.display_name, stage="intro")
        db.add(progress)
    else:
        progress.player_name = user.display_name

    db.commit()

    response = Response(status_code=204)
    response.headers["HX-Redirect"] = "/"
    response.set_cookie(
        key="arg_user",
        value=str(user.username),
        httponly=True,
        samesite="lax",
    )
    return response


@app.post("/logout")
async def logout():
    """Clear the local session and return the login form."""
    response = Response(status_code=204)
    response.headers["HX-Redirect"] = "/"
    response.delete_cookie(key="arg_user")
    return response


@app.post("/redact")
async def redact(request: Request, db: Session = Depends(get_db)):
    """Redact submitted text only for an authenticated user and save the safe result."""
    user = get_logged_in_user(request, db)
    if user is None:
        return HTMLResponse("<div class='login-error'>Log in before redacting text.</div>", status_code=401)

    form = await request.form()
    source_text = str(form.get("text") or "")
    redacted = redact_text(source_text)
    db.add(RedactionRecord(user_id=user.id, redacted_text=redacted))
    db.commit()
    return HTMLResponse(
        "<div class='redaction-result'><strong>Redacted output</strong>"
        f"<pre>{html.escape(redacted)}</pre></div>"
    )


@app.get("/api/progress")
async def get_progress(db: Session = Depends(get_db)):
    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    return JSONResponse(content=serialize_progress(progress))


@app.post("/api/progress")
async def save_progress(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    stage = form.get("stage", "intro")

    xp_raw = form.get("xp", "0")
    if isinstance(xp_raw, str):
        xp = int(xp_raw or 0)
    elif isinstance(xp_raw, int):
        xp = xp_raw
    else:
        xp = 0

    coins_raw = form.get("coins", "0")
    if isinstance(coins_raw, str):
        coins = int(coins_raw or 0)
    elif isinstance(coins_raw, int):
        coins = coins_raw
    else:
        coins = 0

    notes = form.get("notes", "")
    inventory_raw = form.get("inventory", "[]")
    player_name = form.get("player_name") or request.cookies.get("arg_user") or "Player"

    if isinstance(inventory_raw, str):
        inventory_str = inventory_raw or "[]"
    else:
        inventory_str = "[]"

    try:
        inventory = json.loads(inventory_str)
    except (TypeError, ValueError, json.JSONDecodeError):
        inventory = []

    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    if progress is None:
        progress = GameProgress()

    setattr(progress, "player_name", str(player_name) or "Player")
    setattr(progress, "stage", str(stage))
    setattr(progress, "xp", xp)
    setattr(progress, "coins", coins)
    setattr(progress, "inventory", json.dumps(inventory))
    setattr(progress, "progress_notes", str(notes))

    db.add(progress)
    db.commit()
    db.refresh(progress)

    return HTMLResponse(
        f"<span class='status-tag'>Saved: {progress.stage}</span><span class='status-tag'>XP: {progress.xp}</span><span class='status-tag'>Coins: {progress.coins}</span>"
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ARG Desktop API"}

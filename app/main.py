import json
import hashlib
import hmac
import html
import re
import secrets
from pathlib import Path

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
STATIC_DIR.mkdir(exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARG Desktop", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def hash_password(password: str, salt: str | None = None) -> str:
    """Create a portable PBKDF2 hash with a fresh salt for each password."""
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), password_salt.encode("ascii"), 120_000
    )
    return f"{password_salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password without exposing the stored password hash."""
    try:
        salt, expected_digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    actual_digest = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual_digest, expected_digest)


def seed_demo_user() -> str:
    """Create the requested test account and return its generated demo password."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "wilbur").first()
        if user is None:
            demo_password = secrets.token_urlsafe(12)
            user = User(
                username="wilbur",
                display_name="Misha",
                password_hash=hash_password(demo_password),
                demo_password=demo_password,
            )
            db.add(user)
            db.commit()
            return demo_password
        return user.demo_password or ""
    finally:
        db.close()


DEMO_PASSWORD = seed_demo_user()


REDACTION_RULES = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "api_key": re.compile(r"\b(?:sk|pk|api)[_-][A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
    "phone": re.compile(r"(?<![\w-])(?:\+?\d[\d .()-]{7,}\d)(?![\w-])"),
}


def redact_text(text: str) -> tuple[str, list[str]]:
    """Replace common sensitive values and report which rules matched."""
    redacted_text = text
    applied_rules = []
    for rule_name, pattern in REDACTION_RULES.items():
        redacted_text, replacements = pattern.subn(f"[REDACTED:{rule_name.upper()}]", redacted_text)
        if replacements:
            applied_rules.append(rule_name)
    return redacted_text, applied_rules


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

    try:
        inventory = json.loads(progress.inventory or "[]")
    except json.JSONDecodeError:
        inventory = []

    return {
        "player_name": progress.player_name,
        "stage": progress.stage,
        "xp": progress.xp,
        "coins": progress.coins,
        "inventory": inventory,
        "progress_notes": progress.progress_notes,
        "updated_at": progress.updated_at.isoformat() if progress.updated_at else None,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    logged_in_user = request.cookies.get("arg_user", "")
    auto_login = False
    if not logged_in_user and DEMO_PASSWORD:
        logged_in_user = "Misha"
        auto_login = True
    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    payload = serialize_progress(progress)
    if not logged_in_user and payload.get("player_name"):
        logged_in_user = payload["player_name"]
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "progress": payload,
            "logged_in_user": logged_in_user,
            "login_name": "Misha",
            "demo_password": DEMO_PASSWORD,
        },
    )
    if auto_login:
        response.set_cookie(key="arg_user", value="Misha", httponly=True, samesite="lax")
    return response


@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = str(form.get("password") or "")

    if not username:
        return HTMLResponse("<div class='login-error'>Enter a username.</div>")

    if not password:
        return HTMLResponse("<div class='login-error'>Enter a password.</div>")

    user = (
        db.query(User)
        .filter((User.username == username.lower()) | (User.display_name == username))
        .first()
    )
    if user is None or not verify_password(password, user.password_hash):
        return HTMLResponse("<div class='login-error'>The username or password is incorrect.</div>")

    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    if progress is None:
        progress = GameProgress(player_name=user.display_name, stage="intro")
        db.add(progress)
    else:
        progress.player_name = user.display_name

    db.commit()

    response = HTMLResponse(
        f"<div class='login-success'>Welcome, {user.display_name}.</div>"
        f"<form hx-post='/logout' hx-target='#auth-panel' hx-swap='outerHTML'><button class='login-button secondary' type='submit'>Log out</button></form>"
    )
    response.set_cookie(key="arg_user", value=user.display_name, httponly=True, samesite="lax")
    return response


@app.post("/logout")
async def logout():
    response = HTMLResponse(
        """
        <div id="auth-panel" class="login-panel">
          <h2>Login</h2>
          <form hx-post="/login" hx-target="#auth-panel" hx-swap="outerHTML">
            <label>
              Username
              <input type="text" name="username" placeholder="Player name" required />
            </label>
            <label>
              Password
              <input type="password" name="password" placeholder="Enter password" required />
            </label>
            <button class="login-button" type="submit">Log in</button>
          </form>
        </div>
        """
    )
    response.delete_cookie(key="arg_user")
    return response


@app.get("/api/progress")
async def get_progress(db: Session = Depends(get_db)):
    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    return JSONResponse(content=serialize_progress(progress))


@app.post("/api/progress")
async def save_progress(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    stage = form.get("stage", "intro")
    xp = int(form.get("xp", 0) or 0)
    coins = int(form.get("coins", 0) or 0)
    notes = form.get("notes", "")
    inventory_raw = form.get("inventory", "[]")
    player_name = form.get("player_name") or request.cookies.get("arg_user") or "Player"

    try:
        inventory = json.loads(inventory_raw)
    except json.JSONDecodeError:
        inventory = []

    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    if progress is None:
        progress = GameProgress()

    progress.player_name = str(player_name) or "Player"
    progress.stage = str(stage)
    progress.xp = xp
    progress.coins = coins
    progress.inventory = json.dumps(inventory)
    progress.progress_notes = str(notes)

    db.add(progress)
    db.commit()
    db.refresh(progress)

    return HTMLResponse(
        f"<span class='status-tag'>Saved: {progress.stage}</span><span class='status-tag'>XP: {progress.xp}</span><span class='status-tag'>Coins: {progress.coins}</span>"
    )


@app.post("/api/redact")
async def redact(request: Request, db: Session = Depends(get_db)):
    """Redact sensitive text, save an audit record, and return an HTMX fragment."""
    form = await request.form()
    source_text = str(form.get("text") or "").strip()
    username = request.cookies.get("arg_user", "Misha")
    if not source_text:
        return HTMLResponse("<div class='login-error'>Enter text to redact.</div>")

    redacted_text, applied_rules = redact_text(source_text)
    record = RedactionRecord(
        username=username,
        source_text=source_text,
        redacted_text=redacted_text,
        rules_applied=json.dumps(applied_rules),
    )
    db.add(record)
    db.commit()
    rules = ", ".join(applied_rules) if applied_rules else "none"
    return HTMLResponse(
        "<div class='redaction-result'>"
        f"<strong>Redacted text</strong><pre>{html.escape(redacted_text)}</pre>"
        f"<small>Rules applied: {html.escape(rules)}. Saved as record #{record.id}.</small>"
        "</div>"
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ARG Desktop API"}

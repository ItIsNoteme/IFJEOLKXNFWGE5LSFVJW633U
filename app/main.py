import json
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import GameProgress

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARG Desktop", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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
    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    payload = serialize_progress(progress)
    if not logged_in_user and payload.get("player_name"):
        logged_in_user = payload["player_name"]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "progress": payload,
            "logged_in_user": logged_in_user,
        },
    )


@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = str(form.get("password") or "")

    if not username:
        return HTMLResponse("<div class='login-error'>Enter a username.</div>")

    if not password:
        return HTMLResponse("<div class='login-error'>Enter a password.</div>")

    progress = db.query(GameProgress).order_by(GameProgress.id.desc()).first()
    if progress is None:
        progress = GameProgress(player_name=username, stage="intro")
        db.add(progress)
    else:
        progress.player_name = username

    db.commit()

    response = HTMLResponse(
        f"<div class='login-success'>Welcome, {username}.</div>"
        f"<form hx-post='/logout' hx-target='#auth-panel' hx-swap='outerHTML'><button class='login-button secondary' type='submit'>Log out</button></form>"
    )
    response.set_cookie(key="arg_user", value=username, httponly=True, samesite="lax")
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


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ARG Desktop API"}

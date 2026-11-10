from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "assistant.db"
SECRET = os.getenv("APP_SECRET", "change-this-secret-before-deployment").encode()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

app = FastAPI(title="Personal AI Assistant", version="1.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")


@app.on_event("startup")
def startup():
    init_db()


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":", 1)
    candidate = hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
    return hmac.compare_digest(candidate, digest_hex)


def make_token(user_id: int) -> str:
    payload = f"{user_id}:{int(time.time()) + 60 * 60 * 24 * 7}"
    signature = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Please log in first.")
    token = authorization[7:]
    try:
        user_text, expiry_text, signature = token.split(":")
        payload = f"{user_text}:{expiry_text}"
        expected = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expiry_text) < int(time.time()):
            raise ValueError("invalid token")
        user_id = int(user_text)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired login. Please log in again.")
    with db() as conn:
        user = conn.execute("SELECT id, email FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return dict(user)


class AuthInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class NoteInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=10000)


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=250)


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Personal AI Assistant", "version": "1.0.0"}


@app.post("/api/register")
def register(data: AuthInput):
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                (data.email.lower(), hash_password(data.password)),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        user_id = cur.lastrowid
    return {"token": make_token(user_id), "email": data.email.lower()}


@app.post("/api/login")
def login(data: AuthInput):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (data.email.lower(),)).fetchone()
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"token": make_token(user["id"]), "email": user["email"]}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return user


@app.post("/api/chat")
def chat(data: ChatInput, user=Depends(current_user)):
    # A local fallback keeps the app runnable without an AI API key.
    if not GEMINI_API_KEY:
        return {
            "reply": (
                "Your assistant is running in local demo mode. Add GEMINI_API_KEY to the "
                ".env file and restart the server to enable Gemini responses. "
                "For now, I received your message: " + data.message
            ),
            "mode": "demo",
        }
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(data.message)
        return {"reply": response.text, "mode": "gemini"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")


@app.get("/api/notes")
def get_notes(user=Depends(current_user)):
    with db() as conn:
        rows = conn.execute(
            "SELECT id, title, content, created_at FROM notes WHERE user_id=? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/notes")
def add_note(data: NoteInput, user=Depends(current_user)):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO notes(user_id, title, content) VALUES (?, ?, ?)",
            (user["id"], data.title, data.content),
        )
        note_id = cur.lastrowid
    return {"id": note_id, "message": "Note saved."}


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int, user=Depends(current_user)):
    with db() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, user["id"]))
    if not cur.rowcount:
        raise HTTPException(status_code=404, detail="Note not found.")
    return {"message": "Note deleted."}


@app.get("/api/tasks")
def get_tasks(user=Depends(current_user)):
    with db() as conn:
        rows = conn.execute(
            "SELECT id, title, done, created_at FROM tasks WHERE user_id=? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/tasks")
def add_task(data: TaskInput, user=Depends(current_user)):
    with db() as conn:
        cur = conn.execute("INSERT INTO tasks(user_id, title) VALUES (?, ?)", (user["id"], data.title))
    return {"id": cur.lastrowid, "message": "Task added."}


@app.patch("/api/tasks/{task_id}")
def toggle_task(task_id: int, user=Depends(current_user)):
    with db() as conn:
        row = conn.execute("SELECT done FROM tasks WHERE id=? AND user_id=?", (task_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found.")
        new_value = 0 if row["done"] else 1
        conn.execute("UPDATE tasks SET done=? WHERE id=? AND user_id=?", (new_value, task_id, user["id"]))
    return {"id": task_id, "done": bool(new_value)}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, user=Depends(current_user)):
    with db() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user["id"]))
    if not cur.rowcount:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"message": "Task deleted."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

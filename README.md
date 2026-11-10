# Personal AI Assistant — Fresh Starter (14 modules)

A clean Windows/VS Code starter with a FastAPI backend, responsive web dashboard, SQLite accounts, notes and tasks, optional Gemini chat integration, and PWA install support.

## Included modules

1. AI Chat — local demo response by default; optional Gemini API integration.
2. Authentication — registration, login, logout and signed bearer sessions.
3. Location — browser permission-based geolocation.
4. Voice Assistant — browser speech recognition and text-to-speech where supported.
5. Security — security guidance (not antivirus/IDS).
6. Utilities — basic calculator and live clock.
7. Learning — learning workflow guidance.
8. Productivity — working notes and tasks stored per account in SQLite.
9. Smart Study — study workflow guidance.
10. Career — resume and placement workflow guidance.
11. Developer Tools — development workflow guidance and API docs shortcut.
12. File Manager — safe workflow guidance; file uploads are not implemented.
13. Device Health — maintenance checklist; no hardware scan.
14. Automation — workflow ideas; background scheduling is not implemented.

Some modules are functional starter interfaces rather than complete commercial-grade services. The README identifies those limits; do not present them as fully implemented security, file scanning, or automation systems.

## Windows setup (PowerShell in VS Code)

1. Extract the ZIP.
2. Open the extracted `Personal_AI_Assistant_Starter` folder in VS Code.
3. Open Terminal → New Terminal and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run this once in that terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

4. Start the server:

```powershell
uvicorn main:app --reload
```

5. Open these addresses in Chrome:

- Website: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

Stop the server with `Ctrl+C`.

## Optional Gemini chat

1. Copy `.env.example` to `.env`.
2. Set `GEMINI_API_KEY` to your own key and set a long random `APP_SECRET`.
3. Install/load environment values before starting. Easiest option:

```powershell
pip install python-dotenv
```

Then add these lines near the imports in `main.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

4. Restart Uvicorn. Without a key, chat deliberately stays in local demo mode.

Never publish `.env` or expose your API key in frontend JavaScript or GitHub.

## Run checks

```powershell
python -m compileall main.py
python -m pytest -v
```

## Database

SQLite database `assistant.db` is created automatically on first run. Back it up before deleting it; it contains registered accounts, notes and tasks.

## PWA / Android

The site includes a web app manifest and service worker. For Android installation, deploy the site over HTTPS first, open it in Chrome, then use Chrome's menu → **Install app** or **Add to Home screen** (wording varies).

## Production security checklist

This is a learning starter, not a production-hardened product. Before public launch:
- Replace `APP_SECRET` with a strong private secret.
- Use HTTPS and a managed production database.
- Add rate limiting, email verification, password reset, CSRF protections where applicable, audit logging and security review.
- Configure trusted origins/CORS if frontend and backend are hosted separately.
- Add privacy disclosures and consent flows for personal data.
- Add tests for all business logic and use a production server configuration.
- Do not store sensitive user information until security and privacy controls are reviewed.

## Troubleshooting

- `uvicorn is not recognized`: activate `.venv` and run `python -m pip install -r requirements.txt`.
- `Could not import module main`: make sure the terminal's current directory is the folder containing `main.py`.
- `Address already in use`: stop the other server or use `uvicorn main:app --reload --port 8001`.
- Missing package: run `pip install -r requirements.txt` again inside the activated environment.

# Running MathMingo locally (without Docker)

This starts the **backend** (FastAPI, port 8000) and the **frontend** (Expo web, port 8081) on your
own machine. Both use the team's shared **dev** Supabase, so you can sign in with an existing
account and see the same data as everyone else.

The settings are already in the repository: `backend/.env` and `frontend/.env`. You don't need to
create or edit any `.env` file.

---

## 1. Install these first

| Tool | Version | Notes |
|---|---|---|
| **Python** | **3.11.x exactly** | Not 3.10, 3.12 or 3.13. The Component C engine package only installs on 3.11. Download from python.org, and on Windows tick "Add python.exe to PATH". |
| **Node.js** | 20 or newer (tested on 24) | From nodejs.org. It includes `npm`. |
| **Git** | any | |

Check them:

```bash
python --version   # Python 3.11.x   (on Windows you can also use: py -3.11 --version)
node --version     # v20 or newer
```

---

## 2. Backend (terminal 1)

All commands run inside the `backend` folder.

### First time only: create the virtual environment and install

**Windows (PowerShell):**

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# The lock file was made for Linux and includes `uvloop`, which does not exist on Windows.
# This installs everything else in it, with the same pinned versions and hashes.
python -c "import re,pathlib; t=pathlib.Path('requirements.lock').read_text(); pathlib.Path('.venv/requirements.windows.lock').write_text(re.sub(r'^uvloop==.*?(?=^\S)', '', t, flags=re.M|re.S))"
python -m pip install --require-hashes --no-deps -r .venv/requirements.windows.lock
```

If PowerShell refuses to run `Activate.ps1`, run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**macOS / Linux:**

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --no-deps -r requirements.lock
```

### Every time: start it

```bash
# Windows: .\.venv\Scripts\Activate.ps1      macOS/Linux: source .venv/bin/activate
python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

`--env-file .env` is required: the backend reads its settings from environment variables and does
not load `.env` by itself.

### Check that it works

Open these in a browser:

| URL | Expected |
|---|---|
| http://localhost:8000/health/live | `{"status":"alive", ...}` |
| http://localhost:8000/health/ready | `"status":"ready"` and `"database_connection":"ok"` |
| http://localhost:8000/docs | The interactive API documentation |

If `database_connection` isn't `ok`, see Troubleshooting below.

---

## 3. Frontend (terminal 2)

All commands run inside the `frontend` folder.

### First time only

```bash
cd frontend
npm install
```

### Every time

```bash
npx expo start --web --port 8081
```

Then open **http://localhost:8081** and sign in.

- Expo reads the `.env` files **only when it starts**. If you change one, stop Expo with `Ctrl+C`
  and start it again.
- `frontend/.env.local` overrides `frontend/.env` when both set the same value.
- After pulling big changes, a clean start helps: `npx expo start --web --port 8081 --clear`.

---

## 4. Rules for the shared database

Everyone uses the same dev Supabase, so:

- **Do not run `alembic upgrade`, `alembic downgrade` or `alembic stamp`.** The database is already
  migrated. Schema changes are coordinated by one person.
- **Do not run the backend test suite (`pytest`) while `backend/.env` points at Supabase.** Some
  tests drop and recreate every table. Use the Docker test setup for tests instead.
- Treat the data as shared: other people's test accounts and results are in there too.

---

## 5. Testing on a phone (optional)

The phone has to reach your computer over Wi-Fi, so `localhost` won't work:

1. Find your computer's local IP address (for example `192.168.1.20`).
2. Start the backend on all interfaces: add `--host 0.0.0.0` instead of `--host 127.0.0.1`.
3. Add `EXPO_PUBLIC_API_BASE_URL=http://192.168.1.20:8000` (with your IP) to
   `frontend/.env.local`. Restart Expo and scan its QR code with Expo Go.
4. **Don't commit that change**: your IP is not your teammates' IP.

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| `Failed to build 'uvloop'` | You're on Windows and used `requirements.lock` directly. Use the Windows install command in section 2. |
| `requires a different Python: ... not in '<3.12,>=3.11'` | Your virtual environment isn't Python 3.11. Delete `.venv` and create it again with `py -3.11 -m venv .venv`. |
| `Address already in use` / port 8000 or 8081 is busy | Something else is already running there. On Windows, `netstat -ano \| findstr :8000` shows the process id. Close that program (Docker's `api` container also uses 8000). |
| `/health/ready` shows the database failing | Check your internet connection. The dev Supabase may also be paused (free projects pause after inactivity); ask the project owner to resume it. |
| The app shows "We can't reach compD right now" or a network error | The backend isn't running, or it isn't on port 8000. Check http://localhost:8000/health/live. |
| The browser console shows a CORS error | The frontend must run on one of the allowed ports in `backend/.env` (`CORS_ALLOWED_ORIGINS`); 8081 is allowed. |
| Changes to `.env` have no effect | Restart the backend (`Ctrl+C`, start again) or Expo. Neither reloads `.env` while running. |

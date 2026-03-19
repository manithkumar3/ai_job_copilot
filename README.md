# AI Job Copilot

AI Job Copilot is a full-stack FastAPI application for managing job applications and improving resumes with AI.

## What it includes

- Email/password authentication
- Google login via OAuth
- Resume uploads for PDF, DOCX, TXT, and Markdown
- AI resume analysis against a job description or job link
- Improved resume DOCX generation
- Job tracker with wishlist, bookmarks, tags, notes, reminders, and resume version linking
- Dashboard analytics with simple AI job insights
- Smart extraction of company, title, skills, location, employment type, and experience level
- Dark and light mode

## Tech stack

- Backend: FastAPI
- Frontend: Jinja2 templates rendered by FastAPI
- Database: SQLite by default for local development, or PostgreSQL via SQLAlchemy when configured
- Auth: Session-based auth, password login, Google OAuth
- AI: OpenAI when configured, heuristic fallback when not configured

## Project structure

```text
app/
  main.py
  auth.py
  config.py
  database.py
  models.py
  routes/
  services/
  static/
  templates/
scripts/
  seed_data.py
tests/
requirements.txt
docker-compose.yml
```

## Setup

1. Create a virtual environment and install dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file and add your local settings.

```bash
touch .env
```

3. Optional: start PostgreSQL if you want to use Docker/Postgres instead of the default SQLite database.

```bash
docker compose up -d
```

4. Run the app.

```bash
uvicorn app.main:app --reload
```

5. Optional: seed demo data.

```bash
python3 scripts/seed_data.py
```

Open the app at `http://127.0.0.1:8000`.

For external uptime monitoring, you can point UptimeRobot at `http://127.0.0.1:8000/health` and use the `HEAD` method.

## Environment variables

Important values:

- `DATABASE_URL`: Optional database connection string for SQLite or PostgreSQL
- `SECRET_KEY`: Session signing key
- `OPENAI_API_KEY`: Enables real AI analysis
- `OPENAI_MODEL`: Model name for resume analysis
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`: Enable Google login
- Keep `.env` local only and do not commit real secrets

## Demo login after seeding

- Email: `demo@example.com`
- Password: `password123`

## Notes

- If `DATABASE_URL` is not set, the app uses a local SQLite database at `ai_job_copilot.db`.
- To use Docker/Postgres, set `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_job_copilot` in `.env`.
- If your local port `5432` already points to another Postgres instance, the app can fail with password errors unless `.env` points at the correct database.
- If `OPENAI_API_KEY` is missing, the app still works using heuristic analysis.
- If Google OAuth is not configured, the Google button safely redirects back with a message.
- Uploaded and generated files are stored under `app/static/uploads/`.

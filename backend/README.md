# Endometriosis Screening Research Prototype

A research backend that uses machine learning to screen for endometriosis-related risk from self-reported symptoms (Tier 1) and, when the first result is elevated, refines it with two blood markers (Tier 2). Users have accounts, and every screening is saved privately under their account.

> **Medical disclaimer:** This is a research prototype, not a diagnostic tool. Its output must not replace professional medical assessment. The models were trained on a **synthetic** dataset and have not been validated on real clinical data, so results must never be presented as clinically validated or as a diagnosis.

## Contents

* [How it works](#how-it-works)
* [Technology stack](#technology-stack)
* [Project structure](#project-structure)
* [Quick start (Docker)](#quick-start-docker)
* [Settings (.env)](#settings-env)
* [Using the API](#using-the-api)
* [Endpoints](#endpoints)
* [Tests](#tests)
* [Security and privacy](#security-and-privacy)
* [Troubleshooting](#troubleshooting)
* [Limitations](#limitations)

## How it works

1. **Tier 1 (symptoms):** the user submits 12 symptom and background answers (age, BMI, cycle length, pain scores, family history, and so on). The Tier 1 model returns a risk probability and a flag.
2. **Tier 2 (labs):** if Tier 1 flagged the screening as elevated, the user can add CA-125 and CRP blood values to the *same* screening. The Tier 2 model returns a second probability.
3. **Recommendation:** the two results are combined into one recommendation, for example `elevated_not_confirmed` (symptoms raised a flag, but the lab values did not support it).
4. Each result includes the main contributing factors, a plain-language report, and a disclaimer. While `MODEL_VALIDATED=false`, the wording is deliberately softened and every result is labelled a prototype.

## Technology stack

| Component | Technology |
| --- | --- |
| Language | Python 3.12 |
| API framework | FastAPI, served by Uvicorn |
| Database | PostgreSQL 16 |
| Database access | SQLAlchemy 2 with Alembic migrations |
| Validation | Pydantic |
| Authentication | JWT access tokens (30-minute expiry), Argon2 password hashing |
| Machine learning | scikit-learn models loaded from `ml_artifacts/` |
| Packaging | Docker and Docker Compose |
| Tests | Pytest (run on a temporary in-memory SQLite database) |

## Project structure

```text
backend/
├── app/
│   ├── main.py            # creates the app and registers routes
│   ├── api/
│   │   ├── deps.py        # login check used by protected routes
│   │   └── routes/        # auth.py, screenings.py, account.py
│   ├── core/              # config.py (settings), security.py (passwords, tokens)
│   ├── db/                # database models and sessions
│   ├── repositories/      # database read/write code
│   ├── schemas/           # request and response shapes
│   └── services/          # screening logic, model loading, predictions, explanations
├── alembic/               # database migrations
├── ml_artifacts/          # trained Tier 1 and Tier 2 models and scalers
├── scripts/smoke_test.py  # tries every endpoint on a running server
├── tests/                 # automated tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Quick start (Docker)

You need Docker Desktop installed and running.

1. Open a terminal in the `backend/` folder.
2. Copy the settings template.

   Windows PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   macOS / Linux:

   ```bash
   cp .env.example .env
   ```

3. Fill in the two blanks in `.env`: `POSTGRES_PASSWORD` (any strong password) and `JWT_SECRET` (see [Settings](#settings-env) for a one-line command that generates it).
4. Start everything:

   ```bash
   docker compose up --build
   ```

   The first run downloads and builds for several minutes. Later runs take about a minute. It is ready when you see `Application startup complete`. The database tables are created automatically by the migration that runs at startup.
5. Open the interactive docs at <http://127.0.0.1:8000/docs>.

To stop: press `Ctrl + C`, then run `docker compose down`. Your saved data is kept. Do **not** add `-v` to that command unless you want to erase the database.

## Settings (.env)

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database name and login used by Docker Compose. The password must not be empty. |
| `JWT_SECRET` | Secret used to sign login tokens. Required, at least 32 characters; the app refuses to start otherwise. |
| `ENVIRONMENT` | `development` or `production`. |
| `CORS_ORIGINS` | Comma-separated list of frontend addresses allowed to call the API (default `http://localhost:3000`). |
| `MODEL_VALIDATED` | Keep `false` until the models are validated on real clinical data. |

Generate a secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Never commit `.env` or share it. It contains your secrets.

If you run Uvicorn directly instead of through Docker, also set `DATABASE_URL` (an example is in `.env.example`).

## Using the API

1. **Register** with `POST /auth/register`. Send an email, a password, `consent_accepted: true`, and the current `consent_version` (`2026-10-v1`).
2. **Log in** with `POST /auth/login`. The response contains an `access_token`.
3. On the `/docs` page, press **Authorize** and paste the token. Tokens last 30 minutes; log in again when one expires.
4. **Screen** with `POST /screenings`, sending the symptom answers.
5. If the result is elevated, **add labs** with `POST /screenings/{screening_id}/labs` using the id from step 4.
6. **Review** past results with `GET /screenings`, export everything with `GET /account/export`, or delete data with the `DELETE` routes.

## Endpoints

| Method | Path | Purpose | Login needed |
| --- | --- | --- | --- |
| POST | `/auth/register` | Create an account (requires consent) | No |
| POST | `/auth/login` | Get an access token | No |
| GET | `/auth/me` | Show the logged-in account | Yes |
| POST | `/screenings` | Run a Tier 1 symptom screening | Yes |
| GET | `/screenings` | List your screenings | Yes |
| GET | `/screenings/{screening_id}` | View one screening | Yes |
| POST | `/screenings/{screening_id}/labs` | Add CA-125 and CRP for Tier 2 | Yes |
| DELETE | `/screenings/{screening_id}` | Delete one screening | Yes |
| DELETE | `/screenings` | Delete all your screenings | Yes |
| GET | `/account/export` | Download all your data | Yes |
| DELETE | `/account` | Delete your account and data | Yes |
| GET | `/health` | Check the service is up | No |

The `/docs` page lists the exact request fields and response formats.

## Tests

Install the development tools into a virtual environment, then run the tests:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

The tests use a temporary in-memory SQLite database, so they need neither Docker nor PostgreSQL, and they never touch real data. They cover registration and login, screenings, Tier 2 labs, ownership checks (no one can read another user's records), export, deletion, and the prototype wording.

With the server running, `python scripts/smoke_test.py` also tries every endpoint end to end using two throwaway accounts, which it deletes afterwards.

## Security and privacy

* Passwords are stored only as Argon2 hashes.
* Every route except register, login, and health requires a valid token, and a test enforces this.
* Each user can only see and delete their own records.
* Users can export all their data and delete their account.
* The app refuses to start with a missing or short `JWT_SECRET`.
* The database port is bound to `127.0.0.1` only.
* Use synthetic or properly de-identified data for development. Real participant data needs appropriate consent, ethics approval, and legal review first.

Not yet in place, and needed before any real-world use: HTTPS, managed secret storage, backups, login rate limiting, monitoring, and clinical validation.

## Troubleshooting

* **Database container says the password is not specified:** `POSTGRES_PASSWORD` in `.env` is empty. Fill it in and run `docker compose up` again.
* **The app exits at startup mentioning `JWT_SECRET`:** it is missing or shorter than 32 characters.
* **`401 Not authenticated` on `/docs`:** your token expired (30 minutes) or you have not pressed Authorize. Log in again.
* **`404 Screening not found` when adding labs:** the `screening_id` box still holds the grey example value. Paste a real id from `GET /screenings`.
* **`409` when adding labs:** labs were already added to that screening, or the first result was not elevated.
* **Docker commands fail with a connection error:** start Docker Desktop and wait for it to say the engine is running.

## Limitations

* The models were trained on a synthetic dataset. Very high accuracy figures on synthetic data do not predict performance on real patients, and some behaviour reflects the made-up data rather than medical practice. For example, a CA-125 of 45 is above the cut-off of about 35 that is commonly treated as raised, yet the Tier 2 model scores it as low risk because of how the synthetic values are distributed.
* Output is a screening aid, not a diagnosis.
* Real clinical validation, independent evaluation across demographic groups, and an ethics review are required before any clinical use.

## Disclaimer

This project is for research and educational purposes. Its output must not be the sole basis for medical decisions and does not replace consultation with a qualified healthcare professional.

# Artiou (艺游) MVP

A React Native + Expo + FastAPI MVP for a museum audio guide app.

## Project Structure

```text
museum_guide/
├── backend/
│   ├── Taskfile.yml
│   ├── pyproject.toml
│   ├── VERSION.txt
│   ├── app.py
│   ├── routes.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analyze.py
│   │   └── tts.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── utils/
│   │   └── __init__.py
│   ├── src/
│   │   └── __init__.py
│   ├── commands/
│   │   └── __init__.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   └── test_analyze.py
│   │   └── integration/
│   │       ├── __init__.py
│   │       └── test_api.py
│   └── .env.example
├── frontend/
│   └── ...
└── README.md
```

## Features (MVP)

- Take photo from camera
- Upload image to backend `/analyze`
- Display Chinese result from GPT-4o Vision
- Generate and play TTS audio
- Save and view simple local history

## Backend Setup

```bash
cd backend
poetry install
cp .env.example .env
```

### Run with Taskfile

```bash
task install
task serve
task test
task lint
```

### Run directly

```bash
poetry run uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Required env vars in `backend/.env`:

- `OPENAI_API_KEY`
- Optional: `OPENAI_VISION_MODEL`, `OPENAI_TTS_MODEL`, `OPENAI_TTS_VOICE`, `CORS_ORIGINS`

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run start
```

Required env vars in `frontend/.env`:

- `EXPO_PUBLIC_API_BASE_URL` (e.g. `http://127.0.0.1:8000`)

## Artiou website deploy/review checklist

Before marking a website deploy as REVIEW/PASS, run the live SEO smoke test from the repo root:

```bash
python3 website/artiou/scripts/live-seo-smoke.py
```

For a faster preflight that still checks canonical host redirects, UTF-8 headers, robots sitemap declaration, core English growth URLs, and missing-path 404/410 behavior:

```bash
python3 website/artiou/scripts/live-seo-smoke.py --core-only
```

The full smoke test parses `https://www.artiou.com/sitemap.xml` and requires every sitemap URL to return `200`, be indexable, be self-canonical, avoid fallback-shell canonical mismatches, and contain no internal planning/placeholder language. Missing probes such as `/en/nonexistent-growth-audit-test/` and `/en/news/nonexistent-growth-audit-test/` must return `404` or `410`; if they return a `200` fallback, the command exits non-zero and the deploy must not be marked REVIEW/PASS.

## API Endpoints

- `GET /` health check
- `POST /analyze` with `multipart/form-data` field `image`
- `POST /tts` with JSON body: `{ "text": "..." }`

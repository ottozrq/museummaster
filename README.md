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

## API Endpoints

- `GET /` health check
- `POST /analyze` with `multipart/form-data` field `image`
- `POST /tts` with JSON body: `{ "text": "..." }`

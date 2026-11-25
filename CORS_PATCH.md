# Backend CORS patch — required before the frontend can talk to the API

The backend at HEAD 8481d7a has no CORS middleware in `app/main.py`.
A browser page on one origin (e.g. `http://localhost:5173`) is blocked
from calling the API on another origin (`http://localhost:8002`) unless
the backend explicitly allows it. Without this patch, every frontend
request fails in the browser even though Swagger works.

## 1. `app/core/config.py` — add one setting

Inside the `Settings` class, next to the other settings:

```python
CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"
```

Comma-separated list, no spaces needed. On Render, set the env var to
the public frontend URL only, e.g.
`CORS_ORIGINS=https://diagnoflow-frontend.onrender.com`.

## 2. `app/main.py` — add the middleware

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=get_settings().APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Put `add_middleware` right after `app = FastAPI(...)`, before
`register_exception_handlers(app)` / `include_router(...)`.

## 3. Rebuild / restart the backend

Local Docker (the compose file mounts `./app`, but a restart is still
needed for the new setting to load):

```powershell
docker compose up -d --build --force-recreate diagnoflow
```

Then open the frontend and log in. If the browser console still shows
a CORS error, check that the origin in the error message is exactly
one of the comma-separated values in `CORS_ORIGINS`.

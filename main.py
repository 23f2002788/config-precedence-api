import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow browser-based cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

# Layer 1: Hardcoded defaults
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def load_yaml():
    # Layer 2: Environment-specific YAML
    path = BASE_DIR / "config.development.yaml"

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_dotenv_layer():
    # Layer 3: Read .env separately so that it
    # does not overwrite the actual OS variables.
    values = dotenv_values(BASE_DIR / ".env")
    result = {}

    for key, value in values.items():
        if value is None:
            continue

        if key == "NUM_WORKERS":
            result["workers"] = value
        elif key.startswith("APP_"):
            result[key[4:].lower()] = value

    return result


def load_os_layer():
    # Layer 4: Actual OS-level APP_* variables
    result = {}

    for key, value in os.environ.items():
        if key.startswith("APP_"):
            result[key[4:].lower()] = value

    return result


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {
            "true", "1", "yes", "on"
        }

    return str(value)


@app.get("/effective-config")
def effective_config(
    set: list[str] = Query(default=[])
):
    # Merge from lowest to highest precedence.
    config = DEFAULTS.copy()
    config.update(load_yaml())
    config.update(load_dotenv_layer())
    config.update(load_os_layer())

    # Layer 5: Query-string overrides.
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = key.strip().lower()

        if key:
            config[key] = value

    # Apply the required types.
    config = {
        key: coerce(key, value)
        for key, value in config.items()
    }

    # Never reveal the real API key.
    config["api_key"] = "****"

    return config
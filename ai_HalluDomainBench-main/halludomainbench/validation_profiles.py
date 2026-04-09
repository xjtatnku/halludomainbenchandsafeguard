from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import read_json


def load_validation_profiles(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Validation profile file must be a JSON object: {path}")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError(f"Validation profile file must contain a 'profiles' object: {path}")
    return {
        str(name): dict(profile)
        for name, profile in profiles.items()
        if isinstance(profile, dict)
    }


def load_validation_profile(path: Path, profile_name: str) -> dict[str, Any]:
    profiles = load_validation_profiles(path)
    if profile_name not in profiles:
        raise ValueError(f"Unknown validation profile '{profile_name}' in {path}")
    return dict(profiles[profile_name])

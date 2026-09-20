# -*- coding: utf-8 -*-
"""
VietLabor AI - UI Branding Utilities
Handles high-resolution logo loading, margin cropping, caching, and base64 encoding.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PRIMARY_LOGO_PATH = PROJECT_ROOT / "logo.png"
STATIC_LOGO_RETINA = PROJECT_ROOT / "ui" / "static" / "logo_retina.png"
STATIC_LOGO_THUMB = PROJECT_ROOT / "ui" / "static" / "logo_256.png"


def ensure_retina_logo() -> Path:
    """
    Ensures a tightly cropped, high-resolution retina logo exists.
    Removes massive unneeded blank margins and scales to 512px with Lanczos.
    """
    if STATIC_LOGO_RETINA.exists() and STATIC_LOGO_RETINA.stat().st_size > 0:
        return STATIC_LOGO_RETINA

    if not PRIMARY_LOGO_PATH.exists():
        return PRIMARY_LOGO_PATH

    try:
        from PIL import Image
        import numpy as np

        STATIC_LOGO_RETINA.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(PRIMARY_LOGO_PATH)
        arr = np.array(img)

        # Detect non-white graphic bounding box
        is_not_white = (arr < 250).any(axis=2)
        rows = np.any(is_not_white, axis=1)
        cols = np.any(is_not_white, axis=0)

        if np.any(rows) and np.any(cols):
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]

            margin = 15
            crop_box = (
                max(0, cmin - margin),
                max(0, rmin - margin),
                min(img.width, cmax + margin),
                min(img.height, rmax + margin),
            )
            cropped = img.crop(crop_box)
        else:
            cropped = img

        scale = 512 / max(cropped.width, 1)
        h = int(cropped.height * scale)
        retina = cropped.resize((512, h), Image.Resampling.LANCZOS)
        retina.save(STATIC_LOGO_RETINA, optimize=True, quality=95)
        return STATIC_LOGO_RETINA
    except Exception:
        return PRIMARY_LOGO_PATH


def get_logo_path() -> Path:
    """Returns the primary project logo path (logo.png)."""
    return PRIMARY_LOGO_PATH


def get_retina_logo_path() -> Path:
    """Returns the cropped retina logo path."""
    return ensure_retina_logo()


@lru_cache(maxsize=1)
def get_logo_base64() -> str:
    """
    Returns base64-encoded PNG data of the high-resolution cropped project logo.
    Cached in-memory to ensure zero overhead on UI reruns.
    """
    target = ensure_retina_logo()
    if target.exists():
        try:
            raw_bytes = target.read_bytes()
            return base64.b64encode(raw_bytes).decode("utf-8")
        except Exception:
            return ""
    return ""

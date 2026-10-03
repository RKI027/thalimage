"""Where things sit relative to a source checkout.

Only meaningful when running from the repository (an editable install or
`uv run` in a checkout). An installed wheel lives in site-packages, so
anything that must work there takes its location from settings instead
(see Settings.frontend_dir).
"""

from pathlib import Path

# backend/src/thalimage/paths.py -> the repository root
REPO_ROOT = Path(__file__).resolve().parents[3]

# Where `pnpm build` writes the SPA in a checkout.
CHECKOUT_FRONTEND_DIR = REPO_ROOT / "frontend" / "build"

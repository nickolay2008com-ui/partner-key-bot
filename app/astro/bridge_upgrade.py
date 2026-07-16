from __future__ import annotations

from app.astro import product_blocks as _product_blocks
from app.astro.sign_bridge import _mechanic as _moon_sign_mechanic

# Compatibility for the full emotional bridge: the sign mechanic lives in
# sign_bridge, while the preserved implementation expects it on product_blocks.
if not hasattr(_product_blocks, "_mechanic"):
    _product_blocks._mechanic = _moon_sign_mechanic

from app.astro.bridge_upgrade_legacy import *  # noqa: F401,F403,E402

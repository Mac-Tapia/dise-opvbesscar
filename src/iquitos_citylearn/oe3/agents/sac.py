from __future__ import annotations

from typing import Any, Optional

def make_sac(env: Any, **kwargs) -> Any:
    from citylearn.agents.sac import SAC  # type: ignore
    try:
        return SAC(env, **kwargs)
    except TypeError:
        return SAC(env=env, **kwargs)

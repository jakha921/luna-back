from fastapi import Request
from fastapi_cache import FastAPICache

def user_cache_key_builder(
    func,
    namespace: str = "",
    request: Request = None,
    *args,
    **kwargs,
) -> str:
    prefix = FastAPICache.get_prefix()
    user_id = kwargs.get("telegram_id") or request.path_params.get("telegram_id")
    return f"{prefix}:user_cache:{user_id}"

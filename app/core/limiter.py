from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Initializes the rate limiter using the client's IP address and our Redis instance
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
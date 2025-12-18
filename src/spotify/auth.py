from typing import Any

from spotipy.oauth2 import SpotifyOAuth

from src.config.config_loader import get_token_path
from src.config.models import SpotifyConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SpotifyAuthManager:
    def __init__(self, config: SpotifyConfig) -> None:
        self.config = config
        self.token_path = get_token_path()
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        self.sp_oauth = SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scope=" ".join(config.scopes),
            cache_path=str(self.token_path),
            open_browser=False,
        )

    def get_auth_url(self) -> str:
        return self.sp_oauth.get_authorize_url()

    def authenticate_with_code(self, redirect_url: str) -> dict[str, Any]:
        code = self.sp_oauth.parse_response_code(redirect_url)

        if not code:
            raise ValueError(
                "Invalid redirect URL - no authorization code found. "
                "Please make sure you pasted the complete redirect URL."
            )

        return self.sp_oauth.get_access_token(code, as_dict=True, check_cache=False)

    def authenticate(self, auto_open_browser: bool = True) -> dict[str, Any]:
        token_info = self.sp_oauth.get_cached_token()

        if token_info:
            if self.sp_oauth.is_token_expired(token_info):
                token_info = self.sp_oauth.refresh_access_token(token_info["refresh_token"])
            return token_info

        raise RuntimeError("No cached token - use interactive authentication flow")

    def get_valid_token(self) -> str:
        token_info = self.sp_oauth.get_cached_token()

        if not token_info:
            logger.info("No token found, authenticating...")
            token_info = self.authenticate()

        if self.sp_oauth.is_token_expired(token_info):
            logger.info("Token expired, refreshing...")
            token_info = self.sp_oauth.refresh_access_token(token_info["refresh_token"])

        return token_info["access_token"]

    def is_authenticated(self) -> bool:
        try:
            token_info = self.sp_oauth.get_cached_token()
            return token_info is not None
        except Exception:
            return False

    def get_token_info(self) -> dict[str, Any] | None:
        try:
            return self.sp_oauth.get_cached_token()
        except Exception:
            return None

    def clear_token(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()
            logger.info("Authentication token cleared")

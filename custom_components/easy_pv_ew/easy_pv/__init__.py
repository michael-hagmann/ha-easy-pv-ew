"""Easy PV."""

import logging
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ContentTypeError

from .redact import redact

LOG = logging.getLogger(__name__)
BASE_URL = "https://inverter-en.easycharging-tech.com/prod-api"
HEADERS = {
    "app": "EasyPV",
    "app-type": "1",
    "app-version": "2.4.0",
    "user-agent": "Easy PV/2.4.0",
    "content-language": "en_US",
}

HTTP_OK = 200
HTTP_UNAUTHORIZED = 401


class BaseError(Exception):
    """Base exception for Easy PV client errors."""


class ApiError(BaseError):
    """Error raised during API operations."""

    def __init__(self, msg: str, code: int, details: str) -> None:
        """Initialize the BaseError with a message, code, and details."""
        super().__init__(f"{msg}: [{code}] {details}")


class LoginError(ApiError):
    """Error raised for login errors."""

    def __init__(self, code: int, msg: str) -> None:
        """Initialize the LoginError with a code and message."""
        super().__init__("Login failed", code, msg)


class InvalidResponseError(BaseError):
    """Error raised for invalid responses from the API."""

    def __init__(self) -> None:
        """Initialize the InvalidResponseError."""
        super().__init__("Invalid response from API")


class CommunicationError(BaseError):
    """Error raised when the API cannot be reached (network, DNS, timeout)."""

    def __init__(self, details: str) -> None:
        """Initialize the CommunicationError with details."""
        super().__init__(f"Cannot reach Easy PV API: {details}")


class EasyPVClient:
    """
    Client for interacting with the Easy PV API.

    Provides methods for authentication and retrieving station and device data.
    The aiohttp session is owned by the caller (in Home Assistant the shared
    session from ``async_get_clientsession``).
    """

    def __init__(self, session: ClientSession) -> None:
        """Initialize the EasyPVClient instance."""
        self._session = session
        self._token: str | None = None

    @property
    def token(self) -> str | None:
        """Return the current token."""
        return self._token

    @property
    def is_logged_in(self) -> bool:
        """Check if the client is logged in."""
        return self._token is not None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        auth: bool = True,
        log_response: bool = False,
    ) -> dict[str, Any]:
        """
        Send a request and return the decoded JSON body.

        Raises LoginError if the token is rejected (HTTP 401 or code 401 in
        the body). With log_response the anonymized body is logged on debug
        level; never set it for login or user info responses.
        """
        headers = dict(HEADERS)
        if auth:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with self._session.request(
                method,
                f"{BASE_URL}{path}",
                params=params,
                json=json,
                headers=headers,
            ) as response:
                if auth and response.status == HTTP_UNAUTHORIZED:
                    raise LoginError(HTTP_UNAUTHORIZED, "token rejected")
                if response.status != HTTP_OK:
                    raise InvalidResponseError
                data = await response.json()
        except (ContentTypeError, ValueError) as err:
            # Not JSON (maintenance page, captive portal) or broken JSON.
            raise InvalidResponseError from err
        except (ClientError, TimeoutError) as err:
            raise CommunicationError(_describe(err)) from err

        if not isinstance(data, dict) or "code" not in data:
            raise InvalidResponseError

        if log_response and LOG.isEnabledFor(logging.DEBUG):
            LOG.debug("Response %s %s: %s", method, path, redact(data))

        if auth and data["code"] == HTTP_UNAUTHORIZED:
            raise LoginError(data["code"], data.get("msg", ""))

        return data

    async def login_with_password(self, username: str, password: str) -> None:
        """Login to the Easy PV service."""
        data = await self._request(
            "POST",
            "/api/sys/v2/passLogin",
            json={"num": username, "password": password},
            auth=False,
        )
        if data["code"] == HTTP_OK and (data.get("data") or {}).get("token"):
            self._token = data["data"]["token"]
            return

        raise LoginError(data["code"], data.get("msg", ""))

    async def login_with_token(self, token: str) -> None:
        """Login to the Easy PV service using a token."""
        try:
            self._token = token
            await self.get_user_info()
        except:
            self._token = None
            raise

    def logout(self) -> None:
        """Log out from the Easy PV service."""
        self._token = None

    async def get_user_info(self) -> Any:
        """
        Get the user information if logged in.

        A rejected token (401) raises LoginError in _request; any other error
        code is a server problem and raises ApiError, so that Home Assistant
        retries instead of asking for the credentials again.
        """
        data = await self._request("GET", "/api/user/v2/selectUserInfo")
        if data["code"] == HTTP_OK and isinstance(data.get("data"), dict):
            return data["data"]

        raise ApiError("Failed to get user info", data["code"], data.get("msg", ""))

    async def get_stations(self) -> list[Any]:
        """Get the list of stations."""
        data = await self._request(
            "GET",
            "/api/powerStation/v3/getStationList",
            params={"pageNum": "1", "pageSize": "1000"},
            log_response=True,
        )
        if data["code"] == HTTP_OK and isinstance(data.get("data"), dict):
            rows = data["data"].get("rows")
            if rows is None:
                return []
            if isinstance(rows, list):
                return rows

        raise ApiError("Failed to get stations", data["code"], data.get("msg", ""))

    async def get_station_devices(self, station_id: str) -> list[Any]:
        """Get the devices of a station."""
        data = await self._request(
            "GET",
            "/api/powerStation/v2/getPowerList",
            params={"powerId": station_id},
            log_response=True,
        )
        if data["code"] == HTTP_OK and isinstance(data.get("data"), list):
            # An empty list is valid: a station without devices.
            return data["data"]

        raise ApiError("Failed to get devices", data["code"], data.get("msg", ""))

    async def get_device_data(
        self, station_id: str, device_id: str, date: str | None = None
    ) -> dict[str, Any]:
        """Get the data of a specific device."""
        if not date:
            now = datetime.now(tz=UTC)
            date = f"{now.year}-{now.month:02d}"

        data = await self._request(
            "GET",
            "/api/powerStation/v3/getDeviceDataInfo",
            params={"deviceId": device_id, "stationId": station_id, "date": date},
            log_response=True,
        )
        if data["code"] == HTTP_OK and isinstance(data.get("data"), dict):
            return data["data"]

        raise ApiError("Failed to get device data", data["code"], data.get("msg", ""))


def _describe(err: Exception) -> str:
    """
    Describe a network error without request details.

    The repr and str of ClientResponseError contain the request info with all
    headers (including the token) or the URL with station and device IDs.
    """
    if isinstance(err, ClientResponseError):
        return f"{type(err).__name__} (HTTP {err.status})"
    return str(err) or type(err).__name__

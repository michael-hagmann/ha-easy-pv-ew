"""Easy PV."""

import logging
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientSession

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


class EasyPVClient:
    """
    Client for interacting with the Easy PV API.

    Provides methods for authentication and retrieving station and device data.
    """

    def __init__(self) -> None:
        """Initialize the EasyPVClient instance."""
        self._token: str | None = None

    @property
    def token(self) -> str | None:
        """Return the current token."""
        return self._token

    @property
    def is_logged_in(self) -> bool:
        """Check if the client is logged in."""
        return self._token is not None

    async def login_with_password(self, username: str, password: str) -> None:
        """Login to the Easy PV service."""
        async with (
            ClientSession() as session,
            session.post(
                f"{BASE_URL}/api/sys/v2/passLogin",
                json={"num": username, "password": password},
                headers=HEADERS,
            ) as response,
        ):
            if response.status == HTTP_OK:
                data = await response.json()
                if data["code"] == HTTP_OK and data["data"]["token"]:
                    self._token = data["data"]["token"]
                    return

                raise LoginError(data["code"], data["msg"])

            raise InvalidResponseError

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
        """Get the user information if logged in."""
        async with (
            ClientSession() as session,
            session.get(
                f"{BASE_URL}/api/user/v2/selectUserInfo",
                headers={**HEADERS, "Authorization": f"Bearer {self._token}"},
            ) as response,
        ):
            if response.status == HTTP_OK:
                data = await response.json()
                if data["code"] == HTTP_OK and data["data"]:
                    return data["data"]

                raise LoginError(data["code"], data["msg"])

            raise InvalidResponseError

    async def get_stations(self) -> list[Any]:
        """Get the list of stations."""
        async with (
            ClientSession() as session,
            session.get(
                f"{BASE_URL}/api/powerStation/v3/getStationList?pageNum=1&pageSize=1000",
                headers={**HEADERS, "Authorization": f"Bearer {self._token}"},
            ) as response,
        ):
            if response.status == HTTP_OK:
                data = await response.json()
                if data["code"] == HTTP_OK and data["data"]["rows"]:
                    return data["data"]["rows"]

                raise ApiError("Failed to get stations", data["code"], data["msg"])

            raise InvalidResponseError

    async def get_station_devices(self, station_id: str) -> list[Any]:
        """Get the devices of a station."""
        async with (
            ClientSession() as session,
            session.get(
                f"{BASE_URL}/api/powerStation/v2/getPowerList?powerId={station_id}",
                headers={**HEADERS, "Authorization": f"Bearer {self._token}"},
            ) as response,
        ):
            if response.status == HTTP_OK:
                data = await response.json()
                if data["code"] == HTTP_OK and data["data"]:
                    return data["data"]

                raise ApiError("Failed to get devices", data["code"], data["msg"])

            raise InvalidResponseError

    async def get_device_data(
        self, station_id: str, device_id: str, date: str | None = None
    ) -> dict[str, Any]:
        """Get the data of a specific device."""
        if not date:
            now = datetime.now(tz=UTC)
            date = f"{now.year}-{now.month:02d}"

        async with (
            ClientSession() as session,
            session.get(
                f"{BASE_URL}/api/powerStation/v3/getDeviceDataInfo?deviceId={device_id}&stationId={station_id}&date={date}",
                headers={**HEADERS, "Authorization": f"Bearer {self._token}"},
            ) as response,
        ):
            if response.status == HTTP_OK:
                data = await response.json()
                if data["code"] == HTTP_OK and data["data"]:
                    return data["data"]

                raise ApiError("Failed to get device data", data["code"], data["msg"])

            raise InvalidResponseError

from __future__ import annotations

from typing import Any, TypedDict

from netbox_cli.client import NetBoxClient, NetBoxClientError
from netbox_cli.service.auth_service import (
    AuthenticationError,
    AuthService,
    SuperuserRequiredError,
)


class UserDetails(TypedDict):
    id: object
    username: object
    display: object
    full_name: str | None
    email: object
    active: object
    last_login: object
    date_joined: object
    groups: list[str]


class StatusResult(TypedDict, total=False):
    url: str
    endpoint: str
    reachable: bool
    token_configured: bool
    token_version: int | None
    authenticated: bool
    superuser: bool
    authorized: bool
    user: object
    user_details: UserDetails | None
    status_code: int | None
    message: str


class StatusService:
    def __init__(
        self,
        client: NetBoxClient,
        *,
        url: str,
        token_configured: bool,
        token_version: int | None = None,
    ) -> None:
        self.client = client
        self.url = url
        self.token_configured = token_configured
        self.token_version = token_version

    def check(self) -> StatusResult:
        result: StatusResult = {
            "url": self.url,
            "endpoint": f"{self.url.rstrip('/')}/api/authentication-check/",
            "reachable": False,
            "token_configured": self.token_configured,
            "token_version": self.token_version,
            "authenticated": False,
            "superuser": False,
            "authorized": False,
            "user": None,
            "user_details": None,
        }
        try:
            user = AuthService(self.client).validate()
        except NetBoxClientError as error:
            # Qualquer resposta HTTP prova que a URL e o NetBox foram alcançados.
            result["reachable"] = error.status_code is not None
            result["status_code"] = error.status_code
            result["message"] = str(error)
        except AuthenticationError as error:
            result["reachable"] = True
            result["message"] = str(error)
        else:
            result["reachable"] = True
            result["authenticated"] = True
            result["user"] = user.get("username") or user.get("display")
            result["user_details"] = _user_details(user)
            try:
                AuthService(self.client).require_superuser()
            except SuperuserRequiredError as error:
                result["message"] = str(error)
            except NetBoxClientError as error:
                result["status_code"] = error.status_code
                result["message"] = str(error)
            else:
                result["superuser"] = True
                result["authorized"] = True
        return result


def _user_details(user: dict[str, Any]) -> UserDetails:
    first_name = str(user.get("first_name") or "").strip()
    last_name = str(user.get("last_name") or "").strip()
    full_name = " ".join(part for part in (first_name, last_name) if part)
    groups = _related_names(user.get("groups"))
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "display": user.get("display"),
        "full_name": full_name or None,
        "email": user.get("email") or None,
        "active": user.get("is_active"),
        "last_login": user.get("last_login"),
        "date_joined": user.get("date_joined"),
        "groups": groups,
    }


def _related_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name") or item.get("display")
        else:
            name = item
        if name is not None:
            names.append(str(name))
    return names

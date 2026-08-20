from __future__ import annotations

from typing import Any

from netbox_cli.client import NetBoxClient, NetBoxClientError
from netbox_cli.service.auth_service import AuthenticationError, AuthService


class StatusService:
    def __init__(
        self, client: NetBoxClient, *, url: str, token_configured: bool
    ) -> None:
        self.client = client
        self.url = url
        self.token_configured = token_configured

    def check(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "url": self.url,
            "reachable": False,
            "token_configured": self.token_configured,
            "authenticated": False,
            "user": None,
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
        return result

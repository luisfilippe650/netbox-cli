from __future__ import annotations

from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.exceptions import NetBoxCLIError


class AuthenticationError(NetBoxCLIError):
    """O NetBox não retornou uma autenticação utilizável."""


class AuthService:
    ENDPOINT = "/api/users/tokens/provision/"

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def login(self, username: str, password: str) -> str:
        result = self.client.post(
            self.ENDPOINT,
            {
                "username": username,
                "password": password,
                "description": "netbox-cli",
                "write_enabled": True,
            },
        )
        if not isinstance(result, dict) or not result.get("token"):
            raise AuthenticationError("O NetBox não retornou o token de acesso")
        return str(result["token"])

    def validate(self) -> dict:
        result = self.client.get("/api/authentication-check/")
        if not isinstance(result, dict):
            raise AuthenticationError("Resposta de autenticação inválida")
        return result

from __future__ import annotations

from dataclasses import dataclass

from netbox_cli.client.netbox_client import NetBoxClient, NetBoxClientError
from netbox_cli.exceptions import NetBoxCLIError


class AuthenticationError(NetBoxCLIError):
    """O NetBox não retornou uma autenticação utilizável."""


class SuperuserRequiredError(NetBoxCLIError):
    """O usuário autenticado não é superusuário do NetBox."""


@dataclass(frozen=True, slots=True)
class ProvisionedToken:
    id: int
    value: str
    version: int


class AuthService:
    PROVISION_ENDPOINT = "/api/users/tokens/provision/"
    AUTHENTICATION_ENDPOINT = "/api/authentication-check/"
    # O NetBox protege esta rota com IsSuperuser; authentication-check apenas
    # confirma a identidade e não expõe o campo is_superuser.
    SUPERUSER_ENDPOINT = "/api/plugins/installed-plugins/"
    TOKENS_ENDPOINT = "/api/users/tokens/"

    def __init__(self, client: NetBoxClient) -> None:
        self.client = client

    def login(self, username: str, password: str) -> str:
        """Mantém a API anterior; novos fluxos devem usar provision()."""

        return self.provision(username, password).value

    def provision(self, username: str, password: str) -> ProvisionedToken:
        result = self.client.post(
            self.PROVISION_ENDPOINT,
            {
                "username": username,
                "password": password,
                "description": "netbox-cli",
                "write_enabled": True,
                "version": 2,
            },
        )

        if (
            not isinstance(result, dict)
            or not result.get("token")
            or not result.get("id")
        ):
            raise AuthenticationError("O NetBox não retornou o token de acesso")

        version = result.get("version")

        if version != 2:
            raise AuthenticationError(
                "O NetBox não provisionou um token v2 compatível com esta CLI"
            )

        token = str(result["token"])

        if token.startswith("nbt_"):
            value = token
        else:
            key = result.get("key")

            if not key:
                raise AuthenticationError("O NetBox não retornou a chave do token v2")

            value = f"nbt_{key}.{token}"

        return ProvisionedToken(id=int(result["id"]), value=value, version=2)

    def validate(self) -> dict:
        result = self.client.get(self.AUTHENTICATION_ENDPOINT)

        if not isinstance(result, dict):
            raise AuthenticationError("Resposta de autenticação inválida")

        return result

    def require_superuser(self) -> None:
        try:
            self.client.get(self.SUPERUSER_ENDPOINT)
        except NetBoxClientError as error:
            if error.status_code in {401, 403}:
                raise SuperuserRequiredError(
                    "A NetBox CLI é exclusiva para superusuários. "
                    "Este usuário não possui acesso de superusuário."
                ) from error

            raise

    def revoke(self, token_id: int) -> None:
        self.client.delete(f"{self.TOKENS_ENDPOINT}{token_id}/")

    def find_token_id(self, token: str) -> int | None:
        if not token.startswith("nbt_") or "." not in token:
            return None

        key = token.removeprefix("nbt_").split(".", 1)[0]
        result = self.client.get(
            self.TOKENS_ENDPOINT,
            params={"key": key, "limit": 2},
        )

        if not isinstance(result, dict) or not isinstance(result.get("results"), list):
            raise AuthenticationError("Resposta inválida ao localizar o token atual")

        matches = result["results"]

        if len(matches) != 1 or not isinstance(matches[0], dict):
            return None

        token_id = matches[0].get("id")

        return token_id if isinstance(token_id, int) else None

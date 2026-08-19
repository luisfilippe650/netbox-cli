from netbox_cli.client import NetBoxClient


def test_legacy_token_uses_token_scheme() -> None:
    client = NetBoxClient("http://netbox.example", "legacy-token")

    assert client.session.headers["Authorization"] == "Token legacy-token"


def test_v2_token_uses_bearer_scheme() -> None:
    client = NetBoxClient("http://netbox.example", "nbt_key.secret")

    assert client.session.headers["Authorization"] == "Bearer nbt_key.secret"

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from netbox_cli.app import app
from netbox_cli.client import NetBoxClientError
from netbox_cli.config import ConfigStore, Settings
from netbox_cli.runtime import RuntimeOptions, configure
from netbox_cli.schemas.devices import AddDevice
from netbox_cli.schemas.organization import AddRegion
from netbox_cli.service.devices import DevicesService
from netbox_cli.service.organization import RegionsService


class FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = iter(responses)
        self.calls: list[tuple[str, str, Any]] = []

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append(("GET", endpoint, params))
        return next(self.responses)

    def post(self, endpoint: str, data: dict[str, Any]) -> Any:
        self.calls.append(("POST", endpoint, data))
        return next(self.responses)

    def patch(self, endpoint: str, data: dict[str, Any]) -> Any:
        self.calls.append(("PATCH", endpoint, data))
        return next(self.responses)


@pytest.fixture(autouse=True)
def reset_runtime_options() -> Any:
    configure(RuntimeOptions())
    yield
    configure(RuntimeOptions())


def test_environment_settings_work_without_creating_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "missing.yaml"
    monkeypatch.setenv("NETBOX_URL", "https://netbox.example/")
    monkeypatch.setenv("NETBOX_TOKEN", "nbt_key.token")
    monkeypatch.setenv("NETBOX_TIMEOUT", "7.5")

    settings = ConfigStore(path).load(require_token=True)

    assert settings.url == "https://netbox.example"
    assert settings.token == "nbt_key.token"
    assert settings.timeout == 7.5
    assert not path.exists()


def test_complete_environment_configuration_does_not_read_local_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("invalid: [", encoding="utf-8")
    monkeypatch.setenv("NETBOX_URL", "https://netbox.example")
    monkeypatch.setenv("NETBOX_TOKEN", "nbt_key.token")
    monkeypatch.setenv("NETBOX_TIMEOUT", "20")

    settings = ConfigStore(path).load(require_token=True)

    assert settings.url == "https://netbox.example"
    assert settings.token == "nbt_key.token"


def test_environment_token_is_not_persisted_by_file_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.yaml"
    store = ConfigStore(path)
    store.save(Settings(url="https://file.example"))
    monkeypatch.setenv("NETBOX_URL", "https://environment.example")
    monkeypatch.setenv("NETBOX_TOKEN", "environment-secret")

    store.save_url("https://new-file.example")
    persisted = store.load(use_environment=False)

    assert persisted.url == "https://new-file.example"
    assert persisted.token == ""


def test_explicit_options_take_precedence_over_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NETBOX_URL", "https://environment.example")
    monkeypatch.setenv("NETBOX_TOKEN", "environment-token")
    monkeypatch.setenv("NETBOX_TIMEOUT", "30")

    settings = ConfigStore(tmp_path / "missing.yaml").load(
        url="https://flag.example",
        token="flag-token",
        timeout=2,
    )

    assert settings == Settings(
        url="https://flag.example",
        token="flag-token",
        token_url="https://flag.example",
        timeout=2,
    )


def test_overridden_url_never_reuses_file_token(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    store = ConfigStore(path)
    store.save(
        Settings(
            url="https://old.example",
            token="old-token",
            token_url="https://old.example",
        )
    )

    settings = store.load(url="https://new.example")

    assert settings.url == "https://new.example"
    assert settings.token == ""


def test_ensure_creates_updates_and_then_becomes_unchanged() -> None:
    create_client = FakeClient(
        [{"count": 0, "results": []}, {"id": 1, "name": "Sudeste"}]
    )
    created = RegionsService(create_client).ensure(  # type: ignore[arg-type]
        AddRegion(name="Sudeste")
    )
    assert created["action"] == "created"
    assert create_client.calls[-1][0] == "POST"

    current = {"id": 1, "name": "Sudeste", "slug": "sudeste", "description": ""}
    unchanged_client = FakeClient([{"count": 1, "results": [current]}])
    unchanged = RegionsService(unchanged_client).ensure(  # type: ignore[arg-type]
        AddRegion(name="Sudeste")
    )
    assert unchanged["changed"] is False
    assert [call[0] for call in unchanged_client.calls] == ["GET"]

    update_client = FakeClient(
        [
            {"count": 1, "results": [current]},
            {**current, "description": "Operação"},
        ]
    )
    updated = RegionsService(update_client).ensure(  # type: ignore[arg-type]
        AddRegion(name="Sudeste", description="Operação")
    )
    assert updated["action"] == "updated"
    assert update_client.calls[-1] == (
        "PATCH",
        "/api/dcim/regions/1/",
        {"description": "Operação"},
    )


def test_ensure_dry_run_reports_change_without_mutating() -> None:
    current = {"id": 1, "name": "Sudeste", "slug": "sudeste", "description": ""}
    client = FakeClient([{"count": 1, "results": [current]}])

    result = RegionsService(client).ensure(  # type: ignore[arg-type]
        AddRegion(name="Sudeste", description="Nova"), dry_run=True
    )

    assert result["action"] == "would_update"
    assert result["changes"] == {"description": "Nova"}
    assert [call[0] for call in client.calls] == ["GET"]


@pytest.mark.parametrize("position", [1.0, 1.5])
def test_device_ensure_treats_numeric_position_as_unchanged(position: float) -> None:
    current = {
        "id": 9,
        "name": "server-01",
        "role": {"id": 4},
        "device_type": {"id": 4},
        "site": {"id": 1},
        "rack": {"id": 14},
        "position": position,
        "face": {"value": "front"},
    }
    client = FakeClient([{"count": 1, "results": [current]}])

    result = DevicesService(client).ensure(  # type: ignore[arg-type]
        AddDevice(
            name="server-01",
            role=4,
            device_type=4,
            site=1,
            rack=14,
            position=position,
        )
    )

    assert result["action"] == "unchanged"
    assert result["changed"] is False
    assert [call[0] for call in client.calls] == ["GET"]


def test_device_move_dry_run_resolves_target_without_patch() -> None:
    client = FakeClient(
        [
            {"count": 1, "results": [{"id": 7, "name": "srv01"}]},
            {
                "count": 1,
                "results": [
                    {
                        "id": 4,
                        "name": "R01",
                        "site": {"id": 1},
                        "location": None,
                    }
                ],
            },
        ]
    )

    result = DevicesService(client).move(  # type: ignore[arg-type]
        "srv01",
        rack_name="R01",
        position=10,
        dry_run=True,
    )

    assert result["action"] == "would_move"
    assert result["payload"]["rack"] == 4
    assert [call[0] for call in client.calls] == ["GET", "GET"]


def test_global_json_mode_emits_parseable_structured_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing.yaml"
    for name in ("NETBOX_URL", "NETBOX_TOKEN", "NETBOX_TIMEOUT", "NETBOX_CONFIG"):
        monkeypatch.delenv(name, raising=False)

    result = CliRunner().invoke(
        app,
        ["--config", str(missing), "--output", "json", "devices", "get", "1"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["code"] == "configuration_error"
    assert not missing.exists()


def test_ignore_not_found_returns_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    from netbox_cli.cli import common

    class MissingService:
        def delete(self, item_id: int) -> None:
            raise NetBoxClientError("missing", status_code=404)

    monkeypatch.setattr(common, "make_service", lambda service_class: MissingService())

    result = common.delete_resource(
        MissingService,
        9,
        resource="device",
        ignore_not_found=True,
    )

    assert result["changed"] is False
    assert result["not_found"] is True


def test_regular_client_creation_does_not_repeat_superuser_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from netbox_cli.cli import common

    class FakeStore:
        def __init__(self, path: Path | None = None) -> None:
            pass

        def load(self, **kwargs: Any) -> Settings:
            return Settings(
                url="https://netbox.example",
                token="nbt_key.token",
                token_url="https://netbox.example",
            )

    constructed: list[dict[str, Any]] = []

    class ClientWithoutRequests:
        def __init__(self, **kwargs: Any) -> None:
            constructed.append(kwargs)

    monkeypatch.setattr(common, "ConfigStore", FakeStore)
    monkeypatch.setattr(common, "NetBoxClient", ClientWithoutRequests)

    common.make_client()

    assert constructed == [
        {
            "base_url": "https://netbox.example",
            "token": "nbt_key.token",
            "timeout": 15,
        }
    ]
    common._open_clients.clear()

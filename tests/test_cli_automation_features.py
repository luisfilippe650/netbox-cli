from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner
from rich.console import Console

from netbox_cli.app import app
from netbox_cli.client import NetBoxClientError
from netbox_cli.config import ConfigStore, Settings
from netbox_cli.runtime import RuntimeOptions, configure
from netbox_cli.presentation.output import OutputFormat, render
from netbox_cli.presentation.errors import show_error
from netbox_cli.schemas.devices import (
    AddCable,
    AddDevice,
    AddDeviceRole,
    AddDeviceType,
    AddFrontPort,
    AddInterface,
    UpdateDeviceRole,
)
from netbox_cli.schemas.organization import AddRegion
from netbox_cli.schemas.organization.sites_dto import AddSite
from netbox_cli.service.devices import (
    CablesService,
    DeviceRolesService,
    DevicesService,
    DeviceTypesService,
    FrontPortsService,
    InterfacesService,
)
from netbox_cli.service.organization import RegionsService, SitesService


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


def test_device_role_crud_payload_uses_endpoint_and_generated_slug() -> None:
    client = FakeClient([{"id": 4, "name": "Servidor"}])

    result = DeviceRolesService(client).create(  # type: ignore[arg-type]
        AddDeviceRole(name="Servidor", color="2196f3", vm_role=False)
    )

    assert result["id"] == 4
    assert client.calls == [
        (
            "POST",
            "/api/dcim/device-roles/",
            {
                "name": "Servidor",
                "slug": "servidor",
                "color": "2196f3",
                "vm_role": False,
                "description": "",
            },
        )
    ]


def test_device_payload_resolves_role_name_to_id() -> None:
    client = FakeClient(
        [{"count": 1, "results": [{"id": 4, "name": "Servidor"}]}]
    )

    payload = DevicesService(client).build_payload(  # type: ignore[arg-type]
        AddDevice(name="server-01", role="Servidor", device_type=2, site=1)
    )

    assert payload["role"] == 4
    assert client.calls == [
        (
            "GET",
            "/api/dcim/device-roles/",
                {"q": "Servidor", "limit": 0},
        )
    ]


def test_device_payload_keeps_numeric_role_without_lookup() -> None:
    client = FakeClient([])

    payload = DevicesService(client).build_payload(  # type: ignore[arg-type]
        AddDevice(name="server-01", role="4", device_type=2, site=1)
    )

    assert payload["role"] == 4
    assert client.calls == []


def test_site_payload_resolves_region_slug() -> None:
    client = FakeClient(
        [{"count": 1, "results": [{"id": 3, "name": "Sudeste", "slug": "sudeste"}]}]
    )

    payload = SitesService(client).build_payload(  # type: ignore[arg-type]
        AddSite(name="Site Teste", region="sudeste")
    )

    assert payload["region"] == 3
    assert client.calls == [
        ("GET", "/api/dcim/regions/", {"q": "sudeste", "limit": 0})
    ]


def test_device_type_payload_resolves_manufacturer_name() -> None:
    client = FakeClient(
        [{"count": 1, "results": [{"id": 11, "name": "Teste", "slug": "teste"}]}]
    )

    payload = DeviceTypesService(client).build_payload(  # type: ignore[arg-type]
        AddDeviceType(manufacturer="Teste", model="Servidor 1U", u_height=1)
    )

    assert payload["manufacturer"] == 11
    assert payload["slug"] == "servidor-1u"


def test_device_type_ensure_uses_resolved_manufacturer_filter() -> None:
    current = {
        "id": 42,
        "manufacturer": {"id": 11},
        "model": "Servidor 1U",
        "slug": "servidor-1u",
        "u_height": 1.0,
    }
    client = FakeClient(
        [
            {"count": 1, "results": [{"id": 11, "name": "Teste", "slug": "teste"}]},
            {"count": 1, "results": [current]},
        ]
    )

    result = DeviceTypesService(client).ensure(  # type: ignore[arg-type]
        AddDeviceType(manufacturer="teste", model="Servidor 1U", u_height=1),
        identity_field="model",
    )

    assert result["changed"] is False
    assert client.calls[-1] == (
        "GET",
        "/api/dcim/device-types/",
        {"manufacturer_id": 11, "model": "Servidor 1U", "limit": 0},
    )


def test_device_payload_resolves_all_relationships_by_name_or_slug() -> None:
    client = FakeClient(
        [
            {"count": 1, "results": [{"id": 4, "name": "Servidor", "slug": "servidor"}]},
            {"count": 1, "results": [{"id": 1, "name": "Site Teste", "slug": "site-teste"}]},
            {"count": 1, "results": [{"id": 42, "model": "Servidor 1U", "slug": "servidor-1u"}]},
            {"count": 1, "results": [{"id": 3, "name": "Sala Teste", "slug": "sala-teste"}]},
            {"count": 1, "results": [{"id": 8, "name": "Rack-01"}]},
        ]
    )

    payload = DevicesService(client).build_payload(  # type: ignore[arg-type]
        AddDevice(
            name="server-01",
            role="servidor",
            device_type="Servidor 1U",
            site="site-teste",
            location="Sala Teste",
            rack="Rack-01",
        )
    )

    assert payload["role"] == 4
    assert payload["device_type"] == 42
    assert payload["site"] == 1
    assert payload["location"] == 3
    assert payload["rack"] == 8
    assert client.calls[-1] == (
        "GET",
        "/api/dcim/racks/",
        {"site_id": 1, "location_id": 3, "q": "Rack-01", "limit": 0},
    )


def test_device_role_update_requires_at_least_one_value() -> None:
    with pytest.raises(ValueError, match="ao menos um campo"):
        UpdateDeviceRole(name=None, color=None, vm_role=None, description=None)


def test_interface_payload_resolves_device_name() -> None:
    client = FakeClient(
        [{"count": 1, "results": [{"id": 7, "name": "Switch-01"}]}]
    )

    payload = InterfacesService(client).build_payload(  # type: ignore[arg-type]
        AddInterface(device="Switch-01", name="Gi0/1", type="1000base-t")
    )

    assert payload["device"] == 7
    assert payload["name"] == "Gi0/1"
    assert payload["type"] == "1000base-t"


def test_front_port_payload_maps_rear_port_by_name() -> None:
    client = FakeClient(
        [
            {"count": 1, "results": [{"id": 9, "name": "Patch-01"}]},
            {"count": 1, "results": [{"id": 30, "name": "Rear-01"}]},
        ]
    )

    payload = FrontPortsService(client).build_payload(  # type: ignore[arg-type]
        AddFrontPort(
            device="Patch-01",
            name="Front-01",
            type="8p8c",
            rear_port="Rear-01",
        )
    )

    assert payload["device"] == 9
    assert payload["rear_ports"] == [
        {"rear_port": 30, "position": 1, "rear_port_position": 1}
    ]
    assert client.calls[-1] == (
        "GET",
        "/api/dcim/rear-ports/",
        {"device_id": 9, "name": "Rear-01", "limit": 0},
    )


def test_cable_payload_resolves_both_terminations() -> None:
    client = FakeClient(
        [
            {"count": 1, "results": [{"id": 7, "name": "Switch-01"}]},
            {"count": 1, "results": [{"id": 11, "name": "Gi0/1"}]},
            {"count": 1, "results": [{"id": 9, "name": "Patch-01"}]},
            {"count": 1, "results": [{"id": 21, "name": "Front-01"}]},
        ]
    )

    payload = CablesService(client).build_payload(  # type: ignore[arg-type]
        AddCable(
            a_type="interface",
            a_device="Switch-01",
            a_name="Gi0/1",
            b_type="front-port",
            b_device="Patch-01",
            b_name="Front-01",
            type="cat6",
            label="CAB-01",
        )
    )

    assert payload["a_terminations"] == [
        {"object_type": "dcim.interface", "object_id": 11}
    ]
    assert payload["b_terminations"] == [
        {"object_type": "dcim.frontport", "object_id": 21}
    ]
    assert payload["status"] == "connected"


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
                "retries": 2,
                "backoff": 0.5,
                "verbose": False,
                "debug": False,
            }
    ]
    common._open_clients.clear()


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"id": 10, "name": "Dell"}, "10"),
        (
            {
                "action": "created",
                "changed": True,
                "resource": {"id": 20, "name": "Servidor"},
            },
            "20",
        ),
        (
            {
                "action": "unchanged",
                "changed": False,
                "resource": {"id": 30, "name": "Site Teste"},
            },
            "30",
        ),
    ],
)
def test_id_output_supports_direct_and_ensure_responses(
    response: dict[str, Any], expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    render(response, OutputFormat.id, title="Recurso")

    assert capsys.readouterr().out.strip() == expected


def test_id_output_reports_when_dry_run_create_has_no_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(typer.Exit) as exit_info:
        render(
            {
                "action": "would_create",
                "changed": True,
                "dry_run": True,
                "payload": {"name": "Servidor"},
            },
            OutputFormat.id,
            title="Recurso",
        )

    assert exit_info.value.exit_code == 1
    assert "não retornou um ID" in capsys.readouterr().err


def test_global_id_output_overrides_command_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure(RuntimeOptions(output="id"))

    render({"id": 40}, OutputFormat.json, title="Recurso")

    assert capsys.readouterr().out.strip() == "40"


def test_debug_json_error_includes_context_and_chained_traceback() -> None:
    configure(RuntimeOptions(output="json", debug=True))
    stream = StringIO()

    try:
        try:
            raise OSError("connection refused")
        except OSError as cause:
            raise NetBoxClientError(
                "Falha de conexão",
                method="GET",
                endpoint="/api/dcim/devices/",
                timeout=3,
                attempts=2,
                cause="ConnectionError: connection refused",
            ) from cause
    except NetBoxClientError as error:
        show_error(
            error,
            console=Console(file=stream, force_terminal=False, color_system=None),
        )

    payload = json.loads(stream.getvalue())
    details = payload["error"]
    assert details["method"] == "GET"
    assert details["endpoint"] == "/api/dcim/devices/"
    assert details["timeout"] == 3
    assert details["attempts"] == 2
    assert details["exception"] == "NetBoxClientError"
    assert "OSError: connection refused" in details["traceback"]

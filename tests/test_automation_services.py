from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from netbox_cli.client import NetBoxClientError
from netbox_cli.client.netbox_client import NetBoxClient
from netbox_cli.config import ConfigurationError, ConfigStore, Settings
from typer.testing import CliRunner

from netbox_cli.app import app
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.presentation.details import (
    DetailOutputFormat,
    InventoryOutputFormat,
    render_inventory,
    render_rack,
)
from netbox_cli.service.devices.devices_service import DevicesService
from netbox_cli.service.infrastructure_service import InfrastructureService
from netbox_cli.service.inventory_service import InventoryFilterError, InventoryService
from netbox_cli.service.lookup import (
    ResourceNotFoundError,
    get_all_results,
    get_by_name,
    get_scoped_rack,
)
from netbox_cli.service.organization.sites_service import SitesService
from netbox_cli.service.racks.racks_service import RacksService
from netbox_cli.service.search_service import SearchService
from netbox_cli.service.auth_service import AuthService
from netbox_cli.service.status_service import StatusService


class FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = iter(responses)
        self.calls: list[tuple[str, str, Any]] = []

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append(("GET", endpoint, params))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response

    def patch(self, endpoint: str, data: dict[str, Any]) -> Any:
        self.calls.append(("PATCH", endpoint, data))
        return next(self.responses)

    def post(self, endpoint: str, data: dict[str, Any]) -> Any:
        self.calls.append(("POST", endpoint, data))
        return next(self.responses)


def page(*items: dict[str, Any]) -> dict[str, Any]:
    return {"count": len(items), "results": list(items)}


def test_inspect_combines_device_interfaces_and_ips() -> None:
    client = FakeClient(
        [
            page(
                {
                    "id": 7,
                    "name": "Server-01",
                    "site": {"name": "CPTEC"},
                    "location": {"name": "Datacenter"},
                    "rack": {"name": "RACK-04"},
                    "position": "20.0",
                    "status": {"value": "active", "label": "Active"},
                }
            ),
            page(
                {
                    "name": "eth0",
                    "connected_endpoints": [
                        {"name": "Gi0/12", "device": {"name": "Switch-01"}}
                    ],
                },
                {"name": "ilo", "connected_endpoints": None},
            ),
            page(
                {
                    "address": "10.10.0.23/24",
                    "assigned_object": {"name": "eth0"},
                }
            ),
        ]
    )

    result = DevicesService(client).inspect("server-01")  # type: ignore[arg-type]

    assert result["name"] == "Server-01"
    assert result["interfaces"][0]["name"] == "eth0"
    assert result["interfaces"][0]["connected_device"] == "Switch-01"
    assert result["interfaces"][0]["connected_interface"] == "Gi0/12"
    assert result["ip_addresses"] == [{"interface": "eth0", "address": "10.10.0.23/24"}]
    assert client.calls[1][2] == {"device_id": 7, "limit": 0}


def test_inspect_reports_unknown_device() -> None:
    client = FakeClient([page(), page()])
    with pytest.raises(ResourceNotFoundError, match="não encontrado"):
        DevicesService(client).inspect("missing")  # type: ignore[arg-type]


def test_move_resolves_names_and_updates_location_context() -> None:
    client = FakeClient(
        [
            page({"id": 7, "name": "Server-01"}),
            page(
                {
                    "id": 4,
                    "name": "RACK-02",
                    "site": {"id": 1},
                    "location": {"id": 3},
                }
            ),
            {"id": 7, "name": "Server-01"},
        ]
    )

    result = DevicesService(client).move(  # type: ignore[arg-type]
        "Server-01", rack_name="RACK-02", position=15
    )

    assert result["moved"] is True
    assert client.calls[-1] == (
        "PATCH",
        "/api/dcim/devices/7/",
        {"rack": 4, "position": 15, "face": "front", "site": 1, "location": 3},
    )


def test_allocate_refuses_to_move_device_already_in_a_rack() -> None:
    client = FakeClient(
        [
            page(
                {
                    "id": 7,
                    "name": "Server-01",
                    "rack": {"id": 4, "name": "RACK-04"},
                }
            )
        ]
    )

    with pytest.raises(NetBoxCLIError, match="já está alocado em 'RACK-04'"):
        DevicesService(client).allocate(  # type: ignore[arg-type]
            "Server-01", rack_name="RACK-02", position=15
        )

    assert all(method != "PATCH" for method, _, _ in client.calls)


def test_allocate_places_an_unallocated_device_without_a_second_lookup() -> None:
    client = FakeClient(
        [
            page({"id": 7, "name": "Server-01", "rack": None}),
            page(
                {
                    "id": 4,
                    "name": "RACK-02",
                    "site": {"id": 1},
                    "location": {"id": 3},
                }
            ),
            {"id": 7, "name": "Server-01"},
        ]
    )

    result = DevicesService(client).allocate(  # type: ignore[arg-type]
        "Server-01", rack_name="RACK-02", position=15
    )

    assert result["allocated"] is True
    assert [method for method, _, _ in client.calls] == ["GET", "GET", "PATCH"]


def test_rack_elevation_requests_all_units() -> None:
    client = FakeClient(
        [
            page({"id": 4, "name": "RACK-04", "u_height": 42}),
            page({"id": "42.0", "device": None}),
        ]
    )

    result = RacksService(client).elevation("RACK-04")  # type: ignore[arg-type]

    assert result["u_height"] == 42
    assert client.calls[-1] == (
        "GET",
        "/api/dcim/racks/4/elevation/",
        {"face": "front", "limit": 0},
    )


def test_general_search_normalizes_devices() -> None:
    client = FakeClient(
        [
            page(
                {
                    "id": 7,
                    "name": "Server-01",
                    "rack": {"name": "RACK-04"},
                    "site": {"name": "CPTEC"},
                    "status": {"label": "Active"},
                    "primary_ip4": {"address": "10.10.0.23/24"},
                }
            ),
            page(),
            page(),
            page(),
            page(),
        ]
    )

    result = SearchService(client).search("server-01")  # type: ignore[arg-type]

    assert result["count"] == 1
    assert result["results"][0] == {
        "type": "device",
        "id": 7,
        "name": "Server-01",
        "rack": "RACK-04",
        "site": "CPTEC",
        "status": "Active",
        "ip": "10.10.0.23/24",
    }
    assert len(client.calls) == 5


def test_available_positions_require_contiguous_free_units() -> None:
    client = FakeClient(
        [
            page(
                {
                    "id": 4,
                    "name": "RACK-04",
                    "u_height": 4,
                    "starting_unit": 1,
                }
            ),
            page(
                {"id": "1.0", "occupied": False},
                {"id": "1.5", "occupied": False},
                {"id": "2.0", "occupied": True},
                {"id": "2.5", "occupied": True},
                {"id": "3.0", "occupied": False},
                {"id": "3.5", "occupied": False},
                {"id": "4.0", "occupied": False},
                {"id": "4.5", "occupied": False},
            ),
            page(),
        ]
    )

    result = RacksService(client).available(  # type: ignore[arg-type]
        "RACK-04", height=2
    )

    assert result["positions"] == [3.0]
    assert result["count"] == 1


def test_inventory_resolves_site_and_normalizes_devices() -> None:
    client = FakeClient(
        [
            page({"id": 1, "name": "CPTEC"}),
            page(
                {
                    "id": 7,
                    "name": "Server-01",
                    "role": {"name": "Server"},
                    "device_type": {"display": "PowerEdge"},
                    "site": {"name": "CPTEC"},
                    "rack": {"name": "RACK-04"},
                    "position": "20.0",
                    "status": {"label": "Active"},
                    "primary_ip4": {"address": "10.10.0.23/24"},
                }
            ),
        ]
    )

    result = InventoryService(client).inventory(  # type: ignore[arg-type]
        site_name="CPTEC"
    )

    assert result["count"] == 1
    assert result["results"][0]["primary_ip"] == "10.10.0.23/24"
    assert client.calls[-1][2] == {"site_id": 1, "limit": 0}


def test_inventory_requires_exactly_one_filter() -> None:
    client = FakeClient([])
    with pytest.raises(InventoryFilterError, match="--site ou --rack"):
        InventoryService(client).inventory()  # type: ignore[arg-type]


def test_trace_normalizes_cable_path() -> None:
    client = FakeClient(
        [
            page({"id": 7, "name": "Server-01"}),
            page({"id": 10, "name": "eth0", "device": {"name": "Server-01"}}),
            [
                [
                    [
                        {
                            "id": 10,
                            "name": "eth0",
                            "device": {"name": "Server-01"},
                        }
                    ],
                    {
                        "id": 20,
                        "label": "CAB-20",
                        "status": {"label": "Connected"},
                    },
                    [
                        {
                            "id": 30,
                            "name": "Gi0/12",
                            "device": {"name": "Switch-01"},
                        }
                    ],
                ]
            ],
        ]
    )

    result = DevicesService(client).trace("Server-01", "eth0")  # type: ignore[arg-type]

    assert result["connected"] is True
    assert result["segments"][0]["far"][0]["device"] == "Switch-01"
    assert result["segments"][0]["far"][0]["name"] == "Gi0/12"
    assert result["segments"][0]["cable"]["label"] == "CAB-20"


def test_inventory_csv_has_stable_header(capsys: pytest.CaptureFixture[str]) -> None:
    render_inventory(
        {
            "filter": {"type": "rack", "value": "RACK-04"},
            "results": [{"id": 7, "name": "Server-01", "rack": "RACK-04"}],
        },
        InventoryOutputFormat.csv,
    )

    csv_output = capsys.readouterr().out
    assert csv_output.startswith("id,name,role,device_type,site,location,rack,")
    assert "7,Server-01" in csv_output


def test_status_distinguishes_reachable_url_from_invalid_token() -> None:
    client = FakeClient([NetBoxClientError("Invalid token", status_code=403)])

    result = StatusService(  # type: ignore[arg-type]
        client, url="http://localhost:8000", token_configured=True
    ).check()

    assert result["reachable"] is True
    assert result["authenticated"] is False
    assert result["status_code"] == 403


def test_login_composes_netbox_v2_token() -> None:
    client = FakeClient([{"id": 7, "version": 2, "key": "abc123", "token": "secret"}])

    token = AuthService(client).login("admin", "password")  # type: ignore[arg-type]

    assert token == "nbt_abc123.secret"
    assert client.calls == [
        (
            "POST",
            "/api/users/tokens/provision/",
            {
                "username": "admin",
                "password": "password",
                "description": "netbox-cli",
                "write_enabled": True,
                "version": 2,
            },
        )
    ]


def test_status_reports_authenticated_user() -> None:
    client = FakeClient(
        [
            {
                "id": 1,
                "username": "admin",
                "display": "admin (NetBox Admin)",
                "first_name": "NetBox",
                "last_name": "Admin",
                "email": "admin@example.com",
                "is_active": True,
                "last_login": "2026-08-20T10:00:00Z",
                "date_joined": "2026-01-01T10:00:00Z",
                "groups": [{"name": "Administradores"}],
                "permissions": [{"name": "DCIM"}, {"name": "IPAM"}],
            },
            [],
        ]
    )

    result = StatusService(  # type: ignore[arg-type]
        client,
        url="http://localhost:8000",
        token_configured=True,
        token_version=2,
    ).check()

    assert result["reachable"] is True
    assert result["authenticated"] is True
    assert result["user"] == "admin"
    assert result["token_version"] == 2
    assert result["user_details"] == {
        "id": 1,
        "username": "admin",
        "display": "admin (NetBox Admin)",
        "full_name": "NetBox Admin",
        "email": "admin@example.com",
        "active": True,
        "last_login": "2026-08-20T10:00:00Z",
        "date_joined": "2026-01-01T10:00:00Z",
        "groups": ["Administradores"],
    }


def test_rack_capacity_consolidates_front_and_rear_units() -> None:
    client = FakeClient(
        [
            page({"id": 4, "name": "RACK-04", "u_height": 4}),
            page(
                {"id": "1.0", "occupied": True},
                {"id": "1.5", "occupied": True},
            ),
            page(
                {"id": "1.0", "occupied": True},
                {"id": "2.0", "occupied": True},
                {"id": "2.5", "occupied": True},
            ),
            page(),
        ]
    )

    result = RacksService(client).capacity("RACK-04")  # type: ignore[arg-type]

    assert result["total_u"] == 4
    assert result["occupied_u"] == 2
    assert result["free_u"] == 2
    assert result["occupancy_percent"] == 50
    assert result["front"]["occupied_u"] == 1
    assert result["rear"]["occupied_u"] == 1.5


def test_rack_capacity_counts_reservations_on_both_faces() -> None:
    client = FakeClient(
        [
            page({"id": 4, "name": "RACK-04", "u_height": 4}),
            page(),
            page(),
            page({"id": 30, "rack": {"id": 4}, "units": [2]}),
        ]
    )

    result = RacksService(client).capacity("RACK-04")  # type: ignore[arg-type]

    assert result["occupied_u"] == 1
    assert result["free_u"] == 3
    assert result["front"]["occupied_u"] == 1
    assert result["rear"]["occupied_u"] == 1


def test_available_positions_exclude_reserved_units() -> None:
    client = FakeClient(
        [
            page(
                {
                    "id": 4,
                    "name": "RACK-04",
                    "u_height": 4,
                    "starting_unit": 1,
                }
            ),
            page(),
            page({"id": 30, "rack": {"id": 4}, "units": [2]}),
        ]
    )

    result = RacksService(client).available(  # type: ignore[arg-type]
        "RACK-04", height=1
    )

    assert result["positions"] == [1.0, 3.0, 3.5, 4.0]


def test_site_status_aggregates_capacity_and_manufacturers() -> None:
    client = FakeClient(
        [
            page({"id": 1, "name": "CPTEC", "status": {"label": "Active"}}),
            page({"id": 4, "name": "RACK-04", "u_height": 2}),
            page(
                {
                    "id": 7,
                    "name": "Server-01",
                    "rack": {"id": 4},
                    "position": "1.0",
                    "face": {"value": "front"},
                    "device_type": {
                        "id": 13,
                        "manufacturer": {"name": "Dell"},
                    },
                },
                {
                    "id": 8,
                    "name": "Server-02",
                    "rack": None,
                    "position": None,
                    "device_type": {
                        "id": 13,
                        "manufacturer": {"name": "Dell"},
                    },
                },
            ),
            page({"id": 13, "u_height": "1.0", "is_full_depth": False}),
            page(),
        ]
    )

    result = SitesService(client).status("CPTEC")  # type: ignore[arg-type]

    assert result["racks"] == 1
    assert result["devices"] == 2
    assert result["capacity"]["free_u"] == 1
    assert result["capacity"]["occupancy_percent"] == 50
    assert result["manufacturers"] == [{"name": "Dell", "devices": 2}]
    assert len(client.calls) == 5


def test_infrastructure_tree_nests_device_under_rack() -> None:
    client = FakeClient(
        [
            page({"id": 1, "name": "Sudeste", "parent": None}),
            page({"id": 2, "name": "CPTEC", "region": {"id": 1}}),
            page(
                {
                    "id": 3,
                    "name": "Datacenter",
                    "site": {"id": 2},
                    "parent": None,
                }
            ),
            page(
                {
                    "id": 4,
                    "name": "RACK-04",
                    "site": {"id": 2},
                    "location": {"id": 3},
                }
            ),
            page(
                {
                    "id": 5,
                    "name": "Server-01",
                    "site": {"id": 2},
                    "location": {"id": 3},
                    "rack": {"id": 4},
                    "position": "20.0",
                }
            ),
        ]
    )

    result = InfrastructureService(client).tree()  # type: ignore[arg-type]

    region = result["children"][0]
    site = region["children"][0]
    location = site["children"][0]
    rack = location["children"][0]
    assert [region["name"], site["name"], location["name"], rack["name"]] == [
        "Sudeste",
        "CPTEC",
        "Datacenter",
        "RACK-04",
    ]
    assert rack["children"][0]["name"] == "Server-01"


def test_device_deallocate_clears_only_rack_fields() -> None:
    client = FakeClient(
        [
            page(
                {
                    "id": 7,
                    "name": "Server-01",
                    "rack": {"name": "RACK-04"},
                    "position": "20.0",
                }
            ),
            {"id": 7, "name": "Server-01"},
        ]
    )

    result = DevicesService(client).deallocate("Server-01")  # type: ignore[arg-type]

    assert result["deallocated"] is True
    assert result["previous_rack"] == "RACK-04"
    assert client.calls[-1] == (
        "PATCH",
        "/api/dcim/devices/7/",
        {"rack": None, "position": None, "face": None},
    )


def test_name_lookup_falls_back_to_search_for_case_insensitive_match() -> None:
    client = FakeClient([page(), page({"id": 4, "name": "teste2"})])

    result = get_by_name(  # type: ignore[arg-type]
        client, "/api/dcim/racks/", "TESTE2", resource_label="Rack"
    )

    assert result["id"] == 4
    assert client.calls == [
        ("GET", "/api/dcim/racks/", {"name": "TESTE2", "limit": 0}),
        ("GET", "/api/dcim/racks/", {"q": "TESTE2", "limit": 0}),
    ]


def test_scoped_rack_uses_site_and_location_ids() -> None:
    client = FakeClient(
        [
            page({"id": 1, "name": "CPTEC"}),
            page({"id": 2, "name": "Datacenter"}),
            page({"id": 4, "name": "RACK-04"}),
        ]
    )

    result = get_scoped_rack(  # type: ignore[arg-type]
        client,
        "RACK-04",
        site_name="CPTEC",
        location_name="Datacenter",
    )

    assert result["id"] == 4
    assert client.calls[-1][2] == {
        "site_id": 1,
        "location_id": 2,
        "name": "RACK-04",
        "limit": 0,
    }


def test_rack_render_uses_starting_unit_and_half_unit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_rack(
        {
            "name": "RACK-10",
            "starting_unit": 10,
            "u_height": 2,
            "units": [
                {"id": "11.5", "occupied": False},
                {"id": "11.0", "occupied": False},
                {
                    "id": "10.5",
                    "occupied": True,
                    "device": {"name": "Half-U"},
                },
                {"id": "10.0", "occupied": False},
            ],
        },
        DetailOutputFormat.human,
    )

    output = capsys.readouterr().out
    assert "11U" in output
    assert "10U" in output
    assert "U10.5: Half-U" in output
    assert "01U" not in output


def test_trace_preserves_breakout_branches() -> None:
    client = FakeClient(
        [
            page({"id": 7, "name": "Server-01"}),
            page({"id": 10, "name": "eth0"}),
            [
                [
                    [{"id": 10, "name": "eth0"}],
                    {"id": 20, "label": "BREAKOUT"},
                    [
                        {"id": 30, "name": "Gi0/1", "device": {"name": "SW1"}},
                        {"id": 31, "name": "Gi0/2", "device": {"name": "SW1"}},
                    ],
                ]
            ],
        ]
    )

    result = DevicesService(client).trace("Server-01", "eth0")  # type: ignore[arg-type]

    assert len(result["segments"]) == 1
    assert [item["name"] for item in result["segments"][0]["far"]] == [
        "Gi0/1",
        "Gi0/2",
    ]


def test_device_inspect_loads_reported_components() -> None:
    client = FakeClient(
        [
            page({"id": 7, "name": "Server-01", "front_port_count": 1}),
            page(),
            page(),
            page({"id": 40, "name": "USB", "type": {"label": "USB A"}}),
        ]
    )

    result = DevicesService(client).inspect("Server-01")  # type: ignore[arg-type]

    assert result["components"]["front_ports"][0]["name"] == "USB"
    assert result["components"]["front_ports"][0]["type"] == "USB A"
    assert len(client.calls) == 4


def test_singular_commands_are_discoverable() -> None:
    runner = CliRunner()
    root_help = runner.invoke(app, ["--help"])
    login_help = runner.invoke(app, ["login", "--help"])
    site_help = runner.invoke(app, ["site", "status", "--help"])
    rack_help = runner.invoke(app, ["rack", "capacity", "--help"])
    device_help = runner.invoke(app, ["device", "allocate", "--help"])

    assert root_help.exit_code == 0
    assert login_help.exit_code == 0
    assert "Autentica no NetBox" in login_help.output
    assert "login" in root_help.output
    assert site_help.exit_code == 0
    assert rack_help.exit_code == 0
    assert device_help.exit_code == 0
    assert "--rack-site" in device_help.stdout


def test_invalid_rack_face_exits_before_api_call() -> None:
    result = CliRunner().invoke(app, ["rack", "show", "R01", "--face", "side"])

    assert result.exit_code == 2
    assert "front" in result.output


def test_tree_site_scope_filters_large_resource_collections() -> None:
    client = FakeClient(
        [
            page({"id": 2, "name": "CPTEC", "region": {"id": 1}}),
            {"id": 1, "name": "Sudeste", "parent": None},
            page(),
            page(),
            page(),
        ]
    )

    result = InfrastructureService(client).tree(  # type: ignore[arg-type]
        site_name="CPTEC"
    )

    assert result["counts"]["sites"] == 1
    assert [region["name"] for region in result["children"]] == ["Sudeste"]
    assert result["children"][0]["children"][0]["name"] == "CPTEC"
    assert client.calls[2][2] == {"site_id": 2, "limit": 0}
    assert client.calls[3][2] == {"site_id": 2, "limit": 0}
    assert client.calls[4][2] == {"site_id": 2, "limit": 0}


def test_all_results_follows_every_pagination_link() -> None:
    next_url = "http://netbox.local/api/dcim/devices/?limit=1000&offset=1000"
    client = FakeClient(
        [
            {
                "count": 2,
                "next": next_url,
                "results": [{"id": 1, "name": "A"}],
            },
            {
                "count": 2,
                "next": None,
                "results": [{"id": 2, "name": "B"}],
            },
        ]
    )

    results = get_all_results(  # type: ignore[arg-type]
        client, "/api/dcim/devices/", params={"limit": 0}
    )

    assert [item["id"] for item in results] == [1, 2]
    assert client.calls == [
        ("GET", "/api/dcim/devices/", {"limit": 0}),
        ("GET", next_url, None),
    ]


@pytest.mark.parametrize(
    "command",
    ["rack-groups", "racks", "manufacturers", "device-types", "devices"],
)
def test_all_commands_request_every_page_by_default(command: str) -> None:
    result = CliRunner().invoke(app, [command, "all", "--help"])

    assert result.exit_code == 0
    assert "[default: 0]" in result.stdout


def test_client_rejects_pagination_url_from_another_origin() -> None:
    client = NetBoxClient("https://netbox.local", token="secret")
    try:
        with pytest.raises(NetBoxClientError, match="origem inesperada"):
            client.get("https://attacker.invalid/api/dcim/devices/?offset=1000")
    finally:
        client.close()


def test_config_treats_null_token_as_empty() -> None:
    settings = ConfigStore._parse(
        {"url": "https://netbox.local", "token": None, "timeout": 15}
    )

    assert settings.token == ""


def test_saved_token_is_bound_to_current_url(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.yaml")
    store.save(Settings(url="https://netbox-a.local"))

    settings = store.save_token("secret")

    assert settings.token == "secret"
    assert settings.token_url == "https://netbox-a.local"


def test_config_store_refuses_to_persist_token_for_another_url(
    tmp_path: Path,
) -> None:
    store = ConfigStore(tmp_path / "config.yaml")

    with pytest.raises(ConfigurationError, match="não pertence"):
        store.save(
            Settings(
                url="https://netbox-b.local",
                token="secret-from-a",
                token_url="https://netbox-a.local",
            )
        )


def test_manual_url_change_invalidates_token_before_use(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "url: https://netbox-b.local\n"
        "token: secret-from-a\n"
        "token_url: https://netbox-a.local\n"
        "timeout: 15\n",
        encoding="utf-8",
    )
    store = ConfigStore(path)

    settings = store.load()

    assert settings.url == "https://netbox-b.local"
    assert settings.token == ""
    assert settings.token_url == ""
    with pytest.raises(ConfigurationError, match="Token não configurado"):
        store.load(require_token=True)


def test_legacy_token_without_origin_is_invalidated(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "url: https://netbox.local\n" "token: legacy-secret\n" "timeout: 15\n",
        encoding="utf-8",
    )

    settings = ConfigStore(path).load()

    assert settings.token == ""
    assert settings.token_url == ""


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"url": None}, "url deve ser um texto"),
        ({"url": "netbox.local"}, "URL HTTP ou HTTPS"),
        ({"timeout": float("nan")}, "finito"),
        ({"timeout": float("inf")}, "finito"),
        ({"timeout": True}, "número"),
    ],
)
def test_config_rejects_invalid_scalar_values(
    raw: dict[str, Any], message: str
) -> None:
    with pytest.raises(ConfigurationError, match=message):
        ConfigStore._parse(raw)

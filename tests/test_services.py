from unittest.mock import Mock

from netbox_cli.schemas.organization import AddLocation, AddRegion, AddSite
from netbox_cli.service.base_service import slugify
from netbox_cli.service.organization import LocationsService, RegionsService, SitesService


def test_slugify_removes_accents_and_symbols() -> None:
    assert slugify("São Paulo / Produção") == "sao-paulo-producao"


def test_region_crud_uses_regions_endpoint() -> None:
    client = Mock()
    client.post.return_value = {"id": 1, "name": "Sudeste"}
    service = RegionsService(client)

    result = service.create(AddRegion(name="Sudeste"))
    service.get(1)
    service.list(search="sud", limit=10)
    service.delete(1)

    assert result["id"] == 1
    client.post.assert_called_once_with(
        "/api/dcim/regions/",
        {"name": "Sudeste", "slug": "sudeste", "description": ""},
    )
    client.get.assert_any_call("/api/dcim/regions/1/")
    client.get.assert_any_call("/api/dcim/regions/", params={"q": "sud", "limit": 10})
    client.delete.assert_called_once_with("/api/dcim/regions/1/")


def test_site_payload_contains_region() -> None:
    client = Mock()
    service = SitesService(client)
    service.create(AddSite(name="São Paulo", region=7))

    client.post.assert_called_once_with(
        "/api/dcim/sites/",
        {
            "name": "São Paulo",
            "slug": "sao-paulo",
            "status": "active",
            "region": 7,
            "description": "",
        },
    )


def test_location_payload_contains_site_and_parent() -> None:
    client = Mock()
    service = LocationsService(client)
    service.create(AddLocation(name="Sala A", site=3, parent=8))

    client.post.assert_called_once_with(
        "/api/dcim/locations/",
        {
            "name": "Sala A",
            "site": 3,
            "slug": "sala-a",
            "status": "active",
            "parent": 8,
            "description": "",
        },
    )

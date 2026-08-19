from netbox_cli.schemas.organization.locations_dto import AddLocation
from netbox_cli.service.base_service import CRUDService


class LocationsService(CRUDService[AddLocation]):
    ENDPOINT = "/api/dcim/locations/"

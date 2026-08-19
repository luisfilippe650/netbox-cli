from netbox_cli.schemas.racks import AddRackGroup
from netbox_cli.service.base_service import CRUDService


class RackGroupsService(CRUDService[AddRackGroup]):
    ENDPOINT = "/api/dcim/rack-groups/"

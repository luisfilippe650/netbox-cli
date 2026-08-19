from netbox_cli.schemas.racks import AddRack
from netbox_cli.service.base_service import CRUDService


class RacksService(CRUDService[AddRack]):
    ENDPOINT = "/api/dcim/racks/"
    USES_SLUG = False

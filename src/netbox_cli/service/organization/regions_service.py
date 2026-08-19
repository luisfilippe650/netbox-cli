from netbox_cli.schemas.organization.regions_dto import AddRegion
from netbox_cli.service.base_service import CRUDService


class RegionsService(CRUDService[AddRegion]):
    ENDPOINT = "/api/dcim/regions/"

from netbox_cli.schemas.organization.sites_dto import AddSite
from netbox_cli.service.base_service import CRUDService


class SitesService(CRUDService[AddSite]):
    ENDPOINT = "/api/dcim/sites/"

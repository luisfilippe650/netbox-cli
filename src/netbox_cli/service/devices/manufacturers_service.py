from netbox_cli.schemas.devices import AddManufacturer
from netbox_cli.service.base_service import CRUDService


class ManufacturersService(CRUDService[AddManufacturer]):
    ENDPOINT = "/api/dcim/manufacturers/"

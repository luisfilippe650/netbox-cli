from typing import Any

from pydantic import BaseModel

from netbox_cli.client import NetBoxClient
from netbox_cli.client.pagination import get_all_results
from netbox_cli.schemas.devices import (
    AddCable,
    AddConsolePort,
    AddFrontPort,
    AddInterface,
    AddPowerPort,
    AddRearPort,
)
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.lookup import get_by_name, resolve_resource_id

DEVICES_ENDPOINT = "/api/dcim/devices/"


class DeviceComponentsService(CRUDService[BaseModel]):
    USES_SLUG = False

    def __init__(self, client: NetBoxClient) -> None:
        super().__init__(client)
        self._device_ids: dict[str, int] = {}

    def build_payload(self, item: BaseModel) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)
        device = payload.get("device")

        if isinstance(device, str):
            payload["device"] = self.resolve_device_id(device)

        return payload

    def resolve_device_id(self, identifier: int | str) -> int:
        if isinstance(identifier, int):
            return identifier

        cache_key = identifier.casefold()

        if cache_key not in self._device_ids:
            self._device_ids[cache_key] = resolve_resource_id(
                self.client,
                DEVICES_ENDPOINT,
                identifier,
                resource_label="Dispositivo",
            )

        return self._device_ids[cache_key]

    def list(
        self,
        *,
        search: str | None = None,
        limit: int | None = 0,
        device: int | str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}

        if search:
            params["q"] = search

        if device is not None:
            params["device_id"] = self.resolve_device_id(device)

        if limit is not None:
            params["limit"] = limit

        if limit == 0:
            results = get_all_results(self.client, self.ENDPOINT, params=params)

            return {
                "count": len(results),
                "next": None,
                "previous": None,
                "results": results,
            }

        return self.client.get(self.ENDPOINT, params=params or None)

    def resolve_component_id(
        self, device: int | str, identifier: int | str
    ) -> int:
        if isinstance(identifier, int):
            return identifier

        device_id = self.resolve_device_id(device)
        component = get_by_name(
            self.client,
            self.ENDPOINT,
            identifier,
            resource_label=self.RESOURCE_LABEL,
            filters={"device_id": device_id},
        )

        return int(component["id"])


class InterfacesService(DeviceComponentsService):
    ENDPOINT = "/api/dcim/interfaces/"
    RESOURCE_LABEL = "Interface"


class RearPortsService(DeviceComponentsService):
    ENDPOINT = "/api/dcim/rear-ports/"
    RESOURCE_LABEL = "Porta traseira"


class FrontPortsService(DeviceComponentsService):
    ENDPOINT = "/api/dcim/front-ports/"
    RESOURCE_LABEL = "Porta frontal"

    def build_payload(self, item: BaseModel) -> dict[str, Any]:
        payload = super().build_payload(item)
        rear_port = payload.pop("rear_port", None)
        rear_position = payload.pop("rear_port_position", 1)

        if rear_port is not None:
            device_id = payload["device"]
            rear_port_id = RearPortsService(self.client).resolve_component_id(
                device_id, rear_port
            )
            payload["rear_ports"] = [
                {
                    "rear_port": rear_port_id,
                    "position": 1,
                    "rear_port_position": rear_position,
                }
            ]

        return payload


class ConsolePortsService(DeviceComponentsService):
    ENDPOINT = "/api/dcim/console-ports/"
    RESOURCE_LABEL = "Porta de console"


class PowerPortsService(DeviceComponentsService):
    ENDPOINT = "/api/dcim/power-ports/"
    RESOURCE_LABEL = "Porta de energia"


TERMINATION_SERVICES: dict[str, type[DeviceComponentsService]] = {
    "interface": InterfacesService,
    "front-port": FrontPortsService,
    "rear-port": RearPortsService,
    "console-port": ConsolePortsService,
    "power-port": PowerPortsService,
}

TERMINATION_OBJECT_TYPES = {
    "interface": "dcim.interface",
    "front-port": "dcim.frontport",
    "rear-port": "dcim.rearport",
    "console-port": "dcim.consoleport",
    "power-port": "dcim.powerport",
}


class CablesService(CRUDService[AddCable]):
    ENDPOINT = "/api/dcim/cables/"
    USES_SLUG = False

    def build_payload(self, item: BaseModel) -> dict[str, Any]:
        payload = item.model_dump(mode="json", exclude_none=True)

        if not isinstance(item, AddCable):
            return payload

        for side in ("a", "b"):
            termination_type = payload.pop(f"{side}_type")
            device = payload.pop(f"{side}_device")
            name = payload.pop(f"{side}_name")
            service = TERMINATION_SERVICES[termination_type](self.client)
            component_id = service.resolve_component_id(device, name)
            payload[f"{side}_terminations"] = [
                {
                    "object_type": TERMINATION_OBJECT_TYPES[termination_type],
                    "object_id": component_id,
                }
            ]

        return payload

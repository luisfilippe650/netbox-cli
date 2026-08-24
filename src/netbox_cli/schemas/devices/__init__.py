from netbox_cli.schemas.devices.connectivity_dto import (
    AddCable,
    AddConsolePort,
    AddFrontPort,
    AddInterface,
    AddPowerPort,
    AddRearPort,
    TerminationType,
    UpdateCable,
    UpdateConsolePort,
    UpdateFrontPort,
    UpdateInterface,
    UpdatePowerPort,
    UpdateRearPort,
)
from netbox_cli.schemas.devices.device_roles_dto import AddDeviceRole, UpdateDeviceRole
from netbox_cli.schemas.devices.device_types_dto import AddDeviceType, UpdateDeviceType
from netbox_cli.schemas.devices.devices_dto import AddDevice, UpdateDevice
from netbox_cli.schemas.devices.manufacturers_dto import AddManufacturer, UpdateManufacturer

__all__ = [
    "AddCable",
    "AddConsolePort",
    "AddDevice",
    "AddDeviceRole",
    "AddDeviceType",
    "AddFrontPort",
    "AddInterface",
    "AddManufacturer",
    "AddPowerPort",
    "AddRearPort",
    "TerminationType",
    "UpdateCable",
    "UpdateConsolePort",
    "UpdateDeviceRole",
    "UpdateDevice",
    "UpdateDeviceType",
    "UpdateFrontPort",
    "UpdateInterface",
    "UpdateManufacturer",
    "UpdatePowerPort",
    "UpdateRearPort",
]

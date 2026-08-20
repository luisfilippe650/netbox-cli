"""Fachada compatível para os renderizadores organizados por domínio."""

from netbox_cli.presentation.device_details import render_inspection, render_trace
from netbox_cli.presentation.formats import DetailOutputFormat, InventoryOutputFormat
from netbox_cli.presentation.inventory_details import render_inventory
from netbox_cli.presentation.rack_details import (
    render_availability,
    render_capacity,
    render_rack,
)
from netbox_cli.presentation.status_details import (
    render_infrastructure_tree,
    render_search,
    render_site_status,
    render_status,
)

__all__ = [
    "DetailOutputFormat",
    "InventoryOutputFormat",
    "render_availability",
    "render_capacity",
    "render_infrastructure_tree",
    "render_inspection",
    "render_inventory",
    "render_rack",
    "render_search",
    "render_site_status",
    "render_status",
    "render_trace",
]

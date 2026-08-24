from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from netbox_cli.client import NetBoxClient
from netbox_cli.exceptions import NetBoxCLIError
from netbox_cli.schemas.devices import (
    AddDevice,
    AddDeviceRole,
    AddDeviceType,
    AddManufacturer,
)
from netbox_cli.schemas.organization import AddLocation, AddRegion, AddSite
from netbox_cli.schemas.racks import AddRack, AddRackGroup
from netbox_cli.service.base_service import CRUDService
from netbox_cli.service.devices import (
    DeviceRolesService,
    DeviceTypesService,
    DevicesService,
    ManufacturersService,
)
from netbox_cli.service.organization import LocationsService, RegionsService, SitesService
from netbox_cli.service.racks import RackGroupsService, RacksService


class ImportDocumentError(NetBoxCLIError):
    """Documento de importação inválido."""


class ImportExecutionError(NetBoxCLIError):
    """Falha ao aplicar um documento de importação."""


@dataclass(frozen=True, slots=True)
class ResourceDefinition:
    model: type[BaseModel]
    service: type[CRUDService[Any]]
    priority: int
    identity_field: str = "name"


@dataclass(frozen=True, slots=True)
class ImportEntry:
    position: int
    resource: str
    item: BaseModel
    definition: ResourceDefinition


@dataclass(frozen=True, slots=True)
class AppliedChange:
    entry: ImportEntry
    service: CRUDService[Any]
    result: dict[str, Any]
    previous: dict[str, Any] | None = None


RESOURCE_DEFINITIONS: dict[str, ResourceDefinition] = {
    "regions": ResourceDefinition(AddRegion, RegionsService, 10),
    "sites": ResourceDefinition(AddSite, SitesService, 20),
    "locations": ResourceDefinition(AddLocation, LocationsService, 30),
    "rack-groups": ResourceDefinition(AddRackGroup, RackGroupsService, 40),
    "manufacturers": ResourceDefinition(AddManufacturer, ManufacturersService, 50),
    "device-roles": ResourceDefinition(AddDeviceRole, DeviceRolesService, 60),
    "device-types": ResourceDefinition(
        AddDeviceType,
        DeviceTypesService,
        70,
        identity_field="model",
    ),
    "racks": ResourceDefinition(AddRack, RacksService, 80),
    "devices": ResourceDefinition(AddDevice, DevicesService, 90),
}

RESOURCE_ALIASES = {
    "region": "regions",
    "site": "sites",
    "location": "locations",
    "rack-group": "rack-groups",
    "rack_group": "rack-groups",
    "manufacturer": "manufacturers",
    "device-role": "device-roles",
    "device_role": "device-roles",
    "device-type": "device-types",
    "device_type": "device-types",
    "rack": "racks",
    "device": "devices",
}


def load_import_document(path: Path) -> Any:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ImportDocumentError(f"Não foi possível ler {path}: {error}") from error

    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise ImportDocumentError(f"YAML/JSON inválido em {path}: {error}") from error


class ImportService:
    """Converge recursos declarativos e desfaz mudanças em caso de falha."""

    def __init__(
        self,
        client: NetBoxClient,
        *,
        definitions: dict[str, ResourceDefinition] | None = None,
    ) -> None:
        self.client = client
        self.definitions = (
            RESOURCE_DEFINITIONS if definitions is None else definitions
        )

    def run(
        self,
        document: Any,
        *,
        dry_run: bool = False,
        atomic: bool = True,
    ) -> dict[str, Any]:
        entries = self._parse_entries(document)

        if dry_run:
            planning_client = _PlanningClient(self.client)
            results: list[dict[str, Any]] = []

            for entry in entries:
                service, result, _ = self._apply(
                    entry,
                    dry_run=True,
                    client=planning_client,
                )
                results.append(result)

                if result.get("action") == "would_create":
                    payload = result.get("payload")

                    if isinstance(payload, dict):
                        planning_client.register(service.ENDPOINT, payload)

            return self._summary(entries, results, dry_run=True, atomic=atomic)

        applied: list[AppliedChange] = []
        results: list[dict[str, Any]] = []
        current_entry: ImportEntry | None = None

        try:
            for entry in entries:
                current_entry = entry
                service, result, previous = self._apply(entry, dry_run=False)
                results.append(result)

                if result.get("changed"):
                    applied.append(AppliedChange(entry, service, result, previous))
        except Exception as error:
            if not atomic:
                raise

            rollback_errors = self._rollback(applied)
            status = (
                "rollback concluído"
                if not rollback_errors
                else "rollback incompleto: " + "; ".join(rollback_errors)
            )
            raise ImportExecutionError(
                f"Falha no item {current_entry.position if current_entry else 1}; "
                f"{status}. Causa: {error}"
            ) from error

        return self._summary(entries, results, dry_run=False, atomic=atomic)

    def _parse_entries(self, document: Any) -> list[ImportEntry]:
        raw_entries = _document_entries(document)
        entries: list[ImportEntry] = []

        for position, (resource_name, payload) in enumerate(raw_entries, start=1):
            resource = _canonical_resource(resource_name)
            definition = self.definitions.get(resource)

            if definition is None:
                supported = ", ".join(self.definitions)
                raise ImportDocumentError(
                    f"Item {position}: recurso {resource_name!r} não suportado. "
                    f"Use um destes: {supported}."
                )

            if not isinstance(payload, dict):
                raise ImportDocumentError(
                    f"Item {position} ({resource}): esperado um objeto de campos."
                )

            unknown_fields = set(payload) - set(definition.model.model_fields)

            if unknown_fields:
                fields = ", ".join(sorted(unknown_fields))
                raise ImportDocumentError(
                    f"Item {position} ({resource}): campos desconhecidos: {fields}."
                )

            try:
                item = definition.model.model_validate(payload)
            except ValidationError as error:
                raise ImportDocumentError(
                    f"Item {position} ({resource}) inválido: {error}"
                ) from error

            entries.append(ImportEntry(position, resource, item, definition))

        return sorted(entries, key=lambda entry: (entry.definition.priority, entry.position))

    def _apply(
        self,
        entry: ImportEntry,
        *,
        dry_run: bool,
        client: Any | None = None,
    ) -> tuple[CRUDService[Any], dict[str, Any], dict[str, Any] | None]:
        service = entry.definition.service(client or self.client)
        plan = service.ensure(
            entry.item,
            identity_field=entry.definition.identity_field,
            dry_run=True,
        )

        previous = (
            plan.get("resource")
            if plan.get("action") == "would_update"
            and isinstance(plan.get("resource"), dict)
            else None
        )
        result = plan

        if not dry_run and plan.get("action") != "unchanged":
            result = service.ensure(
                entry.item,
                identity_field=entry.definition.identity_field,
                dry_run=False,
            )

        return (
            service,
            {
                "position": entry.position,
                "resource_type": entry.resource,
                **result,
            },
            previous,
        )

    def _rollback(self, applied: list[AppliedChange]) -> list[str]:
        errors: list[str] = []

        for change in reversed(applied):
            try:
                self._rollback_change(change)
            except Exception as error:
                errors.append(
                    f"item {change.entry.position} ({change.entry.resource}): {error}"
                )

        return errors

    def _rollback_change(self, change: AppliedChange) -> None:
        action = change.result.get("action")
        resource = change.result.get("resource")

        if not isinstance(resource, dict) or resource.get("id") is None:
            raise ImportExecutionError("resposta aplicada sem ID")

        item_id = int(resource["id"])

        if action == "created":
            change.service.delete(item_id)
            return

        if action == "updated":
            changes = change.result.get("changes")

            if change.previous is None or not isinstance(changes, dict):
                raise ImportExecutionError("resposta de atualização sem estado anterior")

            payload = {
                field: _writable_value(change.previous.get(field)) for field in changes
            }
            self.client.patch(f"{change.service.ENDPOINT}{item_id}/", payload)

    @staticmethod
    def _summary(
        entries: list[ImportEntry],
        results: list[dict[str, Any]],
        *,
        dry_run: bool,
        atomic: bool,
    ) -> dict[str, Any]:
        return {
            "dry_run": dry_run,
            "atomic": atomic,
            "changed": any(result.get("changed") for result in results),
            "count": len(entries),
            "results": results,
        }


def _document_entries(document: Any) -> list[tuple[str, Any]]:
    if not isinstance(document, dict):
        raise ImportDocumentError("A raiz do documento deve ser um objeto YAML/JSON.")

    resources = document.get("resources", document)

    if isinstance(resources, list):
        return [_flat_entry(item, position) for position, item in enumerate(resources, 1)]

    if not isinstance(resources, dict):
        raise ImportDocumentError("'resources' deve ser um objeto ou uma lista.")

    entries: list[tuple[str, Any]] = []

    for resource, items in resources.items():
        if resource == "version":
            continue

        if not isinstance(items, list):
            raise ImportDocumentError(f"{resource!r} deve conter uma lista de itens.")

        entries.extend((str(resource), item) for item in items)

    return entries


def _flat_entry(item: Any, position: int) -> tuple[str, Any]:
    if not isinstance(item, dict):
        raise ImportDocumentError(f"Item {position}: esperado um objeto.")

    resource = item.get("resource") or item.get("type")

    if not isinstance(resource, str) or not resource.strip():
        raise ImportDocumentError(
            f"Item {position}: informe 'resource' ou 'type'."
        )

    data = item.get("data")

    if data is None:
        data = {
            key: value
            for key, value in item.items()
            if key not in {"resource", "type"}
        }

    return resource, data


def _canonical_resource(resource: str) -> str:
    normalized = resource.strip().lower().replace("_", "-")

    return RESOURCE_ALIASES.get(normalized, normalized)


def _writable_value(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("id") is not None:
            return value["id"]
        if value.get("value") is not None:
            return value["value"]

    if isinstance(value, list):
        return [_writable_value(item) for item in value]

    return value


class _PlanningClient:
    """Acrescenta recursos planejados às consultas sem realizar mutações."""

    def __init__(self, client: NetBoxClient) -> None:
        self._client = client
        self._resources: dict[str, list[dict[str, Any]]] = {}
        self._next_id = -1

    def register(self, endpoint: str, payload: dict[str, Any]) -> None:
        resource = {**payload, "id": self._next_id}
        self._next_id -= 1
        self._resources.setdefault(endpoint, []).append(resource)

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = self._client.get(endpoint, params=params)
        planned = self._resources.get(endpoint)

        if not planned or not isinstance(response, dict):
            return response

        results = response.get("results")

        if not isinstance(results, list):
            return response

        matches = [item for item in planned if _matches_params(item, params)]

        if not matches:
            return response

        combined = [*results, *matches]
        return {**response, "count": len(combined), "results": combined}

    def post(self, endpoint: str, data: dict[str, Any]) -> Any:
        raise ImportExecutionError("o planejamento tentou criar um recurso")

    def patch(self, endpoint: str, data: dict[str, Any]) -> Any:
        raise ImportExecutionError("o planejamento tentou atualizar um recurso")

    def delete(self, endpoint: str) -> None:
        raise ImportExecutionError("o planejamento tentou excluir um recurso")


def _matches_params(item: dict[str, Any], params: dict[str, Any] | None) -> bool:
    for field, expected in (params or {}).items():
        if field == "limit":
            continue

        if field == "q":
            normalized = str(expected).casefold()

            if not any(
                str(item.get(candidate, "")).casefold() == normalized
                for candidate in ("name", "slug", "model")
            ):
                return False

            continue

        item_field = field[:-3] if field.endswith("_id") else field

        if _writable_value(item.get(item_field)) != expected:
            return False

    return True

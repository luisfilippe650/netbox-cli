from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from rich.console import Console
from typer.testing import CliRunner

from netbox_cli.app import app
from netbox_cli.client import NetBoxClientError
from netbox_cli.presentation import output as output_module
from netbox_cli.presentation.output import OutputFormat, render
from netbox_cli.service.import_service import (
    ImportDocumentError,
    ImportExecutionError,
    ImportService,
)


class ImportClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = iter(responses)
        self.calls: list[tuple[str, str, Any]] = []

    def _response(self) -> Any:
        response = next(self.responses)

        if isinstance(response, Exception):
            raise response

        return response

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append(("GET", endpoint, params))
        return self._response()

    def post(self, endpoint: str, data: dict[str, Any]) -> Any:
        self.calls.append(("POST", endpoint, data))
        return self._response()

    def patch(self, endpoint: str, data: dict[str, Any]) -> Any:
        self.calls.append(("PATCH", endpoint, data))
        return self._response()

    def delete(self, endpoint: str) -> None:
        self.calls.append(("DELETE", endpoint, None))


def page(*items: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": len(items),
        "next": None,
        "previous": None,
        "results": list(items),
    }


def test_id_output_prints_one_identifier_per_list_item(
    capsys: pytest.CaptureFixture[str],
) -> None:
    render(
        {"count": 2, "results": [{"id": 3}, {"id": 8}]},
        OutputFormat.id,
        title="Recursos",
    )

    assert capsys.readouterr().out == "3\n8\n"


def test_empty_id_listing_is_successful_and_silent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    render({"count": 0, "results": []}, OutputFormat.id, title="Recursos")

    assert capsys.readouterr().out == ""


def test_table_renders_choice_label(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        output_module,
        "console",
        Console(file=stream, force_terminal=False, width=120),
    )

    render(
        {"results": [{"id": 1, "status": {"value": "connected", "label": "Connected"}}]},
        OutputFormat.table,
        title="Cabos",
    )

    assert "Connected" in stream.getvalue()


def test_import_dry_run_does_not_mutate() -> None:
    client = ImportClient([page()])

    result = ImportService(client).run(  # type: ignore[arg-type]
        {"resources": {"regions": [{"name": "Sudeste"}]}},
        dry_run=True,
    )

    assert result["results"][0]["action"] == "would_create"
    assert [call[0] for call in client.calls] == ["GET"]


def test_import_dry_run_resolves_a_relationship_planned_in_the_same_file() -> None:
    client = ImportClient([page(), page(), page()])

    result = ImportService(client).run(  # type: ignore[arg-type]
        {
            "resources": {
                "regions": [{"name": "Sudeste"}],
                "sites": [{"name": "CPTEC", "region": "Sudeste"}],
            }
        },
        dry_run=True,
    )

    assert [item["action"] for item in result["results"]] == [
        "would_create",
        "would_create",
    ]
    assert all(call[0] == "GET" for call in client.calls)


def test_atomic_import_removes_created_resources_after_failure() -> None:
    client = ImportClient(
        [
            page(),
            page(),
            {"id": 10, "name": "Sudeste", "slug": "sudeste"},
            NetBoxClientError("falha simulada"),
        ]
    )

    with pytest.raises(ImportExecutionError, match="rollback concluído"):
        ImportService(client).run(  # type: ignore[arg-type]
            {
                "resources": {
                    "regions": [
                        {"name": "Sudeste"},
                        {"name": "Sul"},
                    ]
                }
            }
        )

    assert client.calls[-1] == ("DELETE", "/api/dcim/regions/10/", None)


def test_atomic_import_restores_updated_fields_after_failure() -> None:
    current = {
        "id": 10,
        "name": "Sudeste",
        "slug": "sudeste",
        "description": "Original",
    }
    client = ImportClient(
        [
            page(current),
            page(current),
            {**current, "description": "Nova"},
            NetBoxClientError("falha simulada"),
            current,
        ]
    )

    with pytest.raises(ImportExecutionError, match="rollback concluído"):
        ImportService(client).run(  # type: ignore[arg-type]
            {
                "regions": [
                    {"name": "Sudeste", "description": "Nova"},
                    {"name": "Sul"},
                ]
            }
        )

    assert client.calls[-1] == (
        "PATCH",
        "/api/dcim/regions/10/",
        {"description": "Original"},
    )


def test_import_validates_every_item_before_mutating() -> None:
    client = ImportClient([])

    with pytest.raises(ImportDocumentError, match="campos desconhecidos"):
        ImportService(client).run(  # type: ignore[arg-type]
            {
                "regions": [
                    {"name": "Sudeste"},
                    {"name": "Sul", "descripton": "campo digitado errado"},
                ]
            }
        )

    assert client.calls == []


def test_import_command_is_available() -> None:
    result = CliRunner().invoke(app, ["import", "--help"])

    assert result.exit_code == 0, result.output
    assert "--dry-run" in result.output
    assert "--atomic" in result.output

from pathlib import Path
from typing import Annotated

import typer

from netbox_cli.cli.common import execute, make_client
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.service.import_service import ImportService, load_import_document


def import_resources(
    file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Documento declarativo YAML ou JSON.",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Valida e planeja sem alterar o NetBox."),
    ] = False,
    atomic: Annotated[
        bool,
        typer.Option(
            "--atomic/--no-atomic",
            help="Desfaz alterações anteriores se algum item falhar.",
        ),
    ] = True,
    output: Annotated[
        OutputFormat, typer.Option("--output", "-o")
    ] = OutputFormat.json,
) -> None:
    """Converge recursos declarados em um documento YAML ou JSON."""
    execute(
        lambda: ImportService(make_client()).run(
            load_import_document(file),
            dry_run=dry_run,
            atomic=atomic,
        ),
        output=output,
        title="Importação",
    )

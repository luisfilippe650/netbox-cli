from typing import Annotated

import typer

from netbox_cli.cli.common import (
    create_resource,
    delete_resource,
    execute,
    execute_operation,
    explicit_update_fields,
    make_service,
    update_resource,
)
from netbox_cli.presentation.details import DetailOutputFormat, render_site_status
from netbox_cli.presentation.output import OutputFormat
from netbox_cli.schemas.organization.sites_dto import AddSite, UpdateSite
from netbox_cli.service.organization.sites_service import SitesService

app = typer.Typer(help="Gerencia sites do NetBox.", no_args_is_help=True)


def post_site(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n")],
    slug: Annotated[str | None, typer.Option()] = None,
    status: Annotated[str, typer.Option()] = "active",
    region: Annotated[
        str | None, typer.Option("--region", help="ID, nome ou slug da região.")
    ] = None,
    description: Annotated[str, typer.Option("--description", "-d")] = "",
    ensure: Annotated[
        bool, typer.Option("--ensure", help="Cria ou converge pelo nome.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Cria um site."""
    execute(
        lambda: create_resource(
            SitesService,
            AddSite(
                name=name,
                slug=slug,
                status=status,
                region=region,
                description=description,
            ),
            ensure=ensure,
            dry_run=dry_run,
            update_fields=explicit_update_fields(
                ctx,
                required={"name"},
                optional={"slug", "status", "region", "description"},
            ),
        ),
        output=output,
        title="Site criado",
    )


app.command("create")(post_site)
app.command("post", hidden=True)(post_site)


@app.command("get")
def view_site(
    site_id: Annotated[int, typer.Argument(min=1)],
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exibe um site pelo ID."""
    execute(
        lambda: make_service(SitesService).get(site_id), output=output, title="Site"
    )


app.command("view", hidden=True)(view_site)


@app.command("list")
def list_sites(
    search: Annotated[str | None, typer.Option("--search", "-s")] = None,
    limit: Annotated[int | None, typer.Option(min=0)] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Lista sites, opcionalmente filtrados."""
    execute(
        lambda: make_service(SitesService).list(search=search, limit=limit),
        output=output,
        title="Sites",
    )


@app.command("update")
def update_site(
    site_id: Annotated[int, typer.Argument(min=1)],
    name: Annotated[str | None, typer.Option("--name", "-n")] = None,
    slug: Annotated[str | None, typer.Option("--slug")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    region: Annotated[
        str | None, typer.Option("--region", help="ID, nome ou slug da região.")
    ] = None,
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Atualiza somente os campos informados de um site."""
    execute(
        lambda: update_resource(
            SitesService,
            site_id,
            UpdateSite(
                name=name,
                slug=slug,
                status=status,
                region=region,
                description=description,
            ),
            dry_run=dry_run,
        ),
        output=output,
        title="Site atualizado",
    )


@app.command("delete")
def delete_site(
    site_id: Annotated[int, typer.Argument(min=1)],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ignore_not_found: Annotated[bool, typer.Option("--ignore-not-found")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", "-o")] = OutputFormat.json,
) -> None:
    """Exclui um site pelo ID."""

    execute(
        lambda: delete_resource(
            SitesService,
            site_id,
            resource="site",
            dry_run=dry_run,
            ignore_not_found=ignore_not_found,
        ),
        output=output,
        title="Site removido",
    )


@app.command("status")
def site_status(
    name: Annotated[str, typer.Argument(help="Nome exato do site.")],
    output: Annotated[
        DetailOutputFormat, typer.Option("--output", "-o")
    ] = DetailOutputFormat.human,
) -> None:
    """Resume racks, dispositivos, capacidade e fabricantes de um site."""
    result = execute_operation(lambda: make_service(SitesService).status(name))
    render_site_status(result, output)

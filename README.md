# netbox-cli

[Português](README.pt-BR.md) | **English**

A Python CLI for querying and managing physical inventory in NetBox. It combines
interactive Rich menus, tables and trees with JSON output for scripts, CI/CD and
AI agents.

Manage regions, sites, locations, racks, manufacturers, device roles and types,
devices, interfaces, physical ports and cables. Search inventory, inspect devices,
trace connections and check rack capacity from the terminal.

## Installation

Requires Python 3.11+ when running from source:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
netbox --help
```

For Ubuntu servers, build a standalone Debian package with Docker:

```bash
./packaging/build-deb.sh
sudo apt install ./dist/netbox-cli_<version>_amd64.deb
```

Replace `<version>` with the generated package version. The package includes its
runtime, so the target server does not need Python or pip.

## Quick start

```bash
netbox login
netbox status
netbox search server-01
netbox sites list --output table
netbox --output json devices list
```

Run `netbox` without arguments to open the interactive menu. For automation:

```bash
export NETBOX_URL="https://netbox.example.com"
export NETBOX_TOKEN="nbt_key.token"
netbox --output json status
netbox manufacturers create --name Dell --ensure --dry-run
```

Prefer environment variables for tokens. Local login stores a token in
`~/.config/netbox-cli/config.yaml`; the password is never stored. Global options
precede the command. `--ensure` converges resource state and `--dry-run` previews
changes. Exit codes are 0 for success, 1 for operational failure and 2 for invalid
command usage.

## Documentation

The bilingual documentation uses [Zensical](https://zensical.org/). From the
repository root, with Zensical installed:

```bash
zensical serve
```

Open `http://127.0.0.1:8000`. To validate and generate the static site:

```bash
zensical build --strict
```

The site is written to `site/`. Configuration is in [zensical.toml](zensical.toml).
Pages include links to their counterpart in the other language.

- [English documentation](docs/index.md)
- [Portuguese documentation](docs/pt/index.md)
- [Installation](docs/getting-started.md)
- [Configuration and output](docs/configuration.md)
- [Operational queries and connectivity](docs/operations.md)
- [Resource command reference](docs/reference.md)
- [Automation and AI agents](docs/automation.md)
- [About](docs/about.md)

## About

Developed by [Luis Filippe Reis Nogueira](https://github.com/luisfilippe650)
as part of his internship activities at COIDS/INPE to support datacenter
infrastructure management from the terminal and repeatable automation.
It uses the NetBox REST API and is not an official project of NetBox or NetBox Labs.
See [About the project](docs/about.md) for context and credits.

## Development

```bash
pip install -e '.[test]'
pytest
```

Update both Portuguese pages in `docs/pt/` and English pages in `docs/` when changing documented behavior. Do not
commit tokens, local configuration, documentation caches or generated site files.

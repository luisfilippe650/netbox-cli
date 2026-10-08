# Installation and first steps

[Português](pt/getting-started.md)

## Debian package on Ubuntu

The `.deb` includes its runtime and installs `/usr/bin/netbox`. The target server
does not need Python 3.11, pip or a virtual environment.

```bash
sudo apt install ./dist/netbox-cli_0.1.1_amd64.deb
netbox --help
```

Replace the filename with the package you built. Install a newer package with the
same command. Remove it with `sudo apt remove netbox-cli`. User configuration and
tokens remain in `~/.config/netbox-cli/config.yaml`.

## Building the package

Docker with access to its daemon is required:

```bash
./packaging/build-deb.sh
```

The builder compiles Python 3.11 on Ubuntu 20.04, bundles the CLI using PyInstaller
`onedir`, and installs and checks the resulting package in clean Ubuntu 20.04,
22.04, 24.04 and 26.04 containers. Package versions come from
`netbox_cli.__version__`; build dependencies are pinned in
`packaging/deb/constraints.txt`. The default artifact is `amd64`; other
architectures require a native or suitably configured Docker builder.

## Installing from source

Requires Python 3.11 or newer. Run from the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
netbox --help
```

You can also run `python -m netbox_cli --help`. Shell completion is available with
`netbox --install-completion` and `netbox --show-completion`.

## First connection

```bash
netbox
netbox login
netbox --version
netbox status
netbox --output json status
netbox search server-01
```

`netbox` opens the interactive menu to log in, change URL and timeout, inspect the
session or remove the local token. `netbox login` opens login directly.

For automation, supply credentials through environment variables:

```bash
export NETBOX_URL="https://netbox.example.com"
export NETBOX_TOKEN="nbt_key.token"
export NETBOX_TIMEOUT="30"
netbox --output json status
```

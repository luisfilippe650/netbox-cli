# About

[Português](pt/about.md)

## Who developed it

Developed by **[Luis Filippe Reis Nogueira](https://github.com/luisfilippe650)**
as part of his internship activities at the **Divisão de Infraestrutura de Dados
e Supercomputação (COIDS)** of **[INPE — Instituto Nacional de Pesquisas
Espaciais](https://www.gov.br/inpe/pt-br)**, Brazil's National Institute for Space
Research.

Source code: [luisfilippe650/netbox-cli](https://github.com/luisfilippe650/netbox-cli).

## Why it was created

netbox-cli grew out of INPE's datacenter infrastructure management needs.
Its goal is to make information about devices, racks, environments and physical
connections easier to query and update from the terminal through integration
with the NetBox REST API.

Rich menus and views support infrastructure monitoring and maintenance. JSON,
exit codes, `--ensure` and `--dry-run` integrate those workflows into scripts,
pipelines and AI agents, supporting repeatable operations and reviewing changes
before applying them.

## Credits and NetBox integration

netbox-cli uses the NetBox REST API. Credit for the platform, APIs and
documentation goes to the **NetBox community and maintainers**.

- [NetBox source code and community](https://github.com/netbox-community/netbox)
- [NetBox documentation](https://netboxlabs.com/docs/netbox/)

NetBox is a separate project with its own license and maintainers. netbox-cli
**is not an official project of NetBox or NetBox Labs**. Third-party libraries
retain their respective licenses and credits. The NetBox server still enforces
permissions, validation and uniqueness constraints.

## Contributing

Open an issue or pull request with the use case, reproduction steps and expected
behavior. Do not include tokens or sensitive data.

To develop and run tests:

```bash
pip install -e '.[test]'
pytest
```

To review documentation changes, run from the repository root:

```bash
zensical serve
zensical build --strict
```

Pages live in `docs/pt/` (Portuguese) and `docs/` (English). Update both languages when changing a
command. Configuration lives in `zensical.toml`; `site/` and `.cache/` are local
artifacts ignored by Git.

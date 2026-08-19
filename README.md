# netbox-cli

CLI para administrar regiões, sites e locais do NetBox por dois modos de uso:

- `netbox`: terminal interativo com Rich;
- `netbox <recurso> <operação>`: comandos diretos com JSON, apropriados para scripts e agentes de IA.

## Instalação

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
cp .env.exemple .env
```

Configure o `.env`:

```dotenv
NETBOX_URL=http://localhost:8000
NETBOX_TOKEN=seu_token_v1_ou_v2
NETBOX_TIMEOUT=15
```

`NETBOX_URL` deve ser a raiz da instalação, sem `/api` no final.
A CLI detecta tokens v2 iniciados por `nbt_` e usa autenticação Bearer;
os demais tokens usam o esquema Token legado.

## Terminal interativo

```bash
netbox
```

O menu solicita o recurso e a operação, confirma exclusões e apresenta os dados em tabelas Rich.

## Linha direta

```bash
netbox regions list
netbox regions view 1
netbox regions post --name "Sudeste"
netbox regions delete 1

netbox sites post --name "São Paulo" --region 1
netbox sites list --search paulo

netbox locations post --name "Datacenter A" --site 1
netbox locations view 1
netbox locations delete 1
```

A saída direta é JSON por padrão. Para apresentação humana em tabela:

```bash
netbox sites list --output table
```

Use `netbox --help` e `netbox <recurso> --help` para consultar todas as opções.

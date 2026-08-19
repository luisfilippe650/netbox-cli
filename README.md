# netbox-cli

CLI para administrar organização e racks do NetBox por dois modos de uso:

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

### Grupos de racks

```bash
netbox rack-groups post --name "Corredor A"
netbox rack-groups all
netbox rack-groups get 1
netbox rack-groups update 1 --name "Corredor B"
netbox rack-groups delete 1
```

O grupo recebe apenas o nome; seu slug é gerado automaticamente.

### Racks

```bash
netbox racks post \
  --site 1 \
  --name "R01" \
  --width 19 \
  --starting-unit 1 \
  --u-height 42

netbox racks all
netbox racks get 1
netbox racks update 1 --name "R01-A" --u-height 48
netbox racks delete 1
```

Grupo, função e tipo podem ser vinculados opcionalmente:

```bash
netbox racks post \
  --site 1 \
  --name "R02" \
  --width 19 \
  --starting-unit 1 \
  --u-height 42 \
  --group 1 \
  --role 2 \
  --type 3
```

As larguras aceitas pelo NetBox são `10`, `19`, `21` e `23`. O status de um
novo rack é sempre enviado como `active` e não aparece como opção da CLI.

A saída direta é JSON por padrão. Para apresentação humana em tabela:

```bash
netbox sites list --output table
```

Use `netbox --help` e `netbox <recurso> --help` para consultar todas as opções.

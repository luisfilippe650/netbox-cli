# netbox-cli

CLI para administrar organização e racks do NetBox por dois modos de uso:

- `netbox`: interface Rich para login e configuração;
- `netbox <recurso> <operação>`: comandos diretos com JSON, apropriados para scripts e agentes de IA.

## Instalação

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Login e configuração

O login existe somente no terminal interativo. Na primeira execução, use:

```bash
netbox
```

A interface solicita usuário e senha do NetBox. A senha não é armazenada; o
token retornado pela API é salvo em:

```text
~/.config/netbox-cli/config.yaml
```

O arquivo é criado automaticamente com permissão `0600` e este conteúdo
inicial:

```yaml
url: http://localhost:8000
token: ''
timeout: 15
```

URL e timeout podem ser alterados diretamente nesse arquivo. Os comandos de
linha direta reutilizam o token salvo pelo login visual.

## Interface visual

```bash
netbox
```

A interface Rich é exclusiva para login e configuração. Nela é possível:

- fazer ou refazer o login;
- alterar a URL do NetBox;
- alterar o timeout;
- limpar o token armazenado.

Use as setas `↑` e `↓` para navegar pelas escolhas e `Enter` para selecionar.
As operações de regiões, sites, locais e racks são executadas somente pelos
comandos de linha direta abaixo.

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

### Fabricantes

```bash
netbox manufacturers post --name "Dell" --comments "Fornecedor principal"
netbox manufacturers all
netbox manufacturers get 1
netbox manufacturers delete 1
```

Somente o nome é obrigatório. O comentário pode ser omitido.

### Tipos de dispositivos

```bash
netbox device-types post \
  --manufacturer 1 \
  --model "PowerEdge R650" \
  --u-height 1

netbox device-types all
netbox device-types get 1
netbox device-types delete 1
```

### Dispositivos

```bash
netbox devices post \
  --name "srv01" \
  --role 1 \
  --device-type 1 \
  --site 1

netbox devices all
netbox devices get 1
netbox devices delete 1
```

Serial, local, rack e posição são opcionais:

```bash
netbox devices post \
  --name "srv02" \
  --role 1 \
  --device-type 1 \
  --site 1 \
  --serial "ABC123" \
  --location 2 \
  --rack 3 \
  --position 10
```

O status é enviado automaticamente como `active`. Quando uma posição é
informada, o rack se torna obrigatório e a face é enviada como `front`.

Campos personalizados são enviados como um objeto JSON:

```bash
netbox devices post \
  --name "srv03" \
  --role 1 \
  --device-type 1 \
  --site 1 \
  --custom-fields '{"patrimonio":"PAT-001","monitorado":true}'
```

Antes do cadastro, a CLI consulta os campos personalizados aplicáveis a
`dcim.device`. Se algum estiver marcado como obrigatório e não aparecer no JSON,
o comando é interrompido e informa os campos ausentes.

A saída direta é JSON por padrão. Para apresentação humana em tabela:

```bash
netbox sites list --output table
```

Use `netbox --help` e `netbox <recurso> --help` para consultar todas as opções.

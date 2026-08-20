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
token_url: ''
timeout: 15
```

URL e timeout podem ser alterados diretamente nesse arquivo. O token é vinculado
à URL em que o login foi realizado; se a URL for alterada, ele é invalidado antes
de qualquer requisição e um novo login será necessário.

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

## Inspeção e automação

Os comandos de consulta abaixo têm uma saída Rich legível por padrão e aceitam
`--output json` para scripts, pipelines e agentes:

```bash
netbox inspect server-01
netbox inspect server-01 --output json
netbox search server-01
netbox search 10.10.0.23 --output json
```

`inspect` reúne site, local, rack, posição, status, interfaces conectadas e
endereços IP. `search` procura simultaneamente em dispositivos, racks, sites,
locais e endereços IP. O limite padrão é de dez resultados por tipo e pode ser
alterado com `--limit`.

A elevação frontal de um rack pode ser desenhada pelo nome:

```bash
netbox rack show RACK-04
netbox rack show RACK-04 --face rear
netbox rack show RACK-04 --output json
```

Para mover um dispositivo sem descobrir IDs manualmente:

```bash
netbox devices move server-01 --rack RACK-02 --position 15
netbox devices move server-01 --rack RACK-02 --position 15 --output json
```

O comando atualiza rack, posição e face frontal. Se o rack estiver em outro
site ou local, esses vínculos também são atualizados. Nomes inexistentes ou
duplicados são recusados explicitamente, evitando que uma automação escolha o
recurso errado.

### Disponibilidade, inventário e diagnóstico

Para localizar posições contíguas que comportam um equipamento:

```bash
netbox rack available RACK-04 --height 2
netbox rack available RACK-04 --height 2 --output json
```

Quando nomes de racks se repetem, use site e/ou local como escopo:

```bash
netbox rack available RACK-04 --height 2 --site CPTEC --location Datacenter
netbox rack capacity RACK-04 --site CPTEC
```

A disponibilidade considera ocupação, altura e face do rack. Equipamentos e
racks com suporte a meia unidade também podem usar valores como `--height 0.5`.

O inventário pode ser filtrado por exatamente um site ou rack:

```bash
netbox inventory --site CPTEC --output json
netbox inventory --rack RACK-04 --output csv > rack-04.csv
netbox inventory --rack RACK-04 --site CPTEC --output json
```

O CSV possui colunas estáveis para ID, nome, função, modelo, site, local, rack,
posição, status, IP primário e serial.

Para rastrear uma conexão física registrada no NetBox:

```bash
netbox trace server-01 eth0
netbox trace server-01 eth0 --output json
netbox trace server-01 eth0 --site CPTEC
```

Por fim, o diagnóstico mostra separadamente se a URL foi alcançada, se existe
um token configurado e se esse token autentica corretamente:

```bash
netbox status
netbox status --output json
```

`netbox status` retorna código zero apenas quando a autenticação estiver válida,
permitindo seu uso direto em verificações de shell e pipelines.

### Visão operacional e hierarquia

O resumo de um site agrega recursos e capacidade de todos os seus racks:

```bash
netbox site status CPTEC
netbox site status CPTEC --output json
```

Ele informa quantidade de racks e dispositivos, total de unidades, unidades
livres e ocupadas, percentual de ocupação e dispositivos por fabricante.

A capacidade detalhada de um rack consolida a ocupação física e também mostra
frente e traseira separadamente:

```bash
netbox rack capacity RACK-04
netbox rack capacity RACK-04 --output json
```

A árvore completa segue região, site, local, rack e dispositivo:

```bash
netbox tree
netbox tree --site CPTEC
netbox tree --output json
```

Para consultar um dispositivo com identificação, modelo, fabricante, montagem,
IPs, campos personalizados e interfaces:

```bash
netbox device inspect server-01
netbox device inspect server-01 --output json
```

Alocação e retirada do rack também podem ser feitas pelo nome:

```bash
netbox device allocate server-01 --rack RACK-04 --position 20
netbox device allocate server-01 \
  --device-site CPTEC \
  --rack RACK-04 \
  --rack-site CPTEC \
  --rack-location Datacenter \
  --position 20
netbox device deallocate server-01
```

Ao desalocar, rack, posição e face são limpos; site e local são preservados.
As opções de escopo eliminam ambiguidades quando nomes se repetem entre sites.
`allocate` recusa dispositivos que já estejam em um rack; para reposicioná-los,
use `netbox device move`.

# Consultas operacionais

[English](../operations.md)

## Referência rápida

| Comando | Uso |
|---|---|
| `netbox` | Menu interativo |
| `netbox login` | Login direto |
| `netbox status` | Diagnóstico de URL, token e superusuário |
| `netbox search QUERY` | Busca geral |
| `netbox inspect DEVICE` | Inspeção rápida do dispositivo |
| `netbox inventory` | Exportação de inventário |
| `netbox trace DEVICE INTERFACE` | Rastreamento físico |
| `netbox tree` | Hierarquia completa |
| `netbox regions ...` | Regiões |
| `netbox sites ...` | Sites |
| `netbox locations ...` | Locais |
| `netbox rack-groups ...` | Grupos de racks |
| `netbox racks ...` | Racks |
| `netbox manufacturers ...` | Fabricantes |
| `netbox device-roles ...` | Funções de dispositivos |
| `netbox device-types ...` | Tipos de dispositivos |
| `netbox devices ...` | Dispositivos |
| `netbox interfaces ...` | Interfaces |
| `netbox front-ports ...` | Portas frontais |
| `netbox rear-ports ...` | Portas traseiras |
| `netbox console-ports ...` | Portas de console |
| `netbox power-ports ...` | Portas de energia |
| `netbox cables ...` | Cabos e conexões |

`site`, `rack` e `device` são aliases singulares de `sites`, `racks` e `devices`.

Aliases ocultos mantidos por compatibilidade:

- `post` continua equivalente a `create`;
- `all` continua equivalente a `list`;
- `view`, usado anteriormente por regiões, sites e locais, continua equivalente
  a `get`.

Os recursos CRUD usam o mesmo contrato: `list`, `get`, `create`, `update` e
`delete`. Comandos operacionais como `status`, `tree`, `move` e `capacity`
continuam disponíveis ao lado desse conjunto.


## Consultas operacionais

### `status`

Exibe a versão da CLI e verifica URL, conectividade, existência e versão do
token, autenticação e acesso de superusuário. No JSON, a versão está disponível
em `cli_version`.

```bash
netbox status
netbox --output json status
```

O código de saída é zero somente quando `authorized` for verdadeiro, permitindo
uso como health check:

```bash
if netbox --output json status > status.json; then
  echo "NetBox pronto"
else
  jq . status.json
  exit 1
fi
```

### `search`

Busca simultaneamente dispositivos, racks, sites, locais e endereços IP.

```bash
netbox search server-01
netbox search 10.10.0.23 --limit 20
netbox --output json search server-01
```

`--limit` controla o máximo por tipo de recurso; o padrão é 10.

### `inspect`

Inspeção por nome exato, com site opcional para resolver nomes repetidos:

```bash
netbox inspect server-01
netbox inspect server-01 --site CPTEC
netbox --output json inspect server-01 --site CPTEC
```

Mostra localização, montagem, status, interfaces conectadas e IPs. A inspeção
detalhada também está disponível em `netbox device inspect`.

### `inventory`

Lista dispositivos por site ou rack. Site e location podem restringir a resolução
de um rack cujo nome esteja repetido:

```bash
netbox inventory --site CPTEC
netbox inventory --rack RACK-04 --site CPTEC
netbox inventory --rack RACK-04 --site CPTEC --location Datacenter
netbox inventory --rack RACK-04 --output json
netbox inventory --rack RACK-04 --output csv > rack-04.csv
netbox inventory --rack RACK-04 --wide
netbox inventory --rack RACK-04 --no-truncate
netbox inventory --rack RACK-04 --columns id,name,role,rack,status
```

Na saída humana, as colunas são escolhidas conforme a largura atual do terminal.
`--wide` mostra o conjunto completo, `--no-truncate` preserva os valores inteiros
usando quebras de linha e `--columns` seleciona e ordena campos específicos. A
seleção de colunas também pode ser usada com CSV; JSON não é modificado.

O CSV possui colunas estáveis para ID, nome, função, tipo, site, local, rack,
posição, status, IP primário e serial.

É obrigatório informar `--site` ou `--rack`. `--location` só pode ser usado junto
com `--rack`.

### `trace`

Rastreia uma interface através dos cabos registrados no NetBox:

```bash
netbox trace server-01 eth0
netbox trace server-01 eth0 --site CPTEC
netbox --output json trace server-01 eth0 --site CPTEC
```

### `tree`

Árvore completa de região, site, location, rack e dispositivo:

```bash
netbox tree
netbox tree --site CPTEC
netbox --output json tree --site CPTEC
```

Árvore de um rack e seus dispositivos:

```bash
netbox rack tree RACK-04
netbox rack tree RACK-04 --site CPTEC --location Datacenter
netbox --output json rack tree RACK-04 --site CPTEC
```

Árvore de localização e conexões de um dispositivo:

```bash
netbox device tree server-01
netbox device tree server-01 --site CPTEC
netbox --output json device tree server-01 --site CPTEC
```


## Componentes e conexões

Todos os comandos de componentes possuem `create`, `list`, `update` e `delete`.
O dispositivo pode ser informado por ID ou nome exato. Os valores de `--type`
usam os identificadores aceitos pelo NetBox.

### Interfaces

```bash
netbox interfaces create \
  --device switch-01 \
  --name Gi0/1 \
  --type 1000base-t
netbox interfaces list --device switch-01
netbox interfaces update 10 --description "Uplink principal"
netbox interfaces delete 10 --dry-run
```

### Patch panels

Crie primeiro a porta traseira e depois associe a porta frontal pelo ID ou nome:

```bash
netbox rear-ports create \
  --device patch-panel-01 \
  --name Rear-01 \
  --type 8p8c

netbox front-ports create \
  --device patch-panel-01 \
  --name Front-01 \
  --type 8p8c \
  --rear-port Rear-01 \
  --rear-port-position 1
```

### Console e energia

```bash
netbox console-ports create \
  --device servidor-01 \
  --name Console \
  --type rj-45 \
  --speed 9600

netbox power-ports create \
  --device servidor-01 \
  --name PSU-1 \
  --type iec-60320-c14 \
  --maximum-draw 500
```

### Cabos

As terminações aceitas são `interface`, `front-port`, `rear-port`,
`console-port` e `power-port`:

```bash
netbox cables create \
  --a-type interface \
  --a-device switch-01 \
  --a-name Gi0/1 \
  --b-type front-port \
  --b-device patch-panel-01 \
  --b-name Front-01 \
  --type cat6 \
  --label CAB-001

netbox cables list
netbox cables update 20 --status planned
netbox cables delete 20 --dry-run
```

Use `--dry-run` nas criações e atualizações para conferir os IDs resolvidos e o
payload sem alterar o NetBox. Exclusões também aceitam `--ignore-not-found`.

A árvore do dispositivo inclui caminho de localização, interfaces, IPs,
equipamentos conectados e conexões dos demais componentes físicos.


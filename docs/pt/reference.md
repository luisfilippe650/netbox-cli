# Referência de recursos

[English](../reference.md)

## Regiões

### Criar ou convergir

```bash
netbox regions create --name Sudeste
netbox regions create \
  --name Sudeste \
  --slug sudeste \
  --description "Região Sudeste" \
  --ensure
netbox regions create --name Sudeste --ensure --dry-run
```

Opções: `--name`, `--slug`, `--description`, `--ensure`, `--dry-run` e
`--output json|table`.

Com `--ensure`, nome identifica a região. Em um recurso existente, apenas opções
explicitamente informadas participam do PATCH.

### Consultar e listar

```bash
netbox regions get 1
netbox regions list
netbox regions list --search sudeste
netbox regions list --limit 0
netbox regions list --output table
```

`--limit 0` percorre todas as páginas.

### Atualizar e excluir

```bash
netbox regions update 1 --name "Sudeste Brasil"
netbox regions delete 1
netbox regions delete 1 --dry-run
netbox regions delete 1 --ignore-not-found
```


## Sites

### Criar ou convergir

```bash
netbox sites create --name CPTEC
netbox sites create \
  --name CPTEC \
  --slug cptec \
  --status active \
  --region sudeste \
  --description "Site principal" \
  --ensure
netbox sites create --name CPTEC --region Sudeste --ensure --dry-run
```

Opções: `--name`, `--slug`, `--status`, `--region ID|NOME|SLUG`, `--description`,
`--ensure`, `--dry-run` e `--output json|table`.

### Consultar e listar

```bash
netbox sites get 1
netbox sites list
netbox sites list --search cptec
netbox sites list --limit 0
netbox sites list --output table
```

### Resumo operacional

```bash
netbox site status CPTEC
netbox --output json site status CPTEC
```

O resumo agrega racks, dispositivos, capacidade total, unidades ocupadas/livres,
percentual de ocupação e distribuição por fabricante.

### Atualizar e excluir

```bash
netbox sites update 1 --status active --region Sudeste
netbox sites delete 1
netbox sites delete 1 --dry-run
netbox sites delete 1 --ignore-not-found
```


## Locais

Locations pertencem a um site e podem ter um local pai.

### Criar ou convergir

```bash
netbox locations create --name Datacenter --site CPTEC
netbox locations create \
  --name Datacenter \
  --site CPTEC \
  --slug datacenter \
  --status active \
  --parent 2 \
  --description "Sala principal" \
  --ensure
netbox locations create --name Datacenter --site cptec --ensure --dry-run
```

Opções: `--name`, `--site ID|NOME|SLUG`, `--slug`, `--status`,
`--parent ID|NOME|SLUG`,
`--description`, `--ensure`, `--dry-run` e `--output json|table`.

O `--ensure` identifica o local pela combinação nome e site.

### Consultar, listar, atualizar e excluir

```bash
netbox locations get 1
netbox locations list
netbox locations list --search data
netbox locations list --limit 0
netbox locations update 1 --description "Sala principal"
netbox locations delete 1 --dry-run
netbox locations delete 1 --ignore-not-found
```


## Grupos de racks

### Criar ou convergir

```bash
netbox rack-groups create --name "Corredor A"
netbox rack-groups create --name "Corredor A" --ensure
netbox rack-groups create --name "Corredor A" --ensure --dry-run
```

O slug é gerado automaticamente pelo nome.

### Consultar e listar

```bash
netbox rack-groups get 1
netbox rack-groups list
netbox rack-groups list --search corredor
netbox rack-groups list --limit 20
netbox rack-groups list --output table
```

Sem `--limit`, `list` percorre todas as páginas. `--limit 0` também representa
todos os resultados.

### Atualizar

```bash
netbox rack-groups update 1 --name "Corredor B"
netbox rack-groups update 1 --name "Corredor B" --dry-run
```

No dry-run, a CLI consulta o grupo e retorna `changed: false` se o nome já for o
desejado.

### Excluir

```bash
netbox rack-groups delete 1
netbox rack-groups delete 1 --dry-run
netbox rack-groups delete 1 --ignore-not-found
```


## Racks

### Criar ou convergir

```bash
netbox racks create \
  --site "Site Teste" \
  --name RACK-04 \
  --width 19 \
  --starting-unit 1 \
  --u-height 42
```

Com vínculos opcionais:

```bash
netbox racks create \
  --site site-teste \
  --name RACK-04 \
  --width 19 \
  --starting-unit 1 \
  --u-height 42 \
  --location "Sala Teste" \
  --group 2 \
  --role 3 \
  --type 4 \
  --ensure
```

Simulação idempotente:

```bash
netbox --output json racks create \
  --site "Site Teste" \
  --name RACK-04 \
  --width 19 \
  --starting-unit 1 \
  --u-height 42 \
  --ensure \
  --dry-run
```

Campos obrigatórios: `--site`, `--name`, `--width`, `--starting-unit` e
`--u-height`. Larguras aceitas: `10`, `19`, `21` e `23`. O status inicial é
`active`. Site e localização aceitam ID, nome exato ou slug. A localização é
resolvida dentro do site. Grupo, função e tipo são IDs opcionais.

O `--ensure` identifica o rack por nome e site. Defaults de criação, como status,
não sobrescrevem um rack existente quando não foram informados.

### Consultar e listar

```bash
netbox racks get 4
netbox racks list
netbox racks list --search RACK-04
netbox racks list --limit 25
netbox racks list --output table
```

### Atualizar

```bash
netbox racks update 4 --name RACK-04A
netbox racks update 4 --location 3
netbox racks update 4 --location "Sala Teste"
netbox racks update 4 --u-height 48 --role 3
netbox racks update 4 --u-height 48 --dry-run
```

Campos disponíveis: `--site`, `--name`, `--width`, `--starting-unit`,
`--u-height`, `--location`, `--group`, `--role|--function` e
`--type|--rack-type`.

O update altera somente campos informados. O dry-run consulta o rack e mostra
apenas as diferenças reais.

### Elevação

```bash
netbox rack show 4
netbox rack show RACK-04
netbox rack show RACK-04 --face rear
netbox rack show RACK-04 --site CPTEC --location Datacenter
netbox --output json rack show RACK-04
```

O primeiro argumento aceita o ID numérico ou o nome exato do rack. O mesmo
contrato é usado por `rack tree`, `rack available` e `rack capacity`.
Quando informados, `--site` e `--location` também restringem buscas por ID.

`--face` aceita `front` ou `rear`.

### Posições disponíveis

```bash
netbox rack available RACK-04 --height 2
netbox rack available RACK-04 --height 0.5 --face rear
netbox rack available RACK-04 \
  --height 2 \
  --site CPTEC \
  --location Datacenter
```

A consulta considera ocupação, altura, face e suporte a meia unidade.

### Capacidade

```bash
netbox rack capacity RACK-04
netbox rack capacity RACK-04 --site CPTEC --location Datacenter
netbox --output json rack capacity RACK-04
```

Mostra capacidade total, ocupação e visão separada das faces frontal e traseira.

### Árvore

```bash
netbox rack tree RACK-04
netbox rack tree RACK-04 --site CPTEC --location Datacenter
netbox --output json rack tree RACK-04
```

### Excluir

```bash
netbox racks delete 4
netbox racks delete 4 --dry-run
netbox racks delete 4 --ignore-not-found
```


## Fabricantes

### Criar ou convergir

```bash
netbox manufacturers create --name Dell
netbox manufacturers create \
  --name Dell \
  --comments "Fornecedor principal" \
  --ensure
netbox manufacturers create --name Dell --ensure --dry-run
```

O nome identifica o fabricante. `--comments|--comment` é opcional.

### Consultar, listar, atualizar e excluir

```bash
netbox manufacturers get 10
netbox manufacturers list
netbox manufacturers list --search dell
netbox manufacturers list --limit 20
netbox manufacturers list --output table
netbox manufacturers update 10 --comments "Fornecedor homologado"
netbox manufacturers delete 10 --dry-run
netbox manufacturers delete 10 --ignore-not-found
```


## Funções de dispositivos

```bash
netbox device-roles create --name Servidor
netbox device-roles create --name Servidor --color 2196f3 --no-vm-role
netbox device-roles get 2
netbox device-roles list
netbox device-roles list --search servidor --output table
netbox device-roles update 2 --name "Servidor físico" --color 3f51b5
netbox device-roles delete 2 --dry-run
netbox device-roles delete 2 --ignore-not-found
```

O slug é gerado automaticamente a partir do nome. `create` também aceita
`--ensure` para criar ou convergir uma função existente.


## Tipos de dispositivos

### Criar ou convergir

```bash
netbox device-types create \
  --manufacturer Dell \
  --model "PowerEdge R650" \
  --u-height 1

netbox device-types create \
  --manufacturer dell \
  --model "PowerEdge R650" \
  --u-height 1 \
  --ensure
```

Campos obrigatórios: fabricante, modelo e altura. O fabricante aceita ID, nome
exato ou slug. O `--ensure` identifica o tipo pela combinação fabricante e modelo.

### Consultar, listar, atualizar e excluir

```bash
netbox device-types get 15
netbox device-types list
netbox device-types list --search PowerEdge
netbox device-types list --limit 20
netbox device-types list --output table
netbox device-types update 15 --u-height 2
netbox device-types delete 15 --dry-run
netbox device-types delete 15 --ignore-not-found
```


## Dispositivos

### Criar ou convergir

Cadastro mínimo:

```bash
netbox devices create \
  --name server-01 \
  --role Servidor \
  --device-type "PowerEdge R650" \
  --site "Site Teste"
```

Cadastro montado em rack:

```bash
netbox devices create \
  --name server-01 \
  --role servidor \
  --device-type poweredge-r650 \
  --site site-teste \
  --serial ABC123 \
  --location "Sala Teste" \
  --rack Rack-01 \
  --position 10
```

Função, tipo, site, localização e rack aceitam ID, nome/modelo exato ou slug.
Localização e rack são resolvidos dentro do site. Quando `--position` é
informado, `--rack` é obrigatório e a face é `front`.
Posições aceitam incrementos de meia unidade.

Campos personalizados usam um objeto JSON:

```bash
netbox devices create \
  --name server-01 \
  --role Servidor \
  --device-type "PowerEdge R650" \
  --site "Site Teste" \
  --custom-fields '{"patrimonio":"PAT-001","monitorado":true}'
```

A CLI consulta os campos personalizados aplicáveis a `dcim.device` e recusa a
criação quando um campo obrigatório não foi fornecido.

Modo idempotente:

```bash
netbox --output json devices create \
  --name server-01 \
  --role Servidor \
  --device-type "PowerEdge R650" \
  --site "Site Teste" \
  --serial ABC123 \
  --ensure
```

O `--ensure` identifica o dispositivo por nome e site. Em dispositivos
existentes, somente opções explicitamente informadas são atualizadas;
`custom_fields={}` e `status=active` não são aplicados implicitamente.

### Consultar e listar

```bash
netbox devices get 30
netbox devices list
netbox devices list --search server
netbox devices list --limit 50
netbox devices list --output table
netbox devices list --output table --wide
netbox devices list --output table --no-truncate
netbox devices list --output table --columns id,name,role,site,rack,status
```

As tabelas se ajustam à largura do terminal. Use `--wide` para incluir todas as
colunas, `--no-truncate` para quebrar valores longos sem reticências ou
`--columns` para escolher e ordenar os campos exibidos.

### Atualizar

```bash
netbox devices update 30 --name server-02 --status offline
netbox devices update 30 --role Servidor --device-type "PowerEdge R650"
netbox devices update 30 --custom-fields '{"patrimonio":"PAT-002"}' --dry-run
```

### Inspecionar

```bash
netbox device inspect server-01
netbox device inspect server-01 --site CPTEC
netbox --output json device inspect server-01
```

Inclui identificação, modelo, fabricante, montagem, IPs, interfaces, componentes,
campos personalizados, datas e tags.

### Árvore de conexões

```bash
netbox device tree server-01
netbox device tree server-01 --site CPTEC
netbox --output json device tree server-01
```

### Mover

`move` permite reposicionar um dispositivo que já esteja alocado:

```bash
netbox device move server-01 --rack RACK-04 --position 10
netbox device move server-01 \
  --device-site CPTEC \
  --rack RACK-04 \
  --rack-site CPTEC \
  --rack-location Datacenter \
  --position 10
netbox --output json device move server-01 \
  --rack RACK-04 \
  --position 10 \
  --dry-run
```

Se o rack estiver em outro site ou location, esses vínculos também são
atualizados. A face de montagem é `front`.

### Alocar

`allocate` aceita somente dispositivos ainda não instalados em um rack:

```bash
netbox device allocate server-01 --rack RACK-04 --position 10
netbox device allocate server-01 \
  --device-site CPTEC \
  --rack RACK-04 \
  --rack-site CPTEC \
  --rack-location Datacenter \
  --position 10 \
  --dry-run
```

Se o dispositivo já estiver alocado, use `move`.

### Desalocar

```bash
netbox device deallocate server-01
netbox device deallocate server-01 --site CPTEC
netbox device deallocate server-01 --site CPTEC --dry-run
```

Rack, posição e face são limpos; site e location são preservados.

### Excluir

```bash
netbox devices delete 30
netbox devices delete 30 --dry-run
netbox devices delete 30 --ignore-not-found
netbox devices delete 30 --dry-run --ignore-not-found
```


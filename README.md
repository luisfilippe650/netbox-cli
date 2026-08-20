# netbox-cli

CLI em Python para consultar e administrar inventário físico no NetBox. Ela foi
projetada para dois modos de uso:

- uso humano, com menus, tabelas, painéis e árvores Rich;
- automação, CI/CD e agentes de IA, com JSON puro, códigos de saída e operações
  idempotentes.

A CLI cobre regiões, sites, locais, grupos de racks, racks, fabricantes, tipos de
dispositivos e dispositivos. Também oferece busca, inventário, inspeção,
capacidade, elevação de racks, rastreamento físico e árvores de infraestrutura.

## Sumário

- [Instalação](#instalação)
- [Primeiros passos](#primeiros-passos)
- [Configuração e autenticação](#configuração-e-autenticação)
- [Saída, erros e códigos de retorno](#saída-erros-e-códigos-de-retorno)
- [Referência rápida](#referência-rápida)
- [Consultas operacionais](#consultas-operacionais)
- [Regiões](#regiões)
- [Sites](#sites)
- [Locais](#locais)
- [Grupos de racks](#grupos-de-racks)
- [Racks](#racks)
- [Fabricantes](#fabricantes)
- [Tipos de dispositivos](#tipos-de-dispositivos)
- [Dispositivos](#dispositivos)
- [Idempotência e dry-run](#idempotência-e-dry-run)
- [Receitas de automação](#receitas-de-automação)
- [Uso com agentes de IA](#uso-com-agentes-de-ia)
- [Limites atuais](#limites-atuais)

## Instalação

### Pacote Debian para servidores Ubuntu

O pacote `.deb` inclui o runtime necessário e instala o comando em
`/usr/bin/netbox`. O servidor não precisa ter Python 3.11, `pip` ou ambiente
virtual.

```bash
sudo apt install ./dist/netbox-cli_0.1.0_amd64.deb
netbox --help
```

Para atualizar, instale o novo arquivo `.deb` com o mesmo comando. Para remover:

```bash
sudo apt remove netbox-cli
```

A configuração e o token pertencem ao usuário que executa a CLI e continuam em
`~/.config/netbox-cli/config.yaml`; eles não são incluídos nem removidos pelo
pacote.

O artefato `amd64` é construído no Ubuntu 20.04 com Python 3.11 e PyInstaller no
modo `onedir`. O mesmo pacote é instalado e executado automaticamente em
containers limpos com Ubuntu 20.04, 22.04, 24.04 e 26.04 antes de o build ser
considerado concluído.

### Gerando o `.deb`

O único requisito da máquina de build é Docker com acesso ao daemon:

```bash
./packaging/build-deb.sh
```

O script:

1. compila o Python 3.11 no Ubuntu 20.04;
2. empacota a CLI e suas dependências com PyInstaller `onedir`;
3. cria `dist/netbox-cli_<versão>_amd64.deb`;
4. instala exatamente esse arquivo nos Ubuntu 20.04, 22.04, 24.04 e 26.04;
5. valida `netbox --help`, `netbox tree --help` e o destino de `/usr/bin/netbox`.

O número da versão do pacote e do projeto vem de `netbox_cli.__version__`, que é
a fonte única da versão. As dependências do artefato estão fixadas em
`packaging/deb/constraints.txt` para que builds posteriores não incorporem
versões novas silenciosamente. Como o pacote contém binários, uma arquitetura
diferente, como `arm64`, deve ser construída nativamente ou com um builder Docker
configurado para essa arquitetura.

### Instalação para desenvolvimento

Para executar a partir do código-fonte, requer Python 3.11 ou posterior.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Depois da instalação, o comando principal é `netbox`:

```bash
netbox --help
```

Também é possível executar sem instalar o entry point:

```bash
python -m netbox_cli --help
```

Para instalar ou exibir completion do shell:

```bash
netbox --install-completion
netbox --show-completion
```

## Primeiros passos

Fluxo interativo:

```bash
netbox
```

O menu permite fazer login, alterar URL e timeout, verificar o estado da sessão
e remover o token local.

Para abrir diretamente o login:

```bash
netbox login
```

Depois do login, valide a conexão:

```bash
netbox status
netbox --output json status
```

Faça uma primeira consulta:

```bash
netbox search server-01
netbox --output json search server-01
```

## Configuração e autenticação

### Arquivo local

O login solicita usuário e senha. A senha fica oculta e nunca é armazenada. O
token provisionado é salvo em:

```text
~/.config/netbox-cli/config.yaml
```

Conteúdo:

```yaml
url: http://localhost:8000
token: ''
token_id: null
token_url: ''
timeout: 15
```

O diretório é protegido com permissão `0700` e o arquivo com `0600`. O token é
vinculado à URL em que foi provisionado; um token do arquivo não é enviado para
outra origem.

O login provisiona token v2, valida o token recém-criado e confirma que a conta é
superusuária antes de salvá-lo. Tokens fornecidos externamente continuam sujeitos
às permissões aplicadas pelo próprio NetBox.

### Variáveis de ambiente

Para containers, pipelines e runners efêmeros:

```bash
export NETBOX_URL="https://netbox.example.com"
export NETBOX_TOKEN="nbt_chave.token"
export NETBOX_TIMEOUT="30"

netbox --output json status
```

Variáveis disponíveis:

| Variável | Finalidade |
|---|---|
| `NETBOX_URL` | URL base do NetBox |
| `NETBOX_TOKEN` | Token v1 ou v2 da API |
| `NETBOX_TIMEOUT` | Timeout HTTP em segundos |
| `NETBOX_CONFIG` | Caminho alternativo para o YAML |
| `XDG_CONFIG_HOME` | Raiz padrão de configuração quando `NETBOX_CONFIG` não existe |

Quando URL, token e timeout vêm de fontes externas, a CLI funciona sem precisar
criar um arquivo de configuração.

### Opções globais

As opções globais devem aparecer antes do grupo ou comando:

```text
netbox [OPÇÕES GLOBAIS] COMANDO [OPÇÕES DO COMANDO]
```

| Opção | Finalidade |
|---|---|
| `--url URL` | Sobrescreve a URL |
| `--token TOKEN` | Sobrescreve o token |
| `--timeout SEGUNDOS` | Sobrescreve o timeout |
| `--config CAMINHO` | Seleciona outro YAML |
| `--output json\|human` | Força o formato global |

Exemplo:

```bash
netbox \
  --url https://netbox.example.com \
  --token "$NETBOX_TOKEN" \
  --timeout 20 \
  --output json \
  devices all
```

Prefira `NETBOX_TOKEN` a `--token`, pois argumentos podem aparecer no histórico
do shell e na listagem de processos.

### Precedência

Cada campo é resolvido nesta ordem:

```text
opção global > variável de ambiente > arquivo YAML > valor padrão
```

Assim, URL e token podem vir do ambiente enquanto o timeout continua vindo do
arquivo, por exemplo.

## Saída, erros e códigos de retorno

### Formatos

Os comandos CRUD usam JSON por padrão e aceitam tabela:

```bash
netbox sites list
netbox sites list --output table
```

Consultas operacionais usam apresentação humana por padrão e aceitam JSON:

```bash
netbox inspect server-01
netbox inspect server-01 --output json
```

Para garantir JSON em qualquer consulta, use a opção global antes do comando:

```bash
netbox --output json device tree server-01
```

Inventário também aceita CSV:

```bash
netbox inventory --rack RACK-04 --output csv > rack-04.csv
```

### stdout e stderr

- resultados são escritos em `stdout`;
- erros operacionais são escritos em `stderr`;
- no modo global `--output json`, erros operacionais também são JSON puro;
- erros de sintaxe continuam usando a ajuda do Typer.

Exemplo de erro estruturado:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Dispositivo 'server-99' não encontrado."
  }
}
```

### Códigos de saída

| Código | Significado |
|---:|---|
| `0` | Operação concluída |
| `1` | Falha operacional, autenticação inválida ou status não autorizado |
| `2` | Uso incorreto da linha de comando, produzido pelo parser |

Em scripts, use `set -o pipefail` para não perder o código da CLI quando houver
pipe para `jq`.

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
| `netbox device-types ...` | Tipos de dispositivos |
| `netbox devices ...` | Dispositivos |

`site`, `rack` e `device` são aliases singulares de `sites`, `racks` e `devices`.

Aliases ocultos mantidos por compatibilidade:

- `regions create`, `sites create` e `locations create` equivalem a `post`;
- `manufacturers list`, `device-types list` e `devices list` equivalem a `all`.

## Consultas operacionais

### `status`

Verifica URL, conectividade, existência e versão do token, autenticação e acesso
de superusuário.

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
```

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

A árvore do dispositivo inclui caminho de localização, interfaces, IPs,
equipamentos conectados e conexões dos demais componentes físicos.

## Regiões

### Criar ou convergir

```bash
netbox regions post --name Sudeste
netbox regions post \
  --name Sudeste \
  --slug sudeste \
  --description "Região Sudeste" \
  --ensure
netbox regions post --name Sudeste --ensure --dry-run
```

Opções: `--name`, `--slug`, `--description`, `--ensure`, `--dry-run` e
`--output json|table`.

Com `--ensure`, nome identifica a região. Em um recurso existente, apenas opções
explicitamente informadas participam do PATCH.

### Consultar e listar

```bash
netbox regions view 1
netbox regions list
netbox regions list --search sudeste
netbox regions list --limit 0
netbox regions list --output table
```

`--limit 0` percorre todas as páginas.

### Excluir

```bash
netbox regions delete 1
netbox regions delete 1 --dry-run
netbox regions delete 1 --ignore-not-found
```

## Sites

### Criar ou convergir

```bash
netbox sites post --name CPTEC
netbox sites post \
  --name CPTEC \
  --slug cptec \
  --status active \
  --region 1 \
  --description "Site principal" \
  --ensure
netbox sites post --name CPTEC --region 1 --ensure --dry-run
```

Opções: `--name`, `--slug`, `--status`, `--region ID`, `--description`,
`--ensure`, `--dry-run` e `--output json|table`.

### Consultar e listar

```bash
netbox sites view 1
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

### Excluir

```bash
netbox sites delete 1
netbox sites delete 1 --dry-run
netbox sites delete 1 --ignore-not-found
```

## Locais

Locations pertencem a um site e podem ter um local pai.

### Criar ou convergir

```bash
netbox locations post --name Datacenter --site 1
netbox locations post \
  --name Datacenter \
  --site 1 \
  --slug datacenter \
  --status active \
  --parent 2 \
  --description "Sala principal" \
  --ensure
netbox locations post --name Datacenter --site 1 --ensure --dry-run
```

Opções: `--name`, `--site ID`, `--slug`, `--status`, `--parent ID`,
`--description`, `--ensure`, `--dry-run` e `--output json|table`.

O `--ensure` identifica o local pela combinação nome e site.

### Consultar, listar e excluir

```bash
netbox locations view 1
netbox locations list
netbox locations list --search data
netbox locations list --limit 0
netbox locations delete 1 --dry-run
netbox locations delete 1 --ignore-not-found
```

## Grupos de racks

### Criar ou convergir

```bash
netbox rack-groups post --name "Corredor A"
netbox rack-groups post --name "Corredor A" --ensure
netbox rack-groups post --name "Corredor A" --ensure --dry-run
```

O slug é gerado automaticamente pelo nome.

### Consultar e listar

```bash
netbox rack-groups get 1
netbox rack-groups all
netbox rack-groups all --search corredor
netbox rack-groups all --limit 20
netbox rack-groups all --output table
```

Sem `--limit`, `all` percorre todas as páginas. `--limit 0` também representa
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
netbox racks post \
  --site 1 \
  --name RACK-04 \
  --width 19 \
  --starting-unit 1 \
  --u-height 42
```

Com vínculos opcionais:

```bash
netbox racks post \
  --site 1 \
  --name RACK-04 \
  --width 19 \
  --starting-unit 1 \
  --u-height 42 \
  --group 2 \
  --role 3 \
  --type 4 \
  --ensure
```

Simulação idempotente:

```bash
netbox --output json racks post \
  --site 1 \
  --name RACK-04 \
  --width 19 \
  --starting-unit 1 \
  --u-height 42 \
  --ensure \
  --dry-run
```

Campos obrigatórios: `--site`, `--name`, `--width`, `--starting-unit` e
`--u-height`. Larguras aceitas: `10`, `19`, `21` e `23`. O status inicial é
`active`. Grupo, função e tipo são IDs opcionais.

O `--ensure` identifica o rack por nome e site. Defaults de criação, como status,
não sobrescrevem um rack existente quando não foram informados.

### Consultar e listar

```bash
netbox racks get 4
netbox racks all
netbox racks all --search RACK-04
netbox racks all --limit 25
netbox racks all --output table
```

### Atualizar

```bash
netbox racks update 4 --name RACK-04A
netbox racks update 4 --u-height 48 --role 3
netbox racks update 4 --u-height 48 --dry-run
```

Campos disponíveis: `--site`, `--name`, `--width`, `--starting-unit`,
`--u-height`, `--group`, `--role|--function` e `--type|--rack-type`.

O update altera somente campos informados. O dry-run consulta o rack e mostra
apenas as diferenças reais.

### Elevação

```bash
netbox rack show RACK-04
netbox rack show RACK-04 --face rear
netbox rack show RACK-04 --site CPTEC --location Datacenter
netbox --output json rack show RACK-04
```

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
netbox manufacturers post --name Dell
netbox manufacturers post \
  --name Dell \
  --comments "Fornecedor principal" \
  --ensure
netbox manufacturers post --name Dell --ensure --dry-run
```

O nome identifica o fabricante. `--comments|--comment` é opcional.

### Consultar, listar e excluir

```bash
netbox manufacturers get 10
netbox manufacturers all
netbox manufacturers all --search dell
netbox manufacturers all --limit 20
netbox manufacturers all --output table
netbox manufacturers delete 10 --dry-run
netbox manufacturers delete 10 --ignore-not-found
```

## Tipos de dispositivos

### Criar ou convergir

```bash
netbox device-types post \
  --manufacturer 10 \
  --model "PowerEdge R650" \
  --u-height 1

netbox device-types post \
  --manufacturer 10 \
  --model "PowerEdge R650" \
  --u-height 1 \
  --ensure
```

Campos obrigatórios: fabricante por ID, modelo e altura. O `--ensure` identifica
o tipo pela combinação fabricante e modelo.

### Consultar, listar e excluir

```bash
netbox device-types get 15
netbox device-types all
netbox device-types all --search PowerEdge
netbox device-types all --limit 20
netbox device-types all --output table
netbox device-types delete 15 --dry-run
netbox device-types delete 15 --ignore-not-found
```

## Dispositivos

### Criar ou convergir

Cadastro mínimo:

```bash
netbox devices post \
  --name server-01 \
  --role 2 \
  --device-type 15 \
  --site 1
```

Cadastro montado em rack:

```bash
netbox devices post \
  --name server-01 \
  --role 2 \
  --device-type 15 \
  --site 1 \
  --serial ABC123 \
  --location 3 \
  --rack 4 \
  --position 10
```

Quando `--position` é informado, `--rack` é obrigatório e a face é `front`.
Posições aceitam incrementos de meia unidade.

Campos personalizados usam um objeto JSON:

```bash
netbox devices post \
  --name server-01 \
  --role 2 \
  --device-type 15 \
  --site 1 \
  --custom-fields '{"patrimonio":"PAT-001","monitorado":true}'
```

A CLI consulta os campos personalizados aplicáveis a `dcim.device` e recusa a
criação quando um campo obrigatório não foi fornecido.

Modo idempotente:

```bash
netbox --output json devices post \
  --name server-01 \
  --role 2 \
  --device-type 15 \
  --site 1 \
  --serial ABC123 \
  --ensure
```

O `--ensure` identifica o dispositivo por nome e site. Em dispositivos
existentes, somente opções explicitamente informadas são atualizadas;
`custom_fields={}` e `status=active` não são aplicados implicitamente.

### Consultar e listar

```bash
netbox devices get 30
netbox devices all
netbox devices all --search server
netbox devices all --limit 50
netbox devices all --output table
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

## Idempotência e dry-run

### `post --ensure`

O fluxo de convergência é:

```text
resolver identidade e escopo
        │
        ├── não existe ──> criar
        │
        └── existe ──────> comparar somente opções explícitas
                               │
                               ├── diferente ──> PATCH
                               └── igual ──────> changed: false
```

Identidades usadas:

| Recurso | Identidade |
|---|---|
| Região | nome |
| Site | nome |
| Location | nome + site |
| Grupo de racks | nome |
| Rack | nome + site |
| Fabricante | nome |
| Tipo de dispositivo | modelo + fabricante |
| Dispositivo | nome + site |

Respostas típicas:

```json
{
  "action": "unchanged",
  "changed": false,
  "resource": {
    "id": 30,
    "name": "server-01"
  }
}
```

```json
{
  "action": "updated",
  "changed": true,
  "changes": {
    "serial": "ABC123"
  },
  "resource": {
    "id": 30,
    "name": "server-01"
  }
}
```

### `--dry-run`

O dry-run permite leitura, mas nunca envia mutações `POST`, `PATCH` ou `DELETE`.
Ele é útil para aprovação humana, logs de pipeline e agentes de IA.

```bash
plan=$(netbox --output json racks update 4 --u-height 48 --dry-run)
echo "$plan" | jq .

if jq -e '.changed == true' <<<"$plan" > /dev/null; then
  netbox --output json racks update 4 --u-height 48
fi
```

### Exclusão repetível

```bash
netbox --output json devices delete 30 --ignore-not-found
```

Se o dispositivo já não existir:

```json
{
  "deleted": false,
  "changed": false,
  "not_found": true,
  "resource": "device",
  "id": 30
}
```

## Receitas de automação

Os exemplos abaixo usam `jq`. Ative tratamento rigoroso de erros:

```bash
set -euo pipefail
```

### Criar a estrutura base

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${NETBOX_URL:?defina NETBOX_URL}"
: "${NETBOX_TOKEN:?defina NETBOX_TOKEN}"

REGION_ID=$(
  netbox --output json regions post \
    --name Sudeste \
    --description "Região Sudeste" \
    --ensure |
  jq -er '.resource.id'
)

SITE_ID=$(
  netbox --output json sites post \
    --name CPTEC \
    --region "$REGION_ID" \
    --ensure |
  jq -er '.resource.id'
)

LOCATION_ID=$(
  netbox --output json locations post \
    --name Datacenter \
    --site "$SITE_ID" \
    --ensure |
  jq -er '.resource.id'
)

RACK_ID=$(
  netbox --output json racks post \
    --site "$SITE_ID" \
    --name RACK-04 \
    --width 19 \
    --starting-unit 1 \
    --u-height 42 \
    --ensure |
  jq -er '.resource.id'
)

echo "region=$REGION_ID site=$SITE_ID location=$LOCATION_ID rack=$RACK_ID"
```

O cadastro de racks ainda não possui `--location`; portanto, a associação do rack
ao local precisa existir previamente no NetBox ou ser feita por outra integração.
O ID da location foi mantido no exemplo para os cadastros de dispositivos.

### Cadastrar fabricante, tipo e dispositivo

Função e site precisam existir; neste exemplo `DEVICE_ROLE_ID` vem de outra
fonte porque funções de dispositivos ainda não possuem CRUD nesta CLI.

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${DEVICE_ROLE_ID:?defina DEVICE_ROLE_ID}"
: "${SITE_ID:?defina SITE_ID}"
: "${LOCATION_ID:?defina LOCATION_ID}"

MANUFACTURER_ID=$(
  netbox --output json manufacturers post \
    --name Dell \
    --ensure |
  jq -er '.resource.id'
)

DEVICE_TYPE_ID=$(
  netbox --output json device-types post \
    --manufacturer "$MANUFACTURER_ID" \
    --model "PowerEdge R650" \
    --u-height 1 \
    --ensure |
  jq -er '.resource.id'
)

netbox --output json devices post \
  --name server-01 \
  --role "$DEVICE_ROLE_ID" \
  --device-type "$DEVICE_TYPE_ID" \
  --site "$SITE_ID" \
  --location "$LOCATION_ID" \
  --serial ABC123 \
  --ensure
```

### Encontrar espaço e mover um dispositivo

```bash
POSITIONS=$(
  netbox --output json rack available RACK-04 \
    --site CPTEC \
    --height 2
)

POSITION=$(jq -er '.positions[0]' <<<"$POSITIONS")

netbox --output json device move server-01 \
  --device-site CPTEC \
  --rack RACK-04 \
  --rack-site CPTEC \
  --position "$POSITION" \
  --dry-run

netbox --output json device move server-01 \
  --device-site CPTEC \
  --rack RACK-04 \
  --rack-site CPTEC \
  --position "$POSITION"
```

### Exportar inventário periodicamente

```bash
#!/usr/bin/env bash
set -euo pipefail

destination="inventario-$(date +%F).csv"
netbox inventory --site CPTEC --output csv > "$destination"
echo "Inventário salvo em $destination"
```

### Health check para pipeline

```bash
#!/usr/bin/env bash
set -euo pipefail

status_file=$(mktemp)
error_file=$(mktemp)
trap 'rm -f "$status_file" "$error_file"' EXIT

if netbox --output json status >"$status_file" 2>"$error_file"; then
  jq -e '.authorized == true' "$status_file" > /dev/null
else
  jq . "$status_file" 2>/dev/null || true
  jq . "$error_file" 2>/dev/null || true
  exit 1
fi
```

### Exemplo de CI

Exemplo genérico para GitHub Actions:

```yaml
name: NetBox automation

on:
  workflow_dispatch:

jobs:
  inventory:
    runs-on: ubuntu-latest
    env:
      NETBOX_URL: ${{ secrets.NETBOX_URL }}
      NETBOX_TOKEN: ${{ secrets.NETBOX_TOKEN }}
      NETBOX_TIMEOUT: '30'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e .
      - run: netbox --output json status
      - run: |
          netbox --output json manufacturers post \
            --name Dell \
            --ensure \
            --dry-run
```

Guarde o token em secrets do provedor de CI; não o escreva no repositório nem no
log do pipeline.

## Uso com agentes de IA

Para agentes, prefira sempre:

```bash
netbox --output json ...
```

Fluxo recomendado:

1. Executar `status` e interromper se `authorized` não for verdadeiro.
2. Usar `search`, `tree` ou `inspect` para descobrir o estado atual.
3. Informar `--site` e `--location` quando nomes puderem ser repetidos.
4. Para criação declarativa, usar `post --ensure`.
5. Antes de uma mutação sensível, executar o mesmo comando com `--dry-run`.
6. Examinar `changed`, `action` e `changes` no JSON.
7. Aplicar sem `--dry-run` somente quando o plano for esperado.
8. Em exclusões repetíveis, usar `--ignore-not-found`.
9. Nunca interpretar tabelas Rich; consumir somente JSON ou CSV.
10. Tratar código diferente de zero como falha, mesmo que exista saída parcial.

Exemplo de política para um agente:

```text
Antes de alterar o NetBox:
- obtenha o contexto com search/tree/inspect em JSON;
- não escolha silenciosamente entre nomes ambíguos;
- execute dry-run;
- descreva os campos que mudarão;
- aplique somente após aprovação;
- consulte novamente o recurso e confirme o estado final.
```

Exemplo de sequência:

```bash
netbox --output json search server-01
netbox --output json device tree server-01 --site CPTEC
netbox --output json device move server-01 \
  --device-site CPTEC \
  --rack RACK-04 \
  --rack-site CPTEC \
  --position 10 \
  --dry-run
netbox --output json device move server-01 \
  --device-site CPTEC \
  --rack RACK-04 \
  --rack-site CPTEC \
  --position 10
netbox --output json device tree server-01 --site CPTEC
```

## Limites atuais

A CLI não é uma interface genérica para todos os endpoints do NetBox. Ainda não
há CRUD para:

- funções de dispositivos e racks;
- associação de um rack a uma location durante criação ou update;
- interfaces;
- endereços IP, prefixes, VLANs e VRFs;
- cabos;
- tenants;
- tipos genéricos/content types;
- operações em lote por JSON ou JSONL.

Vários cadastros ainda recebem IDs de relacionamentos, como fabricante, função,
site, rack e tipo do dispositivo. Os comandos de movimentação e consulta já
resolvem nomes e recusam ambiguidades, mas a criação ainda depende desses IDs.

`--ensure` executa consulta seguida de criação ou atualização. Duas automações
concorrentes ainda podem disputar a criação do mesmo recurso; as restrições de
unicidade do NetBox continuam sendo a proteção final.

Use a ajuda instalada como fonte definitiva para a versão em execução:

```bash
netbox --help
netbox devices --help
netbox devices post --help
netbox rack tree --help
```

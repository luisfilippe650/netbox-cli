# Automação e agentes de IA

[English](../automation.md)

## Idempotência e dry-run

### `create --ensure`

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

### Contrato JSON e `--output id`

Uma criação sem `--ensure` retorna diretamente o objeto da API, portanto o ID
fica em `.id`. Com `--ensure`, a resposta inclui metadados de convergência e o
objeto fica em `.resource`, portanto o ID fica em `.resource.id`:

| Operação | Caminho JSON do ID |
|---|---|
| Criação normal | `.id` |
| `--ensure`: criado, atualizado ou inalterado | `.resource.id` |
| Update em `--dry-run` | `.resource.id` |
| Criação em `--dry-run` | Não há ID; o recurso ainda não existe |

Para scripts não precisarem conhecer esses envelopes, use `--output id`:

```bash
DEVICE_ID=$(netbox devices create \
  --name server-01 \
  --role Servidor \
  --device-type "PowerEdge R650" \
  --site CPTEC \
  --ensure \
  --output id)
```

O comando imprime somente o valor, como `30`. Também é possível usar a opção
global: `netbox --output id devices create ...`. Se a operação não possuir ID,
como uma criação com `--dry-run`, a CLI encerra com código 1 e explica o motivo.

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
  netbox --output id regions create \
    --name Sudeste \
    --description "Região Sudeste" \
    --ensure
)

SITE_ID=$(
  netbox --output id sites create \
    --name CPTEC \
    --region "$REGION_ID" \
    --ensure
)

LOCATION_ID=$(
  netbox --output id locations create \
    --name Datacenter \
    --site "$SITE_ID" \
    --ensure
)

RACK_ID=$(
  netbox --output id racks create \
    --site "$SITE_ID" \
    --name RACK-04 \
    --width 19 \
    --starting-unit 1 \
    --u-height 42 \
    --location "$LOCATION_ID" \
    --ensure
)

echo "region=$REGION_ID site=$SITE_ID location=$LOCATION_ID rack=$RACK_ID"
```

O rack é associado à location criada anteriormente. Assim, dispositivos podem
usar simultaneamente `--rack` e `--location` sem violar o escopo validado pelo
NetBox.

### Cadastrar fabricante, tipo e dispositivo

Função e site precisam existir. Ambos podem ser informados por nome ou slug,
sem consulta prévia do ID.

```bash
#!/usr/bin/env bash
set -euo pipefail

MANUFACTURER_ID=$(
  netbox --output id manufacturers create \
    --name Dell \
    --ensure
)

DEVICE_TYPE_ID=$(
  netbox --output id device-types create \
    --manufacturer "$MANUFACTURER_ID" \
    --model "PowerEdge R650" \
    --u-height 1 \
    --ensure
)

netbox --output json devices create \
  --name server-01 \
  --role Servidor \
  --device-type "$DEVICE_TYPE_ID" \
  --site CPTEC \
  --location Datacenter \
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
          netbox --output json manufacturers create \
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
4. Para criação declarativa, usar `create --ensure`.
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

- endereços IP, prefixes, VLANs e VRFs;
- funções de racks;
- tenants;
- tipos genéricos/content types;
- operações em lote por JSON ou JSONL.

Relacionamentos cobertos pela CLI aceitam ID, nome exato ou slug sempre que o
recurso possui esses campos. Buscas contextuais, como rack e localização, são
restritas ao site e recusam ambiguidades.

`--ensure` executa consulta seguida de criação ou atualização. Duas automações
concorrentes ainda podem disputar a criação do mesmo recurso; as restrições de
unicidade do NetBox continuam sendo a proteção final.

Use a ajuda instalada como fonte definitiva para a versão em execução:

```bash
netbox --help
netbox devices --help
netbox devices create --help
netbox rack tree --help
```

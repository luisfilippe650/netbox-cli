# Configuração e saída

[English](../configuration.md)

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
| `--version` | Exibe a versão instalada da CLI e encerra |
| `--url URL` | Sobrescreve a URL |
| `--token TOKEN` | Sobrescreve o token |
| `--timeout SEGUNDOS` | Sobrescreve o timeout |
| `--config CAMINHO` | Seleciona outro YAML |
| `--output json\|human\|id` | Força o formato global |
| `--retries N` | Repete leituras após falhas transitórias; padrão 2 |
| `--backoff SEGUNDOS` | Espera inicial exponencial; padrão 0,5 s |
| `--verbose`, `-v` | Mostra endpoint, tentativa, timeout e resposta |
| `--debug` | Ativa verbose e inclui tipo da exceção e traceback |

Exemplo:

```bash
netbox \
  --url https://netbox.example.com \
  --token "$NETBOX_TOKEN" \
  --timeout 20 \
  --output json \
  devices list
```

Prefira `NETBOX_TOKEN` a `--token`, pois argumentos podem aparecer no histórico
do shell e na listagem de processos.

### Diagnóstico e novas tentativas

Erros de comunicação exibem sempre método, endpoint, timeout por tentativa,
quantidade de tentativas realizadas e causa resumida. Para acompanhar cada
requisição:

```bash
netbox \
  --timeout 5 \
  --retries 3 \
  --backoff 0.5 \
  --verbose \
  devices list
```

O backoff é exponencial: com `--backoff 0.5`, as esperas são 0,5 s, 1 s e 2 s.
O cabeçalho HTTP `Retry-After`, quando numérico, tem precedência.

São repetidas somente leituras `GET`, `HEAD` e `OPTIONS` após timeout, falha de
conexão, HTTP 429, 500, 502, 503 ou 504. Mutações `POST` e `PATCH` não são
repetidas automaticamente, evitando duplicação caso o servidor tenha processado
a operação antes da conexão cair.

Use `--debug` quando o resumo não for suficiente. O traceback é enviado para
stderr e nunca inclui o token ou o corpo enviado pela requisição.

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


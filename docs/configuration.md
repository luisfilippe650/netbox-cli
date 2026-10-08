# Configuration and output

[Português](pt/configuration.md)

## Local authentication

Login prompts for a username and hidden password. The password is never stored.
Login provisions and validates a v2 token and verifies superuser access before
saving it in `~/.config/netbox-cli/config.yaml`:

```yaml
url: http://localhost:8000
token: ''
token_id: null
token_url: ''
timeout: 15
```

The directory has mode `0700` and the file has mode `0600`. Saved tokens are bound
to the URL where they were provisioned and are not sent to another origin.
Externally supplied tokens remain subject to NetBox permissions.

## Environment and precedence

| Variable | Purpose |
| --- | --- |
| `NETBOX_URL` | NetBox base URL |
| `NETBOX_TOKEN` | v1 or v2 API token |
| `NETBOX_TIMEOUT` | HTTP timeout in seconds |
| `NETBOX_CONFIG` | Alternative YAML configuration path |
| `XDG_CONFIG_HOME` | Configuration root when `NETBOX_CONFIG` is absent |

Each value is resolved independently:

```text
global option > environment variable > YAML file > default
```

When external sources supply URL, token and timeout, no configuration file is
required. Prefer `NETBOX_TOKEN` to command arguments, which can appear in shell
history or process listings.

## Global options

Global options precede the command or resource group:

```text
netbox [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

| Option | Purpose |
| --- | --- |
| `--version` | Print CLI version and exit |
| `--url URL` | Override base URL |
| `--token TOKEN` | Override token |
| `--timeout SECONDS` | Override timeout |
| `--config PATH` | Select another YAML file |
| `--output json\|human\|id` | Force global output format |
| `--retries N` | Retry transient read failures; default 2 |
| `--backoff SECONDS` | Initial exponential delay; default 0.5 |
| `--verbose`, `-v` | Show request endpoint, attempts, timeout and response |
| `--debug` | Enable verbose output and exception traceback |

```bash
netbox --url https://netbox.example.com --timeout 20 --output json devices list
netbox --timeout 5 --retries 3 --backoff 0.5 --verbose devices list
```

Only `GET`, `HEAD` and `OPTIONS` are retried after timeouts, connection failures or
HTTP 429, 500, 502, 503 and 504. `POST` and `PATCH` are not automatically retried.
Backoff doubles on each retry; a numeric `Retry-After` takes precedence.
Communication errors include method, endpoint, timeout, attempts and cause.
Debug tracebacks go to stderr without tokens or request bodies.

## Output and errors

CRUD commands default to JSON and accept tables. Operational queries default to
human output and accept JSON. Global `--output json` forces structured output.

```bash
netbox sites list --output table
netbox inspect server-01 --output json
netbox --output json device tree server-01
netbox inventory --rack RACK-04 --output csv > rack-04.csv
```

Results go to stdout; operational errors go to stderr. Global JSON mode also
formats operational errors as JSON with `error.code` and `error.message`. Parser
errors continue to use Typer help. Some CLI messages and API values may remain in
Portuguese; the English documentation does not change the runtime language.

| Exit code | Meaning |
| ---: | --- |
| 0 | Operation completed |
| 1 | Operational failure, invalid authentication or unauthorized status |
| 2 | Invalid command-line usage |

Use `set -o pipefail` when piping output to `jq` so the CLI failure is preserved.

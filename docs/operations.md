# Operational queries and connectivity

[Português](pt/operations.md)

## Command groups

CRUD groups share `list`, `get`, `create`, `update` and `delete`:
`regions`, `sites`, `locations`, `rack-groups`, `racks`, `manufacturers`,
`device-roles`, `device-types`, `devices`, `interfaces`, `front-ports`,
`rear-ports`, `console-ports`, `power-ports` and `cables`.

`site`, `rack` and `device` are singular aliases. Hidden compatibility aliases
include `post` for `create`, `all` for `list`, and `view` for `get` in regions,
sites and locations. Prefer the canonical names in new scripts.

## `status`

Checks CLI version, connectivity, token version, authentication and superuser access. Exit code is zero only when `authorized` is true; JSON exposes `cli_version`.

```bash
netbox status
netbox --output json status
```

```bash
if netbox --output json status > status.json; then
  echo "NetBox pronto"
else
  jq . status.json
  exit 1
fi
```

## `search`

Searches devices, racks, sites, locations and IP addresses. `--limit` is the maximum per resource type and defaults to 10.

```bash
netbox search server-01
netbox search 10.10.0.23 --limit 20
netbox --output json search server-01
```

## `inspect`

Looks up an exact device name. Supply `--site` to resolve repeated names. Shows location, mounting, status, connected interfaces and IPs.

```bash
netbox inspect server-01
netbox inspect server-01 --site CPTEC
netbox --output json inspect server-01 --site CPTEC
```

## `inventory`

Requires `--site` or `--rack`. `--location` requires `--rack` and narrows rack lookup. Export JSON or CSV, or use `--wide`, `--no-truncate` and `--columns` for human tables. CSV has stable device identity, role, type, placement, status, IP and serial columns; column selection does not alter JSON.

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

## `trace`

Traces a device interface through cables recorded in NetBox. Use the site context for duplicate device names.

```bash
netbox trace server-01 eth0
netbox trace server-01 eth0 --site CPTEC
netbox --output json trace server-01 eth0 --site CPTEC
```

## `tree`

Shows the region, site, location, rack and device hierarchy. Use filters to narrow the tree and JSON to consume it in automation.

```bash
netbox tree
netbox tree --site CPTEC
netbox --output json tree --site CPTEC
```

```bash
netbox rack tree RACK-04
netbox rack tree RACK-04 --site CPTEC --location Datacenter
netbox --output json rack tree RACK-04 --site CPTEC
```

```bash
netbox device tree server-01
netbox device tree server-01 --site CPTEC
netbox --output json device tree server-01 --site CPTEC
```

## Interfaces

Create, list, update and delete interfaces on a device.

```bash
netbox interfaces create \
  --device switch-01 \
  --name Gi0/1 \
  --type 1000base-t
netbox interfaces list --device switch-01
netbox interfaces update 10 --description "Uplink principal"
netbox interfaces delete 10 --dry-run
```

## Patch panels

Create the rear port first, then associate the front port using the rear port ID or name.

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

## Console and power

Manage console and power ports, including connector type, speed and maximum draw.

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

## Cables

Cable endpoint types are `interface`, `front-port`, `rear-port`, `console-port` and `power-port`. Use dry-run to review resolved IDs and payloads. Repeated deletion supports `--ignore-not-found`. Device trees include physical components and their connections.

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

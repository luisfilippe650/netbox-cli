# Automation and AI agents

[Português](pt/automation.md)

## Idempotency with `create --ensure`

The CLI resolves the resource identity and scope, creates it if missing, or
compares only explicitly supplied fields and patches differences. Matching state
returns `changed: false`. Possible actions include `created`, `updated` and
`unchanged`.

| Resource | Identity |
| --- | --- |
| Region, rack group, manufacturer | Name |
| Site | Name |
| Location, rack, device | Name + site |
| Device type | Model + manufacturer |

```bash
netbox manufacturers create --name Dell --ensure
netbox manufacturers create --name Dell --ensure --dry-run
```

## JSON envelopes and IDs

A normal creation returns the API object directly (`.id`). `--ensure` returns
convergence metadata and the object in `.resource` (`.resource.id`). Update
dry-run also exposes `.resource.id`; creation dry-run has no ID yet.

```json
{
  "action": "unchanged",
  "changed": false,
  "resource": {"id": 30, "name": "server-01"}
}
```

Use `--output id` in scripts to avoid depending on these envelopes. It prints only
the ID. An operation without an ID, including creation dry-run, fails with code 1.

## Previewing and deleting

Dry-run permits reads but never sends `POST`, `PATCH` or `DELETE` mutations.

```bash
netbox --output json racks update 4 --u-height 48 --dry-run
netbox --output json devices delete 30 --ignore-not-found
```

Deleting an absent resource with `--ignore-not-found` reports `deleted: false`,
`changed: false`, `not_found: true`, plus resource type and ID.

## Create a base inventory

The role in this example must already exist. Replace sample names with your own.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${NETBOX_URL:?set NETBOX_URL}"
: "${NETBOX_TOKEN:?set NETBOX_TOKEN}"

REGION_ID=$(netbox --output id regions create --name Southeast --ensure)
SITE_ID=$(netbox --output id sites create --name Main --region "$REGION_ID" --ensure)
LOCATION_ID=$(netbox --output id locations create --name Datacenter --site "$SITE_ID" --ensure)
RACK_ID=$(netbox --output id racks create --name RACK-04 --site "$SITE_ID" \
  --location "$LOCATION_ID" --width 19 --starting-unit 1 --u-height 42 --ensure)
MANUFACTURER_ID=$(netbox --output id manufacturers create --name Dell --ensure)
DEVICE_TYPE_ID=$(netbox --output id device-types create --manufacturer "$MANUFACTURER_ID" \
  --model "PowerEdge R650" --u-height 1 --ensure)
netbox --output json devices create --name server-01 --role Server \
  --device-type "$DEVICE_TYPE_ID" --site "$SITE_ID" --location "$LOCATION_ID" \
  --serial ABC123 --ensure
```

## Find space and move a device

Requires `jq`. Preview the move, review it, then run without `--dry-run` to apply.

```bash
set -euo pipefail
POSITIONS=$(netbox --output json rack available RACK-04 --site Main --height 2)
POSITION=$(jq -er '.positions[0]' <<<"$POSITIONS")
netbox --output json device move server-01 --device-site Main \
  --rack RACK-04 --rack-site Main --position "$POSITION" --dry-run
```

## Export inventory and check health

```bash
set -euo pipefail
netbox inventory --site Main --output csv > inventory.csv
netbox --output json status > status.json
jq -e '.authorized == true' status.json
```

Store tokens in your CI provider's secrets. A pipeline can install with
`pip install -e .`, run `netbox --output json status`, and preview an operation
using `--ensure --dry-run`. Never put tokens in the repository or pipeline logs.

## AI agent workflow

1. Check `status` and stop unless `authorized` is true.
2. Discover current state with JSON `search`, `tree` or `inspect`.
3. Supply site/location context and reject ambiguous names.
4. Use `create --ensure` for declarative creation.
5. Preview sensitive mutations using `--dry-run`.
6. Inspect `changed`, `action` and `changes` before applying the intended plan.
7. Query the resource again to confirm the final state.
8. Use `--ignore-not-found` for repeatable deletion.
9. Consume JSON or CSV rather than Rich tables.
10. Treat a nonzero exit code as failure even when partial output exists.

## Current limits

The CLI is not a generic interface for every NetBox endpoint. It does not yet
provide CRUD for IP addresses, prefixes, VLANs, VRFs, rack roles, tenants,
generic/content types or bulk JSON/JSONL operations.

`--ensure` performs lookup followed by creation or update. Concurrent automation
can race to create the same resource; NetBox uniqueness constraints remain the
final protection. Installed command help is the authoritative reference:

```bash
netbox --help
netbox devices --help
netbox devices create --help
netbox rack tree --help
```

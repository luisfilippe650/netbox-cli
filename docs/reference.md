# Resource command reference

[Português](pt/reference.md)

All resource groups expose the same CRUD contract. `--ensure` supports repeatable
creation, `--dry-run` previews mutations, and `--ignore-not-found` makes repeated
deletion safe. Relationship lookup rejects ambiguous names. Examples below retain
sample names such as `Servidor` and `Sudeste`; replace them with your inventory
values. Run `netbox RESOURCE COMMAND --help` for the installed option reference.

## Regions

Identity for `--ensure` is the name. Only explicitly supplied fields are patched. `--limit 0` traverses all pages.

### Create or converge

```bash
netbox regions create --name Sudeste
netbox regions create \
  --name Sudeste \
  --slug sudeste \
  --description "Região Sudeste" \
  --ensure
netbox regions create --name Sudeste --ensure --dry-run
```

### Get and list

```bash
netbox regions get 1
netbox regions list
netbox regions list --search sudeste
netbox regions list --limit 0
netbox regions list --output table
```

### Update and delete

```bash
netbox regions update 1 --name "Sudeste Brasil"
netbox regions delete 1
netbox regions delete 1 --dry-run
netbox regions delete 1 --ignore-not-found
```

## Sites

Regions accept ID, exact name or slug. Site status aggregates racks, devices, occupied/free units, utilization and manufacturers.

### Create or converge

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

### Get and list

```bash
netbox sites get 1
netbox sites list
netbox sites list --search cptec
netbox sites list --limit 0
netbox sites list --output table
```

### Operational summary

```bash
netbox site status CPTEC
netbox --output json site status CPTEC
```

### Update and delete

```bash
netbox sites update 1 --status active --region Sudeste
netbox sites delete 1
netbox sites delete 1 --dry-run
netbox sites delete 1 --ignore-not-found
```

## Locations

Locations belong to a site and may have a parent. Identity is name plus site. Site and parent accept ID, exact name or slug.

### Create or converge

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

### Get, list, update and delete

```bash
netbox locations get 1
netbox locations list
netbox locations list --search data
netbox locations list --limit 0
netbox locations update 1 --description "Sala principal"
netbox locations delete 1 --dry-run
netbox locations delete 1 --ignore-not-found
```

## Rack groups

Slugs are generated from names. Without a limit, or with `--limit 0`, listing retrieves all pages. An unchanged update dry-run reports `changed: false`.

### Create or converge

```bash
netbox rack-groups create --name "Corredor A"
netbox rack-groups create --name "Corredor A" --ensure
netbox rack-groups create --name "Corredor A" --ensure --dry-run
```

### Get and list

```bash
netbox rack-groups get 1
netbox rack-groups list
netbox rack-groups list --search corredor
netbox rack-groups list --limit 20
netbox rack-groups list --output table
```

### Update

```bash
netbox rack-groups update 1 --name "Corredor B"
netbox rack-groups update 1 --name "Corredor B" --dry-run
```

### Delete

```bash
netbox rack-groups delete 1
netbox rack-groups delete 1 --dry-run
netbox rack-groups delete 1 --ignore-not-found
```

## Racks

Identity is name plus site. Use the site and location context to resolve duplicate rack names. Operational commands expose rack status, elevation, capacity and available positions.

### Create or converge

```bash
netbox racks create \
  --site "Site Teste" \
  --name RACK-04 \
  --width 19 \
  --starting-unit 1 \
  --u-height 42
```

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

### Get and list

```bash
netbox racks get 4
netbox racks list
netbox racks list --search RACK-04
netbox racks list --limit 25
netbox racks list --output table
```

### Update

```bash
netbox racks update 4 --name RACK-04A
netbox racks update 4 --location 3
netbox racks update 4 --location "Sala Teste"
netbox racks update 4 --u-height 48 --role 3
netbox racks update 4 --u-height 48 --dry-run
```

### Elevação

```bash
netbox rack show 4
netbox rack show RACK-04
netbox rack show RACK-04 --face rear
netbox rack show RACK-04 --site CPTEC --location Datacenter
netbox --output json rack show RACK-04
```

### Posições disponíveis

```bash
netbox rack available RACK-04 --height 2
netbox rack available RACK-04 --height 0.5 --face rear
netbox rack available RACK-04 \
  --height 2 \
  --site CPTEC \
  --location Datacenter
```

### Capacidade

```bash
netbox rack capacity RACK-04
netbox rack capacity RACK-04 --site CPTEC --location Datacenter
netbox --output json rack capacity RACK-04
```

### Árvore

```bash
netbox rack tree RACK-04
netbox rack tree RACK-04 --site CPTEC --location Datacenter
netbox --output json rack tree RACK-04
```

### Delete

```bash
netbox racks delete 4
netbox racks delete 4 --dry-run
netbox racks delete 4 --ignore-not-found
```

## Manufacturers

Identity is the manufacturer name. Use `--ensure` to converge an existing resource.

### Create or converge

```bash
netbox manufacturers create --name Dell
netbox manufacturers create \
  --name Dell \
  --comments "Fornecedor principal" \
  --ensure
netbox manufacturers create --name Dell --ensure --dry-run
```

### Get, list, update and delete

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

## Device roles

Slugs are generated from names. `create --ensure` creates or converges a role.

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

## Device types

Manufacturer, model and height are required. Manufacturer accepts ID, exact name or slug. Identity is manufacturer plus model.

### Create or converge

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

### Get, list, update and delete

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

## Devices

Role, type, site, location and rack accept ID, exact name/model or slug. Location and rack are resolved within the site. Position requires a rack, supports half-unit increments and uses the front face. Custom fields are a JSON object; required `dcim.device` fields are validated before creation. Identity is name plus site. With `--ensure`, only explicit fields are updated. Tables support `--wide`, `--no-truncate` and `--columns`. `move` repositions allocated devices and updates site/location when needed; `allocate` requires an unallocated device; `deallocate` clears rack, position and face but preserves site/location.

### Create or converge

```bash
netbox devices create \
  --name server-01 \
  --role Servidor \
  --device-type "PowerEdge R650" \
  --site "Site Teste"
```

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

```bash
netbox devices create \
  --name server-01 \
  --role Servidor \
  --device-type "PowerEdge R650" \
  --site "Site Teste" \
  --custom-fields '{"patrimonio":"PAT-001","monitorado":true}'
```

```bash
netbox --output json devices create \
  --name server-01 \
  --role Servidor \
  --device-type "PowerEdge R650" \
  --site "Site Teste" \
  --serial ABC123 \
  --ensure
```

### Get and list

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

### Update

```bash
netbox devices update 30 --name server-02 --status offline
netbox devices update 30 --role Servidor --device-type "PowerEdge R650"
netbox devices update 30 --custom-fields '{"patrimonio":"PAT-002"}' --dry-run
```

### Inspect

```bash
netbox device inspect server-01
netbox device inspect server-01 --site CPTEC
netbox --output json device inspect server-01
```

### Connection tree

```bash
netbox device tree server-01
netbox device tree server-01 --site CPTEC
netbox --output json device tree server-01
```

### Move

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

### Allocate

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

### Deallocate

```bash
netbox device deallocate server-01
netbox device deallocate server-01 --site CPTEC
netbox device deallocate server-01 --site CPTEC --dry-run
```

### Delete

```bash
netbox devices delete 30
netbox devices delete 30 --dry-run
netbox devices delete 30 --ignore-not-found
netbox devices delete 30 --dry-run --ignore-not-found
```

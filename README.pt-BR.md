# netbox-cli

**Português** | [English](README.md)

CLI em Python para consultar e administrar inventário físico no NetBox. Combina
menus, tabelas e árvores Rich para uso humano com JSON para scripts, CI/CD e
agentes de IA.

Gerencie regiões, sites, locais, racks, fabricantes, funções e tipos de
dispositivos, dispositivos, interfaces, portas físicas e cabos. Consulte o
inventário, inspecione dispositivos, rastreie conexões e verifique a capacidade
dos racks pelo terminal.

## Instalação

Para executar a partir do código-fonte, requer Python 3.11+:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
netbox --help
```

Para servidores Ubuntu, gere um pacote Debian independente com Docker:

```bash
./packaging/build-deb.sh
sudo apt install ./dist/netbox-cli_<versão>_amd64.deb
```

Substitua `<versão>` pela versão do pacote gerado. O pacote inclui o runtime;
o servidor de destino não precisa ter Python nem pip.

## Primeiros passos

```bash
netbox login
netbox status
netbox search server-01
netbox sites list --output table
netbox --output json devices list
```

Execute `netbox` sem argumentos para abrir o menu interativo. Para automação:

```bash
export NETBOX_URL="https://netbox.example.com"
export NETBOX_TOKEN="nbt_chave.token"
netbox --output json status
netbox manufacturers create --name Dell --ensure --dry-run
```

Prefira variáveis de ambiente para o token. O login local salva o token em
`~/.config/netbox-cli/config.yaml`; a senha nunca é armazenada. Opções globais
vêm antes do comando. `--ensure` converge o estado do recurso e `--dry-run`
permite conferir alterações. Os códigos de saída são 0 para sucesso, 1 para
falha operacional e 2 para uso incorreto da linha de comando.

## Documentação

A documentação bilíngue usa [Zensical](https://zensical.org/). Na raiz do
repositório, com o Zensical instalado:

```bash
zensical serve
```

Abra `http://127.0.0.1:8000`. Para validar e gerar o site estático:

```bash
zensical build --strict
```

O site é gerado em `site/`. A configuração está em [zensical.toml](zensical.toml).
Cada página tem um link para sua correspondente no outro idioma.

- [Documentação em português](docs/pt/index.md)
- [Documentação em inglês](docs/index.md)
- [Instalação](docs/pt/getting-started.md)
- [Configuração e saída](docs/pt/configuration.md)
- [Consultas operacionais e conexões](docs/pt/operations.md)
- [Referência de recursos](docs/pt/reference.md)
- [Automação e agentes de IA](docs/pt/automation.md)
- [Sobre](docs/pt/about.md)

## Sobre

Desenvolvido por [Luis Filippe Reis Nogueira](https://github.com/luisfilippe650)
no contexto de suas atividades de estágio na COIDS/INPE, para apoiar o
gerenciamento da infraestrutura de datacenter pelo terminal e automações
repetíveis. Utiliza a API REST do NetBox e não é um projeto oficial do NetBox
nem da NetBox Labs. Consulte [Sobre o projeto](docs/pt/about.md) para o contexto
e os créditos.

## Desenvolvimento

```bash
pip install -e '.[test]'
pytest
```

Atualize as páginas em português de `docs/pt/` e em inglês de `docs/` quando mudar o comportamento documentado. Não
versione tokens, configuração local, caches da documentação nem o site gerado.

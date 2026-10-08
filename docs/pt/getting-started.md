# Instalação e primeiros passos

[English](../getting-started.md)

## Instalação

### Pacote Debian para servidores Ubuntu

O pacote `.deb` inclui o runtime necessário e instala o comando em
`/usr/bin/netbox`. O servidor não precisa ter Python 3.11, `pip` ou ambiente
virtual.

```bash
sudo apt install ./dist/netbox-cli_0.1.1_amd64.deb
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
netbox --version
netbox status
netbox --output json status
```

Faça uma primeira consulta:

```bash
netbox search server-01
netbox --output json search server-01
```


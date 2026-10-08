# Sobre

[English](../about.md)

## Quem desenvolveu

Desenvolvido por **[Luis Filippe Reis Nogueira](https://github.com/luisfilippe650)**
no contexto de suas atividades de estágio na **Divisão de Infraestrutura de Dados
e Supercomputação (COIDS)** do **[INPE — Instituto Nacional de Pesquisas
Espaciais](https://www.gov.br/inpe/pt-br)**.

O código-fonte está em [luisfilippe650/netbox-cli](https://github.com/luisfilippe650/netbox-cli).

## Por que foi feito

O netbox-cli foi criado a partir das necessidades de gerenciamento da
infraestrutura de datacenter do INPE. Seu objetivo é facilitar a consulta e a
atualização das informações de equipamentos, racks, ambientes e conexões físicas
pelo terminal, com integração à API REST do NetBox.

Menus e visualizações Rich ajudam nas atividades de acompanhamento e manutenção
da infraestrutura. JSON, códigos de saída, `--ensure` e `--dry-run` permitem
integrar esses fluxos a scripts, pipelines e agentes de IA, com operações
repetíveis e possibilidade de conferir as alterações antes de aplicá-las.

## Créditos e integração com o NetBox

O netbox-cli utiliza a API REST do NetBox. Os créditos pela plataforma, pelas APIs
e pela documentação pertencem à **comunidade e aos mantenedores do NetBox**.

- [Código-fonte e comunidade do NetBox](https://github.com/netbox-community/netbox)
- [Documentação do NetBox](https://netboxlabs.com/docs/netbox/)

O NetBox é um projeto separado, com licença e mantenedores próprios. O netbox-cli
**não é um projeto oficial do NetBox nem da NetBox Labs**. As bibliotecas de
terceiros mantêm suas respectivas licenças e créditos. As permissões, validações
e restrições de unicidade continuam sendo aplicadas pelo servidor NetBox.

## Contribuir

Abra uma issue ou pull request no repositório com o caso de uso, os passos para
reproduzir e o comportamento esperado. Não inclua tokens nem dados sensíveis.

Para desenvolver e executar os testes:

```bash
pip install -e '.[test]'
pytest
```

Para revisar alterações na documentação, execute na raiz do repositório:

```bash
zensical serve
zensical build --strict
```

As páginas ficam em `docs/pt/` (português) e `docs/` (inglês). Atualize os dois idiomas quando mudar
um comando. A configuração está em `zensical.toml`; `site/` e `.cache/` são
artefatos locais ignorados pelo Git.

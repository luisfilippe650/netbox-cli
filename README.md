# netbox-cli

Estrutura inicial vazia para o desenvolvimento da CLI.

## Organização

- `commands`: entrada e opções dos comandos da CLI.
- `services`: regras e operações da aplicação.
- `clients`: comunicação com serviços externos.
- `presentation`: saída e apresentação no terminal.
- `utils`: funções auxiliares genéricas.
- `tests`: testes automatizados.

Analisei o código do projeto. Ele é um aplicativo web/Android que consome diretamente a API REST do NetBox. A URL configurada deve terminar em /api, então os caminhos abaixo são relativos a esse prefixo.

  ## Autenticação e permissões

   Método e rota                          Para que é usada
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   POST /api/users/tokens/provision/      Faz login com usuário e senha e cria um token v2 com permissão de escrita.
  ─────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   GET /api/authentication-check/         Confirma se o token é válido, recupera o usuário autenticado e suas permissões. Também é usada ao restaurar uma sessão salva.
  ─────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   DELETE /api/users/tokens/{tokenId}/    Revoga o token no logout ou quando o login não consegue ser concluído.
  ─────────────────────────────────────  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   OPTIONS /api/users/permissions/        Consulta os métodos permitidos. O aplicativo verifica se POST está disponível para identificar acesso administrativo/irrestrito.

  Implementação: app/src/services/client/client_api.ts:160, app/src/services/client/client_service.ts:24 e app/src/App.tsx:322.

  ## Dispositivos

   Método e rota                          Para que é usada
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   GET /api/dcim/devices/                 Lista, pagina e pesquisa equipamentos.
  ─────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────────────────────
   GET /api/dcim/devices/?q={texto}       Pesquisa dispositivo por nome/texto.
  ─────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────────────────────
   GET /api/dcim/devices/?id={id}         Busca o dispositivo lido pelo scanner/QR Code ou informado manualmente.
  ─────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────────────────────
   GET /api/dcim/devices/?rack_id={id}    Busca os equipamentos instalados em determinado rack para montar sua ocupação.
  ─────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────────────────────
   POST /api/dcim/devices/                Cadastra um equipamento com tipo, função, site, localização, rack, posição e campos personalizados.
  ─────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────────────────────
   PATCH /api/dcim/devices/{id}/          Atualiza nome, serial, patrimônio, descrição, localização, rack, posição e campos personalizados.
  ─────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────────────────────
   DELETE /api/dcim/devices/{id}/         Exclui um equipamento.

  Os filtros de busca aparecem em app/src/App.tsx:191, e as operações CRUD estão em app/src/services/devices/devices_api.ts:29.

  ## Catálogos de dispositivos

   Rota                        Métodos usados              Finalidade
  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   /api/dcim/device-types/     GET, POST, DELETE /{id}/    Listar, criar e excluir tipos/modelos de equipamentos.
  ──────────────────────────  ──────────────────────────  ───────────────────────────────────────────────────────────────────────────────
   /api/dcim/device-roles/     GET, POST, DELETE /{id}/    Gerenciar funções de dispositivos, incluindo cor e indicação de função de VM.
  ──────────────────────────  ──────────────────────────  ───────────────────────────────────────────────────────────────────────────────
   /api/dcim/manufacturers/    GET, POST, DELETE /{id}/    Gerenciar fabricantes utilizados nos tipos de equipamento.

  Não existe atualização (PATCH) desses três catálogos no código atual. As definições estão em app/src/services/devices/devices_api.ts:74.

  ## Campos personalizados

   Método e rota                                             Para que é usada
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   GET /api/extras/custom-fields/?object_type=dcim.device    Obtém as definições dos campos personalizados aplicáveis a dispositivos, incluindo tipo, validação, visibilidade e editabilidade.
  ────────────────────────────────────────────────────────  ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   GET /api/extras/custom-field-choice-sets/{id}/choices/    Carrega as opções de campos personalizados do tipo seleção.
  ────────────────────────────────────────────────────────  ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   GET /api/core/object-types/                               Descobre o endpoint REST correspondente a campos personalizados que apontam para outros objetos.
  ────────────────────────────────────────────────────────  ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   GET {rest_api_endpoint}                                   Rota dinâmica, retornada pelo NetBox, usada para listar objetos relacionados de um campo personalizado. Pode receber os filtros configurados em
                                                             related_object_filter.

  Esse carregamento dinâmico está em app/src/services/devices/devices_service.ts:24. Portanto, além das rotas fixas, o aplicativo pode chamar outros endpoints do NetBox dependendo dos campos personalizados
  cadastrados.

  ## Racks

   Rota                      Métodos usados              Finalidade
  ━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   /api/dcim/racks/          GET, POST, DELETE /{id}/    Listar racks, criar racks e excluí-los.
  ────────────────────────  ──────────────────────────  ───────────────────────────────────────────────────
   /api/dcim/rack-groups/    GET, POST, DELETE /{id}/    Gerenciar grupos de racks.
  ────────────────────────  ──────────────────────────  ───────────────────────────────────────────────────
   /api/dcim/rack-roles/     GET, POST, DELETE /{id}/    Gerenciar funções de racks, incluindo nome e cor.

  Ao abrir os detalhes de um rack, o aplicativo também chama GET /api/dcim/devices/?rack_id={id} para desenhar sua ocupação. As rotas estão centralizadas em app/src/services/racks/racks_api.ts:12.

  ## Organização

   Rota                    Métodos usados              Finalidade
  ━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   /api/dcim/sites/        GET, POST, DELETE /{id}/    Listar, cadastrar e excluir sites.
  ──────────────────────  ──────────────────────────  ────────────────────────────────────────────────
   /api/dcim/locations/    GET, POST, DELETE /{id}/    Gerenciar localizações pertencentes a um site.
  ──────────────────────  ──────────────────────────  ────────────────────────────────────────────────
   /api/dcim/regions/      GET, POST, DELETE /{id}/    Gerenciar regiões associadas aos sites.


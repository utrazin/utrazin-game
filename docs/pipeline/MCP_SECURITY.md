# Segurança de MCPs, agentes e integrações

**Nenhum MCP está habilitado neste repositório.** `.mcp.json` é ignorado pelo Git; existe apenas `.mcp.json.example`. Habilitar qualquer integração exige leitura deste guia e decisão registrada em `docs/decisions/`.

## Princípios

1. Conexões só em `localhost`; nunca expor portas na rede.
2. Projetos de teste e **backup** antes de qualquer automação em arquivo real.
3. Permissões mínimas no Claude Code (`.claude/settings.json` nega comandos destrutivos).
4. Credenciais nunca no Git (`.env`, `.mcp.json` ignorados).
5. Telemetria desligada quando a ferramenta permitir.
6. Nada experimental ligado por padrão; nada pago.

## Avaliação das integrações

> Informações a **reconfirmar** na hora da instalação (licença, versão e flags mudam). Data da pesquisa: 2026-11-11.

### Blender MCP (ahujasid/blender-mcp)

| Campo | Valor |
|---|---|
| URL | https://github.com/ahujasid/blender-mcp |
| Licença | MIT (conferir `LICENSE` do repo) |
| Compatibilidade | Blender 3.x+ via addon `addon.py`; servidor Python via `uvx blender-mcp` |
| Permissões | **Executa Python arbitrário dentro do Blender** (acesso a disco e rede do usuário) |
| Riscos | Alto: código gerado pode apagar/sobrescrever `.blend`, acessar arquivos fora do projeto, baixar assets de serviços externos (Poly Haven, Sketchfab, Hyper3D) com licenças variadas |
| Dependências | `uv`, Python 3.10+, addon instalado no Blender |
| Instalação | Ver README oficial; usar `.mcp.json.example` como base; `DISABLE_TELEMETRY=true` |
| Teste mínimo | Cena vazia nova, pedir "crie um cubo de 1 m na origem", conferir resultado e salvar em pasta temporária |
| Alternativa sem MCP | `blender -b arquivo.blend --python tools/blender/<script>.py -- ...` (determinístico, revisável) |

Regras se habilitado: só em cópias de trabalho (`blender/scenes/.../_wip`), desligar integrações de download de assets externos, revisar o código antes de executar, commit/backup antes de cada sessão.

### BlenderTools / Send to Unreal (Epic)

| Campo | Valor |
|---|---|
| URL | https://github.com/EpicGamesExt/BlenderTools (repo original EpicGames/BlenderTools; hoje mantido por novos mantenedores, ver fórum da Epic) |
| Licença | Conferir no repo (acesso pode exigir conta GitHub vinculada à Epic) |
| Compatibilidade | Verificar suporte a Blender 5.2 e UE 5.8 nas releases antes de instalar |
| Permissões | Conecta ao Editor Unreal via Remote Execution (Python) na rede local |
| Riscos | Médio: Remote Execution abre canal multicast local para executar Python no Editor |
| Alternativa | Pipeline por scripts deste repo (padrão) |

### Automação Python da Unreal (nativa)

| Campo | Valor |
|---|---|
| Plugin | Python Editor Script Plugin + Editor Scripting Utilities (nativos) |
| Licença | Unreal EULA |
| Riscos | Baixo/médio: scripts locais revisados no Git |
| Uso | `tools/unreal/*.py` via `UnrealEditor-Cmd -run=pythonscript` |

### MCP oficial da Unreal (UE 5.8, experimental)

| Campo | Valor |
|---|---|
| Situação | A 5.8 introduziu suporte **experimental** a servidor MCP no Editor (ver release notes da 5.8) |
| Política | **Não habilitar no MVP.** Reavaliar quando sair de experimental. |
| Riscos | Agente com controle do Editor pode alterar/salvar `.uasset` e `.umap` binários (difícil revisar em diff) |
| Teste mínimo (futuro) | Projeto de teste separado, somente leitura de informações do nível |

### MCPs Unreal de terceiros

Há vários (repositórios comunitários). **Não usar** sem: repositório verificável, licença clara, código revisado e decisão registrada.

## Agentes do Claude Code

- Cada subagente tem `tools` restritas no frontmatter.
- Hooks bloqueiam comandos destrutivos (`.claude/hooks/guard_bash.py`).
- Agentes nunca aprovam arte final, licença comercial ou QA não executado.

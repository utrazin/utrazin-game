# Origem de conteúdo de terceiros (pipeline)

Conteúdo incorporado em `.claude/skills/` e ferramentas externas avaliadas. Texto das licenças em `docs/licenses/third-party/`. Pesquisa e cópia em 2026-11-16.

| Origem | Licença | O que entrou | Alterações feitas |
|---|---|---|---|
| gamedev-skills/awesome-gamedev-agent-skills | Apache-2.0 (+ NOTICE) | 18 skills de engine e disciplina (lista em `docs/pipeline/vendored_skills.json`) | Cópia integral das skills; travessões trocados por hífen; sem outras mudanças de conteúdo |
| arjun988/blender-skills | MIT | 25 skills `blender-*` e a pasta compartilhada `blender-references` | Nomes prefixados com `blender-`; referências cruzadas e `related-skills` ajustadas; links `../references/` trocados por `../blender-references/`; aviso de adaptação no `blender-director` e no guia de MCP; travessões trocados |
| donchitos/claude-code-game-studios | MIT | Nenhum arquivo copiado. Conceitos adaptados e reescritos: hierarquia de agentes, orquestração por equipe, portão de qualidade, testes de skills | Implementação própria (`studio-producer`, `team-orchestrate`, `visual-qa-gate`, `validate-pipeline`) |
| ace-step/ace-step-1.5 | MIT (código); pesos MIT nos model cards consultados | Nada baixado. Cliente próprio da API REST | `tools/audio/acestep_client.py` |
| NVIDIA/Audio2Face-3D | SDK e plugins MIT; modelos "NVIDIA Open Model"; Audio2Emotion e dados de exemplo com licença própria | Nada baixado | Documentação e skill `facial-animation-lipsync` |
| ahujasid/blender-mcp | MIT | Nada instalado | Avaliação em `docs/pipeline/MCP_SECURITY.md` |

Observações:
- Código MIT não implica pesos de modelo ou datasets com a mesma licença. Registre a licença do modelo exato antes de usar uma saída no jogo (`ASSET_LICENSES.md`).
- Nenhum script de terceiros foi executado. As skills copiadas não contêm scripts executáveis (verificado por busca de arquivos que não sejam Markdown e de comandos de rede ou execução).
- Manutenção: a página do awesome-gamedev-agent-skills declara 300 commits e versões de engine verificadas em 2026-11-11. Para os demais repositórios só foram lidas as páginas do GitHub; atividade e vulnerabilidades não foram auditadas.

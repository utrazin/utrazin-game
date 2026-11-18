# Como adicionar skills e agentes

## Nova skill

1. Crie `.claude/skills/<nome>/SKILL.md` (minúsculas e hifens; o nome é igual ao da pasta).
2. Frontmatter só com `name` e `description` (até 1024 caracteres; diga quando usar).
3. Seções obrigatórias: Pré-requisitos, Passos, Ferramentas necessárias, Diretórios afetados, Verificações, Erros comuns, Critério de sucesso. Corpo com até 500 linhas; detalhes longos vão para `references/`.
4. Uma skill resolve um problema; evite skill gigante e evite fragmentar demais.
5. Registre na tabela `.claude/skills/gamedev-router/references/routing-table.md` e, se tiver agente líder, na tabela do `gamedev-router/SKILL.md`.
6. `python tools/pipeline/validate_pipeline.py` e `python tools/pipeline/gen_catalog.py`.

## Skill de terceiros

1. Verifique licença do repositório e de modelos ou dados; leia os scripts antes de copiar (sem executar).
2. Prefixe o nome se puder colidir (como `blender-`), ajuste referências cruzadas e remova travessões.
3. Liste em `docs/pipeline/vendored_skills.json` e `docs/licenses/THIRD_PARTY_SOURCES.md`; copie a licença para `docs/licenses/third-party/`.
4. Registre a decisão em `INTEGRATION_MATRIX.md`.

## Novo agente

1. Crie `.claude/agents/<nome>.md` com frontmatter `name`, `description`, `tools` (somente ferramentas válidas).
2. Seções: Missão, Responsabilidades, Arquivos e diretórios sob sua responsabilidade (sem repetir diretório de outro agente), Entradas, Artefatos, Critérios, Testes, Skills que consulta, Proibições, Exige aprovação humana, Formato de retorno.
3. Registre no roteador e rode a validação.

## Ferramenta opcional

Nunca vira requisito: documente dependências em `EXTERNAL_TOOLS.md`, forneça caminho alternativo e teste que a pipeline passa sem ela.

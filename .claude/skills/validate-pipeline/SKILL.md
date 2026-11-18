---
name: validate-pipeline
description: Valida a própria pipeline (skills, agentes, roteamento, links, licenças de terceiros, preferências do projeto). Use depois de adicionar ou editar skills e agentes.
---

# /validate-pipeline

Teste estrutural de skills e agentes, inspirado nos testes de estúdio do Claude Code Game Studios.

## Pré-requisitos
- Python 3.10 ou superior

## Passos
1. `python tools/pipeline/validate_pipeline.py` na raiz do repositório.
2. Corrija erros (bloqueiam) e avalie avisos (não bloqueiam).
3. `python tools/pipeline/gen_catalog.py` para regenerar `docs/pipeline/AGENT_CATALOG.md` e `SKILL_CATALOG.md`.
4. `python -m pytest tests/python/test_pipeline_integrity.py -q` (quando pytest estiver instalado).
5. Para nova skill ou agente, siga `docs/pipeline/EXTENDING.md`.

## Ferramentas necessárias
- Python, `tools/pipeline/validate_pipeline.py`

## Diretórios afetados
- `docs/pipeline/` (catálogos gerados)

## Verificações
- Zero erros; nomes únicos; todo skill e agente presente em `gamedev-router/references/routing-table.md`
- Sem travessão nos arquivos da pipeline (preferência do projeto)

## Erros comuns
- Criar skill nova e esquecer de registrá-la no roteador
- Dois agentes com o mesmo dono de arquivo

## Critério de sucesso
`validate_pipeline.py` termina com código 0 e os catálogos estão atualizados.

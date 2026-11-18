---
name: team-orchestrate
description: Use quando a tarefa exige 3+ especialidades (ex.: nova zona jogável, cena de abertura, interior com props e áudio). Planeja delegação, donos de arquivos, dependências, revisão e integração.
---

# /team-orchestrate

Coordena uma equipe de agentes em uma entrega multidisciplinar sem conflito de arquivos.

## Pré-requisitos
- Objetivo e critério de aceite escritos pelo usuário ou derivados de `GDD_jogo_resgate.md`
- Resultado de `/gamedev-router` (líder e skills)

## Passos
1. **Quebre** em entregas pequenas e verificáveis (cada uma com saída em arquivo ou relatório).
2. **Atribua um dono por arquivo.** Tabela obrigatória: `entrega | agente | arquivos permitidos | entradas | saída | depende de`. Dois agentes nunca no mesmo `.uasset`, `.umap`, `.blend` ou script.
3. **Ordene por dependência.** Padrão: design (`level-designer`/`art-director`) > assets (`blender-specialist`) > integração (`world-builder`/`gameplay-engineer`) > polimento (`technical-artist`, `sound-designer`, `cinematics-director`) > QA (`qa-engineer`).
4. **Delegue em paralelo** só o que não compartilha arquivos. Cada delegação leva: escopo fechado, arquivos permitidos, critérios de aceite, formato de retorno.
5. **Revise cada retorno** contra o critério de aceite. Retorno sem evidência (print, relatório JSON, saída de teste) volta para o agente.
6. **Conflitos**: decide o coordenador; mudança de contrato (C++, nomes, escala) passa por `technical-architect`.
7. **Integre** e rode `/visual-qa-gate` e `python tools/pipeline/validate_pipeline.py`.
8. **Registre** pendências em `docs/decisions/OPEN_DECISIONS.md` e suposições em `ASSUMPTIONS.md`.

## Ferramentas necessárias
- Agentes de `.claude/agents/`; TodoWrite para o plano

## Diretórios afetados
- `docs/plan/` (plano da entrega) e os diretórios de cada agente

## Verificações
- Nenhum arquivo aparece como "permitido" para dois agentes
- Cada entrega tem evidência anexada
- O coordenador não declarou "compilou", "rodou" ou "validado" sem prova

## Erros comuns
- Delegar sem critério de aceite
- Paralelizar passos que dependem um do outro (modelar depois de importar)
- Deixar o agente decidir escopo

## Critério de sucesso
Plano em `docs/plan/` com tabela de donos preenchida, todas as entregas aceitas com evidência e QA final registrado.

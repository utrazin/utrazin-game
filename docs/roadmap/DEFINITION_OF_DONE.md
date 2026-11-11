# Definition of Done

Um item só está **pronto** quando todos os critérios aplicáveis são verdadeiros **e têm evidência**.

## Código C++

- Compila em `Development Editor Win64` sem warnings novos (log anexado ao PR)
- Segue `.claude/rules/cpp.md`
- Sem Tick desnecessário; delegates para eventos
- Automation Test cobrindo a lógica pura (quando existir)
- Nenhum caminho absoluto; nenhum `TODO` sem issue

## Blueprint / conteúdo Unreal

- Nome segue `.claude/rules/unreal-content.md` (`validate_naming.py` verde)
- Sem referências quebradas (Data Validation / `validate_content.py`)
- Não guarda estado de fase em widgets
- Abre e roda em PIE sem erros no Output Log

## Asset de arte

- Entrada no manifesto com todos os campos obrigatórios
- `validate_scene.py` / `validate_rig.py` sem erros
- Escala, colisão, LOD e materiais verificados após import
- Licença auditada (`check_licenses.py` sem bloqueios)
- **Aprovação humana registrada** (`reviewer`, `approved_at`)

## Script Python

- `--help` documentado
- Funções puras separadas de chamadas `bpy` / `unreal`
- Testes com fixtures pequenas em `tests/python/`
- Logs auditáveis e código de saída != 0 em falha

## Funcionalidade de gameplay

- Checklist manual relevante executado e anexado
- Impacto de performance medido ou declarado
- Documentação do sistema atualizada em `docs/gameplay/`

## Marco

- Todos os critérios de aceite do `ROADMAP.md` marcados com evidência
- Relatório em `docs/qa/` com data, commit e resultados

---
name: profile-performance
description: Mede performance com método fixo e compara com o baseline e os budgets.
---

# /profile-performance

Mede performance com método fixo e compara com o baseline e os budgets.

## Pré-requisitos
- Build Development standalone
- Rota de teste definida

## Passos
1. Siga o método em `tests/performance/BASELINE.md`
2. Capture `stat unit`, `stat gpu`, Insights
3. Registre em `docs/qa/perf/<data>.md` com hardware e commit
4. Compare com `docs/architecture/RENDERING.md` e proponha ações

## Ferramentas necessárias
- Unreal Insights

## Diretórios afetados
- docs/qa/perf/
- tests/performance/

## Verificações
- Hardware e settings registrados

## Erros comuns
- Medir no Editor e chamar de resultado final

## Critério de sucesso / resultado esperado
Relatório com números reais e recomendações.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.

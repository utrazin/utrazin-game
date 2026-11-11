---
name: test-gameplay
description: Executa testes automatizados e o QA manual de gameplay e registra resultados reais.
---

# /test-gameplay

Executa testes automatizados e o QA manual de gameplay e registra resultados reais.

## Pré-requisitos
- Build disponível (PIE ou standalone)

## Passos
1. `python -m pytest tests/python -q`
2. Automation: ver tests/unreal/README.md (`Automation RunTests JR.`)
3. Preencha `tests/gameplay/checklists/MANUAL_QA.md` (cópia datada em docs/qa/reports/)
4. Abra issues para falhas

## Ferramentas necessárias
- pytest
- UnrealEditor-Cmd

## Diretórios afetados
- docs/qa/reports/

## Verificações
- Cada passo com ok/falha/não executado

## Erros comuns
- Presumir resultado

## Critério de sucesso / resultado esperado
Relatório de QA com evidências.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.

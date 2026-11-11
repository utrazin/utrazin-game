---
name: audit-licenses
description: Audita licenças de todos os assets do manifesto e gera relatório e créditos.
---

# /audit-licenses

Audita licenças de todos os assets do manifesto e gera relatório e créditos.

## Pré-requisitos
- Manifesto válido

## Passos
1. `python tools/pipeline/check_licenses.py --report docs/licenses/audit-<data>.md`
2. Para cada bloqueio: corrigir ou remover asset
3. `--credits docs/licenses/CREDITS.md`
4. Pedir aprovação humana para `commercial_use_status: allowed`

## Ferramentas necessárias
- tools/pipeline/check_licenses.py

## Diretórios afetados
- docs/licenses/
- assets/licenses/

## Verificações
- Saída sem bloqueios

## Erros comuns
- Licença sem URL
- NC escondido em descrição

## Critério de sucesso / resultado esperado
Relatório limpo e créditos atualizados.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.

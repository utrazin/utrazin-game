---
name: material-lighting-audit
description: Use para auditar materiais e iluminação do jogo: brilho exagerado, emissivos fortes, luzes dentro de objetos, malhas sem textura, exposição e avisos de céu. Define limites e checagens.
---

# /material-lighting-audit

Evita cenas estouradas e objetos brancos sem textura.

## Pré-requisitos
- Lista de materiais do projeto (`reports/*.json`) e acesso aos scripts `tools/unreal/`

## Passos
1. **Inventário**: liste todo material usado em cada malha colocada. Marque os que usam material de reserva (padrão da engine, branco ou cinza) ou `M_L01_Glow`.
2. **Emissivo**: valor emissivo >= 4 só em fontes de luz declaradas (cristal, tela). Em props comuns o emissivo é 0. Corrija multiplicadores globais (ex.: `x6`) para parâmetros por instância.
3. **Albedo**: base color de superfícies comuns entre 0,05 e 0,85 (sRGB 15 a 220). Branco puro é erro.
4. **Luzes**: nenhuma luz pontual dentro de malha ou no chão sem motivo; raio de atenuação curto em interiores; sombras só onde importam; contagem por zona dentro do orçamento (`performance-optimization`).
5. **Exposição**: auto exposure com mínimo e máximo definidos, ou exposição fixa em interiores (Post Process Volume).
6. **Céu**: só o domo do céu usa "Is Sky". Estrelas, planetas e aurora não podem ter essa flag, ou o aviso "SKYDOME MESH" volta.
7. **Nave e destaques**: brilho coerente com o ambiente; teste em dia e noite do jogo.
8. **Relatório**: tabela material, malhas que usam, problema, correção. Reexecute depois da correção e compare.
9. Rode `/visual-qa-gate`.

## Ferramentas necessárias
- Unreal (Material Editor, Output Log), scripts de `tools/unreal/` que listem materiais

## Diretórios afetados
- `unreal/JogoResgate/Content/Materials/`, `tools/unreal/`, `reports/`

## Verificações
- Nenhum material de reserva em malhas colocadas
- Nenhum emissivo alto fora das fontes declaradas
- Aviso de skydome ausente do log

## Erros comuns
- Corrigir a luz e esquecer o material emissivo
- Usar o mesmo material "Glow" em props e em fontes de luz

## Critério de sucesso
Cena sem estouro, sem material de reserva e sem aviso de céu, com relatório antes/depois.

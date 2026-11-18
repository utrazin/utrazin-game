# QA 2026-11-17: registro anti-sobreposição na L01 (A-062, item 6 do handoff)

Portão: visual-qa-gate (etapa estrutural). Estado: **validado estruturalmente, pendente de validação na Unreal**.

## Evidência
- Antes x depois (vista de cima, 60 x 60 m): `2026-11-17_A062_antes_depois_sobreposicao.png`.
- Sobreposições entre sólidos (mesmas regras): 492 antes, 0 depois (`reports/placement_L01.json`, `placement_registry.py check`).
- Plano dos modelos do usuário: 0 sobreposições; 1 enfeite recusado (PRP_Gerador do acampamento caía em cima do Pickup_Vida_Acampamento).
- Testes: test_placement_registry.py e test_l01_user_dressing.py passam (14), menos a falha antiga do catálogo (57 modelos, o teste espera 56).
- Dados regerados no PC: l01_scatter_v3.bin/.json com 1.139.215 instâncias (antes 1.153.932). Cópia antiga em assets/work/levels/L01/_backup_antes_A062.

## Pendente (usuário)
1. Na Unreal: `py "E:/game/utrazin-game/tools/unreal/scatter_l01.py"` e depois Build > Build Paths.
2. Print do mesmo lugar do print_06 (árvore x cristal).
3. Quando rodar o build_l01.py de novo: conferir o bloco "placement" em reports/build_l01.json.

## Não resolvido aqui
- Malhas com forma comprida usam círculo (aproximação).
- Pedras do blockout dentro do círculo da nave caída (rever na cena de abertura).

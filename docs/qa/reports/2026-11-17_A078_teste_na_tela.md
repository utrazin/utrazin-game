# QA 2026-11-17: A-078 (teste no editor do usuário por controle de tela)

Estado: **testado no Play do editor** (zumbi, baú, entrar e sair do carro) e consertado; o E do carro entrou por
Live Coding (compilação completa ainda pendente na próxima vez que o editor for fechado).

| Item | Prova | Resultado |
|---|---|---|
| Zumbi invisível | reports/diag_zombie_bones_pie.json antes: todos os ossos a menos de 2 cm uns dos outros, a ~1 m do chão; diag_zombie_refpose.json: Hips com escala 100 e filhos em metros; diag_anim_bones.json: Spine/pernas em cm | fix_zombie_anim_scale.py (98 animações); no Play o zumbi aparece em pé ao lado do herói |
| Baú sem "E" | build_interiors_l01.json: 42 malhas "sem colisão UCX"; SM_PRP_Bau_Base sem forma simples | fix_collisions_a078.py; no Play aparece "E Abrir o baú" e o baú da chave abre ("Você achou: CHAVE DO BUGGY!") |
| Sair do carro | não havia comando (só checkpoint/explosão) | E / X do controle no AJRVehiclePawn; no Play: E entra (com a chave), E desce, herói anda |
| Sofá no acampamento e enfeites no ar | layout: peças do acampamento na altura fixa 1191,9 cm | sofá e pneus removidos; 47 enfeites assentados (o maior estava 1,5 m no ar) |
| Portas | MapCheck: "JRDoor_x StaticMesh nula" = só a folha B vazia nas portas simples (aviso inofensivo); erro de script rerun_construction_scripts | chamada removida do build_interiors_l01.py |

Ainda não visto: portas abrindo em jogo, interiores por dentro, mirantes, abertura completa, sobrevivente.

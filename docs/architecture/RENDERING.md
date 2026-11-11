# Renderização e otimização

Política: **ligar recursos caros só com medição** (prompt mestre, Etapa 8). Medir com `stat unit`, `stat gpu`, Unreal Insights, em build `Development` standalone, na GPU de referência (A-023).

| Recurso | Padrão inicial | Quando reconsiderar |
|---|---|---|
| World Partition | **Desligado**; mapas com Level Streaming manual (sublevels por trecho) | Se o mapa passar de ~4 km² ou streaming manual ficar inviável |
| Nanite | Desligado em skeletal/veículo; avaliar em rochas e props estáticos densos | Teste A/B de frame time no greybox de arte (M3) |
| Lumen | Desligado no greybox (luz estática/baked + SkyLight) | Comparar Lumen, "Lumen Lite" (novo na 5.8, verificar) e baked em M3 |
| Virtual Shadow Maps | Avaliar junto com Nanite | |
| PCG | Não usar no MVP | Se o preenchimento manual de vegetação virar gargalo |
| HLOD | Ligado para props distantes ao usar streaming | |
| Instanced Static Meshes / Foliage | **Sempre** para vegetação e props repetidos | |
| LOD | Obrigatório em personagens, veículo, props médios | |
| Culling | Frustum (padrão) + Precomputed Visibility ou distance culling volumes nos trechos fechados | |

## Orçamento provisório (60 FPS = 16,6 ms)

| Item | Budget |
|---|---|
| Game thread | 8 ms |
| Render thread | 10 ms |
| GPU | 14 ms |
| IA completa | 12 agentes (A-029) |
| Draw calls visíveis | < 2.500 |
| Memória de textura | < 3 GB |

Valores serão revistos após o primeiro profiling (M1).

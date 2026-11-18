# Fases e configuração por Data Asset

Cada fase tem um `UJRLevelDefinition` (`DA_Level_L01_Zombies` etc.) com:

| Campo | Exemplo L01 |
|---|---|
| LevelId | `L01` |
| DisplayName / Theme | "Fase 1" / Zumbis |
| Map | `/Game/Levels/L01_Zombies/L01_Zombies` (soft ref) |
| AvailableCharacters | CHR-001, CHR-002 |
| VehicleProfile | `DA_Vehicle_SUV` |
| EnemyArchetypes | ENM-001, ENM-002, ENM-003 |
| HordeWaves | 3 ondas (ver ENEMY_AI) |
| Checkpoints | `Start`, `Transition` (principal) |
| RescueTargetId | a definir (OD-008) |
| Ambience / Weather / Lighting | `AMB_L01`, nublado, fim de tarde (provisório) |
| PerformanceProfile | `High` |

Adicionar fase = novo Data Asset + mapa (skill `/add-level`), **sem código novo**.

## Greybox L01 (M1)

Orçamento de tempo (A-018: **no máximo 10 min**, ~50% carro / ~50% a pé):

| Trecho | Tempo alvo | Tamanho |
|---|---|---|
| Carro (velocidade média ~30 km/h em terreno ruim) | 4 a 5 min | ~1,5 km |
| A pé até a arena (3 encontros) | 2 a 3 min | ~300 m |
| Horda final | 1,5 a 2 min | arena ~40 m |
| Resgate + abraço | < 30 s | |

```
[Início/carro] --estrada sinuosa com morros e buracos (~1,5 km)--> [Checkpoint de transição]
      --trilha a pé com ruínas e obstáculos (~300 m)--> [Arena da horda] --> [Cela / resgate]
```

- Landscape 1 x 1 km (suficiente para o percurso sinuoso), resolução 1009 x 1009.
- Trecho de carro: 3 subidas, 2 descidas fortes, 6 buracos, 4 pontos de emboscada de arqueiros.
- Transição: área plana com socket de saída do carro e checkpoint.
- Trecho a pé: 3 encontros escalonados (corpo a corpo, misto, misto + atirador).
- Arena: circular ~40 m, 4 pontos de spawn fora da visão, coberturas.
- Resgate: cela com grade interativa.

## L01 v3 "Vale aberto" (2026-11-15, Etapa 5)

Roteiro e tabela de zonas: [L01_STORYBOARD.md](L01_STORYBOARD.md). Substitui a v2 (corredor fechado).

| Item | Valor gerado |
|---|---|
| Mapa | o mesmo `/Game/Levels/L01_ZombieValley/L01_ZombieValley`; terreno 2 x 2 km em 64 pedaços (grade 4 m) + estrada em 15 trechos (a ponte faz parte da estrada) |
| Zonas | 8, alternando a pé / carro: 0 Acampamento, 1 Estrada do vale, 2 Posto, 3 Floresta, 4 Ponte/colmeia, 5 Fuga da horda, 6 Vila, 7 Saída |
| Estrada principal | ~3,5 km, 12 m de largura, raio mínimo 65 m, rampa máxima 4,6% |
| Rotas alternativas (terra) | Z1 Dunas (com salto) e Z1 Pedras, Z3 Trilha da árvore-mãe (desvio da barricada), Z5 Ribeirinha (com salto), Z7 Serra |
| Limites | morros suaves a partir de ~50 m das rotas, mesas/penhascos longe, serra com penhasco na borda, rio tóxico na ravina (só a ponte cruza), lago tóxico; **4 paredes invisíveis só na borda** (985 m) |
| Portões | árvore caída na ponte (AJRBlockingGate, explosivos), barreiras na entrada da vila; checkpoints de transição no posto, na ponte e na vila |
| Carro | buggy estacionado no acampamento; o jogador começa **a pé** e precisa da chave (baú); E perto do carro para entrar |
| Checkpoints | Start (a pé), Z1_Road, Z2_Posto, Z3_Forest, Z4_Bridge, Z5_Escape, Z6_Village (armas + CarKey; nas zonas a pé o carro renasce estacionado) |
| Diretor de IA | 1 AJRAIDirector + 8 AJRDirectorZone (acampamento e saída seguros; posto, ponte, vila mais densos) |
| Vegetação | **não** espalhada aqui: `veg_hints`/`veg_rules` no layout + `l01_veg_density_v3.png` (R floresta, G esparso, B deserto) para o agente Densidade |

Gerar de novo (Blender 5.3 e Python com Pillow):
```
blender -b --python tools/blender/gen_l01_v3.py -- assets/work/levels/L01
python tools/blender/plot_l01_v3.py assets/work/levels/L01
```
Montar no Editor (depois de compilar o C++): `py tools/unreal/build_l01.py` (usa a v3 se `l01_layout_v3.json`
existir; `build_l01.py v2` força a antiga) e `py tools/unreal/setup_minimap.py` (minimapa v3).
Modelos Quaternius entram por `tools/unreal/quaternius_lib.py` em `/Game/Environment/Quaternius/<Pack>/`.

## L01 v2 "Vale Alienígena" (2026-11-15)

Roteiro completo: [L01_STORYBOARD.md](L01_STORYBOARD.md). Mesmo traçado da v1 (estrada 1.221 m, trilha 865 m), agora com:

| Item | Valor gerado |
|---|---|
| Biomas | areia vermelha (início), cânion de cristais, floresta alienígena (grama azul + musgo roxo), terra nas trilhas; rocha nas encostas (material) |
| Corredor | morros sobem fora de ±45 m (carro) e ±25 m (a pé); 311 paredes invisíveis |
| Saltos | buraco de 10 m (≈ 451 m) e ravina de 13 m (≈ 1.013 m) com rampa + aterrissagem; na ravina 2 há uma ponte estreita ao lado; cair = checkpoint |
| Eventos da estrada | lombadas no cânion, barris explosivos, manada de 10 zumbis, contêineres/ônibus em zigue-zague, 2 tapetes de pregos, costela gigante por cima, guard-rails nas curvas |
| A pé | graveto na praça, baú com pistola na Vila 1, parkour (7 pilares) sobre lago tóxico, Fúria escondida na Vila 2, nave caída + zumbi elite (escopeta) na Vila 3, arco de pedra, arena |
| Checkpoints | Start, Road1, Road2, Transition, Parkour (graveto+pistola), Arena (+escopeta) |
| Itens | nitro, reparo, munição, vida, Fúria (≈ 30 no mapa) + drops dos zumbis |
| Vistas | fazenda + turbina no morro, nave grande, espiras de cristal |
| Cenário | ~3.400 objetos (árvores/cogumelos/cristais alienígenas por bioma) |

Gerar de novo: `tools/blender/gen_l01.py` (terreno + layout), `make_l01_props*.py`, `make_minimap.py`;
montar no Editor: `py tools/unreal/run_all_wave1.py` (ou `setup_wave1.py` e depois `build_l01.py`).
Prévia de cima (com paredes em rosa): `assets/work/levels/L01/l01_map.png`.

## L01 v1: L01_ZombieValley (2026-11-15, substituída pela v2)

Decisão do usuário: mapa **2 x 2 km**, **~1,2 km de carro** e **~800 m a pé** (substitui o greybox 1 x 1 km acima).

| Item | Valor gerado |
|---|---|
| Mapa | `/Game/Levels/L01_ZombieValley/L01_ZombieValley` (sem World Partition; 64 pedaços de terreno de 250 m + estrada em 7 trechos) |
| Estrada | 1.221 m, 10 m de largura, subidas/descidas suaves (≤ 11%), 6 buracos |
| Trilha a pé | 865 m, 3 vilas em ruínas (encontros escalonados), termina na arena |
| Arena | raio 30 m, muro baixo com entrada do jogador e 4 aberturas de spawn |
| Resgate | cela (SM_Cage) no fundo da arena |
| Inimigos | 4 arqueiros em torres na estrada, 12 zumbis na estrada, 11 nos 3 encontros, horda de 4 ondas |
| Cenário | ~1.900 objetos (árvores, pedras, ruínas, destroços) com distância de corte |
| Borda | morros altos em volta (o jogador não sai do mapa) |

Gerar de novo: `tools/blender/gen_l01.py` (terreno + layout) e `tools/blender/make_l01_props.py` (objetos) no Blender;
montar no Editor: `py tools/unreal/build_l01.py`. Prévia de cima: `assets/work/levels/L01/l01_map.png`.

# Fase 1: "Vale Alienígena" v3, vale aberto (storyboard)

Retrabalho da Etapa 5 (2026-11-15). O usuário testou a v2 e não gostou: estrada linear entre paredões de
cristal, objetos soltos ao acaso, árvores meio enterradas, curvas feias, metade carro / metade a pé.
A v3 é um **vale aberto de 2 x 2 km** com 8 zonas alternando carro e a pé (12 a 15 min, nenhum trecho
com mais de ~2,5 min), 2 ou 3 caminhos entre as zonas de carro e limites naturais (morros, penhascos,
rio em ravina, mata densa). Paredes invisíveis só na borda do mapa. Ver A-046 e A-047 em
[ASSUMPTIONS](../decisions/ASSUMPTIONS.md).

Prévia de cima (zonas, rotas, POIs, checkpoints): `assets/work/levels/L01/l01_map_v3.png`.

## Premissa
A nave de resgate do herói (Enzo ou Victoria) caiu no fundo de um vale alienígena tomado por zumbis
infectados. Um buggy ficou no acampamento da queda. É preciso cruzar o vale, achar a sobrevivente na
vila perto do disco voador enterrado e sair pelo portão norte.

## Zonas (v3)

| # | Zona | Modo | Tempo | O que acontece | Marco (landmark) | Itens / armas |
|---|---|---|---|---|---|---|
| 0 | Acampamento da queda | a pé | 1,5 a 2 min | tutorial: pegar o graveto, 4 zumbis lentos (corpo a corpo), achar a **chave do buggy** num baú de barraca, **E no buggy** para entrar | nave de resgate caída pegando fogo | graveto, vida, chave (baú) |
| 1 | Estrada do vale (areia vermelha) | carro | 1 a 1,5 min | terreno aberto, **3 caminhos** (estrada, Dunas com salto, Pedras), grupos para atropelar, 3 carros abandonados com reparo/nitro; tanque na reserva ("vá ao posto") | arco de pedra gigante sobre a estrada | nitro, reparo |
| 2 | Posto de gasolina | a pé | 2 a 2,5 min | o carro para (tanque seco). **Encher o galão** na bomba (E) chama uma horda; **pistola** no baú da sala dos fundos; medkit | placa alta do posto + torre de rádio | pistola, medkit, munição, galão (Fuel) |
| 3 | Floresta alienígena | carro | 1 a 1,5 min | mais densa e brilhante; zumbis sobem no carro; **barricada de corpos** na estrada (romper a 50+ km/h) ou desvio pela trilha da árvore-mãe | árvore-mãe gigante brilhando | nitro, reparo |
| 4 | Árvore caída na ponte | a pé | 2 a 2,5 min | árvore bloqueia a ponte; **explosivos** na colmeia da ilha, com **parkour** (6 pilares) sobre o lago tóxico; **escopeta** (rara) no mesmo baú; armar o explosivo na árvore (E, 4 s) chama a horda | colmeia alienígena na ilha | escopeta, explosivos, munição, vida |
| 5 | Fuga da horda | carro | 1 a 1,5 min | cruzar a ponte aberta com a horda atrás; 2 caminhos (estrada e Ribeirinha com salto) | ponte em chamas | nitro, reparo |
| 6 | Vila da sobrevivente | a pé | 2 a 2,5 min | o carro fica no portão trancado; limpar a vila, **defender 60 a 90 s** (4 ondas), libertar a sobrevivente na cela perto do disco | disco voador enterrado | munição, vida, Fúria, baú |
| 7 | Saída | carro | ~1 min | voltar ao buggy e sair pelo portão norte (passagem na serra); 2 caminhos | portão norte (arco em ruínas) | nitro |

Total: ~12 a 15 min. Estrada principal 3,5 km (raio mínimo das curvas 65 m, rampa máxima 4,6%);
rotas alternativas de 0,5 a 0,74 km cada.

## Regras de desenho (v3)
- **Aberto, mas legível**: fundo do vale largo; os morros começam a ~50 m das rotas e sobem devagar
  (dá para subir de buggy no começo), ficando íngremes longe. Penhascos e mesas aparecem longe das rotas.
- **Limites naturais**: serra com penhasco na borda, o rio tóxico na ravina (só a ponte cruza), o lago
  tóxico, cinturão de mata densa (vegetação, agente Densidade). Paredes invisíveis só na borda (985 m).
- **Saltos opcionais**: só nas rotas alternativas (Dunas e Ribeirinha), numa reta (60 m antes, 40 m
  depois), rampa SM_Ramp + aterrissagem SM_RampLanding, vala rasa de 1,9 m com saída pelos lados.
  Nunca há buraco fatal na estrada principal.
- **Portões forçam sair do carro**: checkpoints de transição no posto (tanque seco), antes da ponte
  (árvore caída) e no portão da vila. Para voltar: andar até o carro e apertar **E**.
- **Diretor de IA** (AJRAIDirector) cria os zumbis por ritmo; zonas do diretor: acampamento e saída
  seguros, posto/ponte/vila mais densos, colmeia mais calma.
- **Checkpoints** devolvem armas e a chave do buggy; nas zonas a pé o buggy renasce estacionado no portão.

## Itens-chave
`CarKey` (baú da barraca, zona 0), `Fuel` (bomba do posto, zona 2; o carro só anda de novo com ele),
`Explosive` (baú da colmeia, zona 4; gasto na árvore da ponte). Console de teste: `JRItens`.

## Histórico: v2 (corredor fechado, substituída)
Roteiro linear de 14 passos (deserto, cânion de cristais, 2 saltos com buraco, floresta, desembarque,
graveto, 3 vilas, parkour, nave, arena da horda, resgate). Gerador: `tools/blender/gen_l01.py`.

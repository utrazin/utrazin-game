# Interiores da Fase 1 (A-070)

Toda construção com porta aberta tem dentro algo que justifique entrar (skill `enterable-interior`).
Gerado por `tools/blender/gen_interiors_l01.py`; posição por `tools/unreal/l01_interiors.py`; aplicado na
Unreal por `tools/unreal/build_interiors_l01.py` **só depois do OK do usuário** (OD-P07).
Prévias: `assets/work/interiors/previews/` (fora, planta de cima, olho do herói a 1,70 m) e
`mapa_construcoes.png` / `mapa_construcoes_detalhe.png` (onde cada uma fica).

## Entráveis

| Construção | Zona | Tamanho (m) | Troca | Dentro (interação + contexto) |
|---|---|---|---|---|
| Loja de conveniência do posto | 2 | 10 x 14, pé-direito 3,4 | CON_PostoLoja (8,5 x 10, fechada) | vitrine e porta dupla, balcão com caixa (munição), 4 gôndolas, 4 geladeiras, depósito com estantes (kit médico), banheiro (bandagem), marquise vermelha |
| Escritório do posto (sala trancada) | 2 | 6 x 7 x 3 | blockout House_Single | escrivaninha com rádio e papéis, arquivos, armário, **baú da pistola** |
| Contêiner do acampamento | 0 | 6,1 x 2,5 x 2,6 | CON_Conteiner (fechado) | aberto numa ponta, estante e caixotes, bandagem |
| Casa da vila | 6 | 9 x 11 x 3, telhado de telha | 1a CON_CasaVila | sala (sofá, mesa, cadeiras), cozinha (kit médico), quarto (cama, armário, **baú da vila**) |
| Casa saqueada | 6 | 8 x 9 x 3 | 2a CON_CasaVila | móveis revirados, Fúria no quarto, kit médico |
| Oficina/cabana da vila | 6 | 7 x 7 x 3,2 | CON_Cabana | portão largo, bancada de ferramentas, pneus, armários, munição e bandagem |
| Oficina da estrada (nova) | 1 | 12 x 10 x 4,2 | lugar novo | portão de 4 m (o buggy entra), elevador de carro, bancada, pneus, escritório; reparo e nitro |
| Cabana do pesquisador (nova) | 3 | 7 x 8 x 3 | lugar novo | bancada com cristais brilhando, anotações (mensagem), cama; kit médico e munição |
| Galpão de abrigo (novo) | 5 | 14 x 10 x 4,5 | lugar novo | estantes industriais, caixotes, mesa; Fúria, munição, kit médico |
| Cabine da torre de rádio (nova) | 2 | 4,5 x 5 x 2,9 | lugar novo | rádio chiando (mensagem de resgate), munição |

Regras: porta >= 1 m (portões 2,2 a 4,5 m), pé-direito >= 2,6 m, paredes de 20 cm, forro com colisão
(câmera nunca no telhado), zona de câmera com braço de 1,9 m dentro (`AJRCameraZone`), luzes fracas
(30 cd, uma com sombra), rampa de 3,8 m em cada porta externa (o piso fica acima do ponto mais alto do chão).
Lugares novos têm só mensagem (não trocam a tarefa principal).

## Fechados de propósito

| Lugar | Por quê |
|---|---|
| Barracas do acampamento | já são abertas (o baú da chave fica dentro); não precisam de interior |
| Nave de resgate caída | marco da abertura; interior fica para a cena de abertura |
| Disco voador, colmeia, árvore-mãe, arco | marcos de paisagem (silhueta), não abrigos |
| Casas em ruína da vila (blockout) | ruína sem teto: dá para andar entre as paredes |
| Ônibus | cenário de rota (zona 5) |

## Depois do OK
1. Compilar (AJRCameraZone).
2. `py ".../tools/unreal/build_interiors_l01.py"`.
3. Regerar a vegetação (no PC: `python3 tools/blender/scatter_l01_v3.py`) e rodar `scatter_l01.py` (árvores fora dos lugares novos).
4. Build > Build Paths.

## Portas e móveis novos (A-076)
- Cada vão de porta tem uma porta de verdade (`AJRDoor`, 19 no total): E abre com animação para longe do
  herói; zumbis e a sobrevivente abrem sozinhos; vão de 1,7 m ou mais = porta dupla; portões de 3 m ou mais
  (oficina da estrada, galpão) já ficam abertos para fora. Folhas: madeira (casas, cabanas, oficina),
  metal (galpão, contêiner, oficina da estrada, cabine) e vidro (frente da loja do posto).
- Móveis novos: barril, tambor com fogo, entulho, tapete, estante, beliche, gerador, mesinha, TV, quadro de
  avisos, barricada, fogão. 133 móveis (eram 68). O galpão virou abrigo; casas com sala, cozinha e quarto.
- Conferência automática: `python tools/blender/check_interiors_l01.py` (precisa de bpy e shapely): móveis
  dentro das paredes, sem sobrepor, giro das portas livre e tudo alcançável da porta principal.
- Prévias: `assets/work/interiors/previews/folha_dentro_A076.png`, `folha_fora_A076.png`, `folha_planta_A076.png`.

## Ordem para aplicar (decidido, OD-P07)
1. Compilar (AJRCameraZone e AJRDoor).
2. `py ".../tools/unreal/build_interiors_l01.py"`.
3. Vegetação já regerada no PC (A-077): rodar `scatter_l01.py`.
4. Build > Build Paths.

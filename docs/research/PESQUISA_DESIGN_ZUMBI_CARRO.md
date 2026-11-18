# Pesquisa de design: jogos de zumbi com carro + a pé (Jogo de Resgate)

Data: 2026-11-15. Objetivo: embasar o redesign do Jogo de Resgate (UE 5.8, terceira pessoa, buggy + combate a pé, resgate de sobrevivente em um vale de floresta alienígena).

> Limitação: o WebFetch atingiu o limite de uso depois de 4 páginas. Só foram lidas por completo: a entrevista do Pacific Drive no site da Unreal, o guia de veículos de Dying Light: The Beast e a página do Blood Drive na Steam. O resto vem dos resultados de busca e de conhecimento consolidado de design sobre esses jogos. Os links indicam onde cada ponto pode ser verificado. Os números de densidade são estimativas recomendadas como ponto de partida, não números de uma fonte.

---

## 1. Jogos que misturam direção e ação a pé (zumbi/sobrevivência)

**1. Pacific Drive (Ironwood, 2024, feito em UE)**
- **Loop:** sair da garagem para uma zona, descer do carro para coletar (carcaças, prédios, anomalias), chegar a uma saída, voltar e consertar/melhorar.
- **Carro e a pé:** é obrigatório sair do carro para achar combustível e peças, e uma tempestade empurra você de volta para ele. Cada peça do carro tem vida própria, os reparos são feitos à mão em primeira pessoa, e no banco do motorista você fica protegido se o carro estiver inteiro.
- **Por que é divertido:** apego ao carro, runs curtas com a saída "sempre à vista" e a incerteza do que vem depois da próxima curva.
- Fontes: [entrevista Unreal Engine](https://www.unrealengine.com/en-US/developer-interviews/pacific-drive-is-a-run-based-driving-survival-game-with-an-ever-changing-mysterious-landscape), [GamesRadar](https://www.gamesradar.com/pacific-drive-preview-hands-on)

**2. Dying Light: The Beast (Techland, 2025)**
- **Carro:** serve para deslocamento rápido e seguro, mas o combustível é "severamente limitado".
- **Carro e a pé:** você reabastece a pé em postos ou sifonando carcaças, ou seja, precisa sair do carro em lugares perigosos.
- **Zumbis e carro:** zumbis comuns não causam dano quando atropelados, mas matar de carro dá quase nenhum XP, então o combate a pé continua sendo o principal. Bater em obstáculos faz o carro soltar fumaça, depois pegar fogo e explodir. Dá para jogar o carro em chamas contra uma horda como bomba.
- Fontes: [Gamepressure](https://www.gamepressure.com/dying-light-the-beast/are-there-vehicles/z211a78), [PC Gamer](https://www.pcgamer.com/games/action/watch-kyle-crane-activate-beast-mode-and-drive-his-new-car-in-dying-light-the-beast)

**3. Days Gone (Bend, 2019; versão PC/remaster depois)**
- **Moto:** é a sua linha de vida. O combustível é limitado (galões e postos para coletar) e a moto recebe upgrades.
- **Zumbis e moto:** hordas de centenas bloqueiam rotas. A graça é atrair a horda e fugir de moto até o ponto que você preparou antes. Freakers e emboscadas derrubam você da moto.
- **Carro e a pé:** é preciso estacionar para entrar em acampamentos, ninhos e casas.
- Fontes: [Game Informer](https://gameinformer.com/b/features/archive/2018/05/14/five-ways-days-gone-differs-from-other-open-world-games), [PlayStation Blog](https://blog.playstation.com/?p=210357), [guia PlayStation](https://www.playstation.com/en-ie/editorial/your-survival-guide-to-the-threat-filled-world-of-days-gone/)

**4. State of Decay 2 / 3 (Undead Labs)**
- **Carro:** funciona como inventário móvel (o porta-malas guarda o loot), com combustível e dano. As portas podem ser arrancadas.
- **Zumbis e carro:** zumbis agarram e puxam você para fora do carro, e os ferais arrancam você pela porta. Um carro muito batido morre no meio da horda.
- **Carro e a pé:** você dirige de ponto de interesse em ponto de interesse e limpa e revista as casas a pé, com o barulho atraindo mais zumbis.
- Fontes: [SoD Wiki: veículos](https://stateofdecay.fandom.com/wiki/Vehicles_(State_of_Decay_2)), [blog oficial](https://stateofdecay.com/?p=43400)

**5. Drive Beyond Horizons (acesso antecipado, 2025)**
- **Loop:** road trip de sobrevivência em mundo aberto. Você monta e conserta o carro peça por peça (motor, rodas, combustível), saqueia cidades a pé e enfrenta zumbis.
- **Carro como base:** o carro é a sua progressão e o seu lugar seguro. É a referência indie mais próxima do seu conceito, e viralizou na Steam.
- Fontes: [site oficial](https://drivebeyondhorizons.com), [wiki: mecânicas](https://wiki.drivebeyondhorizons.com/categorie/mecaniques), [resumo de avaliações VaporLens](https://vaporlens.app/app/2625420/drive_beyond_horizons)

**6. Blood Drive (Byte-Era, em breve)**
- **Loop:** combate veicular em mundo aberto contra hordas de até cerca de 4.000 zumbis. Você resgata sobreviventes, coleta recursos e faz upgrades.
- **Carro:** blindagem e armas no carro, mais atiradores de IA que você posiciona.
- **Zumbis e carro:** os zumbis enxameiam e reagem ao carro, e o impacto arremessa os inimigos. Há ninhos espalhados pelo mundo.
- **O que tirar daqui:** mostra a tendência do "carro como plataforma de armas".
- Fonte: [Steam](https://store.steampowered.com/app/3725500)

**7. Overland e Deadly Days: Roadtrip (roguelites de carro)**
- **Loop:** dirigir de parada em parada. Em cada parada você desce para achar combustível ou sobreviventes, com limite de turnos ou de tempo. O barulho atrai mais zumbis, então o ritmo é "entra, pega, sai".
- **O que tirar daqui:** ótima prova de que o ritmo de parar e coletar funciona.
- Fontes: [PC Gamer: análise de Overland](https://pcgamer.com/overland-review), [Rogueliker: Deadly Days Roadtrip](https://rogueliker.com/deadly-days-roadtrip-early-access-impressions/)

**8. Into the Dead: Our Darkest Days (PikPok, 2025)**
- **Loop:** sobreviventes num abrigo viajam até locais para coletar. Foco em furtividade, com escolhas tensas entre barulho e loot.
- **O que tirar daqui:** mostra que "viagem, coleta curta e tensa, volta" funciona mesmo em escopo pequeno.
- Fontes: [PC Gamer](https://www.pcgamer.com/games/survival-crafting/dread-tension-and-tough-choices-abound-in-stealthy-zombie-survival-game-into-the-dead-our-darkest-days), [VaporLens](https://vaporlens.app/app/2239710/into_the_dead_our_darkest_days)

**9. Dead Island 2 (2023) e Dead Rising Deluxe Remaster (2024)**
- **Carro:** não há direção de verdade.
- **Por que importam:** a diversão vem da sensação do corpo a corpo, do gore e das armas improvisadas, e de um cenário cheio de props pensados para o combate (barris explosivos, poças, fios elétricos). Vale copiar para a parte a pé.
- Fontes: [Motionographer sobre DI2](https://motionographer.com/2025/01/27/dead-island-2-a-stunning-visual-zombie-gore-feast/), [Dead Rising Remaster na Steam](https://store.steampowered.com/app/2527390/Dead_Rising_Deluxe_Remaster)

### O que esses jogos têm em comum
- É preciso sair do veículo várias vezes, por combustível, peças, portões ou loot. Nunca é uma metade de carro e uma metade a pé.
- O veículo é frágil e valioso.
- Os zumbis são obstáculos e ameaças ao carro: bloqueiam estradas, agarram as portas e danificam peças. Não são só lombadas.
- Atropelar é satisfatório, mas a recompensa está no combate a pé.

---

## 2. Padrões de design para escopo pequeno (um nível de cerca de 2x2 km, 10 a 15 minutos)

### Padrões

**AI Director (Left 4 Dead).** Mede a "intensidade" do jogador (dano recebido, abates, tempo desde a última luta) e alterna entre construção, pico e alívio. Os spawns acontecem fora da visão, a uma distância mínima do jogador, e têm limite. Versão simples para iniciante em Blueprint:
- Um float de intensidade que sobe com dano e abates e cai com o tempo.
- Na construção, grupos pequenos a cada 20 a 40 segundos.
- No pico, um evento de horda de cerca de 60 segundos.
- No alívio, nenhum spawn por 30 a 45 segundos.

Fontes: [Valve Director Scripts](https://developer.valvesoftware.com/wiki/Left_4_Dead_2/Scripting/Director_Scripts), [Game Developer: estrutura ou AI Director](https://gamedeveloper.com/design/structure-or-ai-director-), [Shacknews: Evolve sobre picos e vales](https://shacknews.com/article/82787/how-evolve-assures-action-peaks-and-valleys), [artigo PaceMaker](https://arxiv.org/pdf/2408.15001)

**Algo interessante a cada 20 a 40 segundos de direção.** Exemplos: uma carcaça para saquear, um grupo de zumbis na estrada, uma rampa, um galão de combustível, um marco que aparece no horizonte.

**Loot em camadas.** Carcaças na beira da estrada dão itens comuns (munição, sucata). Casas dão itens médios (cartuchos de escopeta, kits médicos). Pontos de interesse perigosos ou bloqueados dão itens raros (uma peça do carro, a própria escopeta). Coloque o melhor loot onde o jogador precisa descer do carro.

**O carro precisa de combustível e peças achados a pé.** É a principal alavanca para forçar a alternância (Pacific Drive, Dying Light: The Beast, Days Gone). Mantenha simples: um medidor de combustível e 1 ou 2 "peças-chave" (por exemplo um guincho ou um para-choque de impacto).

**Bloqueios que obrigam a descer.** Uma árvore alienígena caída, um portão trancado, uma ponte quebrada, um terreno íngreme demais para o carro. Abrir o caminho é uma tarefa a pé (achar uma chave, um fusível ou explosivos) enquanto os zumbis se aproximam.

**Zumbis interagindo com o carro.** Sobem no capô ou no teto e você ziguezagueia para derrubá-los. Agarradores deixam o carro mais lento. Barricadas de corpos ou carcaças bloqueiam a estrada. Zumbis pesados danificam o carro. Atropelar tem custo (vida do carro), então o carro não é invencível.

**Hordas ligadas ao barulho.** Abrir um portão ou ligar um gerador chama uma horda. As opções são defender, fugir de carro ou usar o carro como bomba.

**Zonas seguras e sensação de carro como base.** Travar as portas do carro ou uma garagem segura dão o momento de "alívio".

**Vale aberto em vez de estrada com paredes.** Use marcos e bloqueios naturais (pedras, mata densa, penhascos, água) em vez de paredes invisíveis. Ofereça 2 ou 3 rotas alternativas entre os pontos de interesse.

### Estrutura de nível recomendada (cerca de 12 a 15 minutos, alternando 4 vezes)

| # | Zona | Modo | O que acontece | Tempo |
|---|---|---|---|---|
| 0 | **Local da queda / acampamento** (início) | A pé | Tutorial de corpo a corpo contra 3 a 5 zumbis lentos. Achar a chave ou o fusível do buggy numa barraca. Aprender a pistola. O rádio dá o objetivo: chegar ao sinalizador do sobrevivente. | 1,5 min |
| 1 | **Estrada do vale A** | Carro | Terreno aberto com 2 opções de rota. Grupos pequenos para atropelar, 2 a 3 carcaças com loot (sucata e munição). O combustível começa em cerca de 40%. | 2 min |
| 2 | **Posto / entreposto** | A pé | O combustível acaba. Sifonar ou encher um galão enquanto uma mini-horda cresce (pico do Director). Loot nível 2: cartuchos, kit médico. Opcional: a escopeta fica num quarto dos fundos trancado. | 2 min |
| 3 | **Trilha da floresta alienígena** | Carro | Mais estreita e densa, com flora brilhante. Zumbis sobem no carro (derrube-os) e uma barricada de corpos obriga a atropelar ou desviar. | 1,5 min |
| 4 | **Árvore gigante caída / ponte quebrada** | A pé | Um bloqueio. Pegar explosivos ou a peça do guincho numa colmeia ou caverna próxima. Loot raro (a escopeta, se ainda não foi achada). A explosão faz barulho e dispara uma horda. | 2,5 min |
| 5 | **Fuga da horda** | Carro | Passar pela abertura com a horda atrás. Zumbis pesados batem no carro. Opcional: usar o carro como bomba. Pico curto e intenso. | 1 min |
| 6 | **Local do sobrevivente** (assentamento em ruínas ou nave caída) | A pé | Limpar a área com corpo a corpo, pistola e escopeta. Achar o sobrevivente. Defender por 60 a 90 segundos enquanto ele faz a ligação direta ou abre a rota de fuga. | 2,5 min |
| 7 | **Extração** | Carro | O sobrevivente vai junto (e poderia atirar do banco do passageiro). Sair do vale ao pôr do sol. Pouca resistência, depois o fim. | 1 min |

A regra por trás da tabela: nenhum trecho de carro ou a pé deve passar de cerca de 2,5 minutos. Toda troca de carro para a pé precisa de um motivo (combustível, bloqueio, loot, objetivo). Toda troca de a pé para carro deve parecer alívio ou fuga.

---

## 3. Densidade do cenário em um ambiente estilizado ou low-poly

### Camadas (coloque nesta ordem)

1. **Variação do material do chão:** 3 a 4 camadas na landscape (musgo, terra, solo alienígena, rocha) misturadas por inclinação e altura. Decals para trilhas e marcas de pneu.
2. **Cobertura do chão / grama:** o fator que mais faz o cenário parecer cheio. Use Landscape Grass Type ligado ao material da landscape, assim ele aparece sozinho.
3. **Props pequenos e detalhes:** pedras, cogumelos, ossos, entulho, casulos alienígenas. Em grupos, não espalhados por igual.
4. **Arbustos e samambaias** na altura da cintura. Quebram a linha de visão e escondem zumbis.
5. **Árvores,** com 2 a 3 espécies e variação de tamanho e rotação. Agrupadas em bosques, com clareiras entre eles.
6. **Marcos e props de destaque:** um por zona, visível de longe (uma árvore gigante brilhante, uma nave caída, uma torre de rádio, a placa de um posto). Orientam sem precisar de paredes.
7. **Horizonte:** montanhas ou penhascos distantes como cards low-poly, névoa ou bruma atmosférica, um planeta alienígena no céu.

A regra dos artistas de ambiente: deixe denso onde o jogador olha (beira da estrada, pontos de interesse) e barato na distância, com névoa e impostors.

Fontes: [Game Developer: dicas de arte para florestas](https://www.gamedeveloper.com/art/art-tips-for-building-forests), [80.lv: árvores, arbustos e flores estilizados](https://80.lv/articles/setting-up-trees-bushes-and-flowers-for-a-stylized-3d-environment), [80.lv: dicas para a floresta perfeita](https://80.lv/articles/tips-on-creating-a-perfect-forest/), [The Level Design Book: arte de ambiente](https://book.leveldesignbook.com/process/env-art)

### Densidades iniciais

Estimativas minhas para um jogo estilizado a 60 fps em hardware médio. Ajuste no olho e com `stat unit`.

| Camada | Instâncias por 100 m² | Distância de corte (cull) |
|---|---|---|
| Grama e cobertura do chão (Landscape Grass) | 300 a 800, só na área "perto" | 40 a 80 m |
| Props pequenos e pedras | 2 a 6, em grupos | 80 a 150 m |
| Arbustos e samambaias | 3 a 8 na beira da estrada e nos pontos de interesse, 1 a 2 no resto | 150 m |
| Árvores | 0,5 a 2 na floresta, 0 a 0,2 nas clareiras | cerca de 400 m a 1 km, ou sem corte com Nanite ou HLOD |
| Marcos | 1 por zona, cerca de 6 a 8 no mapa todo | sempre visíveis |

### Ferramentas do UE5 (era 5.7 e 5.8)

- **Landscape Grass Type:** o melhor para grama e cobertura do chão. Zero trabalho manual, segue as camadas pintadas. Mantenha a distância de corte curta.
- **Foliage Mode (pintura manual):** para arbustos, árvores e props colocados à mão perto dos pontos de interesse. O melhor controle para iniciante.
- **PCG Framework** (pronto para produção desde a 5.7): espalha por regras (inclinação, distância das splines da estrada, áreas de exclusão em volta dos pontos de interesse). Um único grafo pode preencher o vale inteiro e se regenera quando você muda a estrada. Recomendado depois que o layout estiver definido. A 5.7 também trouxe o Procedural Vegetation Editor e melhorias de Nanite em folhagem.
- **Procedural Foliage Spawner:** ferramenta mais antiga, praticamente substituída pelo PCG. Pode pular.

Dicas de desempenho para iniciante:
- Use folhagem instanciada (HISM). O Foliage tool e o PCG já fazem isso sozinhos.
- Ative Nanite em árvores, pedras e props.
- Para grama, prefira malhas simples com distância de corte e sombra desligada.
- Use World Partition com HLOD no mapa de 2x2 km.
- Meça com `stat fps`, `stat unit` e `stat foliage`.

Fontes: [StraySpark: primeiros passos com PCG](https://www.strayspark.studio/blog/ue5-pcg-framework-getting-started), [StraySpark: benchmark Nanite foliage vs HISM vs PCG](https://www.strayspark.studio/blog/ue57-nanite-foliage-vs-hism-vs-pcg-benchmark), [StraySpark: desempenho de Nanite foliage](https://www.strayspark.studio/blog/ue5-nanite-foliage-procedural-placement-performance), [Digital Production: folhagem e PCG na UE 5.7](https://digitalproduction.com/2025/11/12/unreal-engine-5-7-foliage-pcg-and-in-editor-ai/), [referência das ferramentas de mundo aberto da UE](https://dev.epicgames.com/documentation/unreal-engine/open-world-tools-property-reference-in-unreal-engine), [fórum UE: otimização de grama](https://forums.unrealengine.com/t/grass-optimisation-in-unreal-engine-5/1152397)

---

## 4. HUD/UI com identidade

### Estilos de referência
- **Dead Space:** totalmente diegético. A vida é uma coluna brilhante no traje, a munição é um holograma na arma, os menus são hologramas projetados no mundo. O visual é icônico porque a UI faz parte da ficção.
- **Days Gone:** estética minimalista e desgastada de motoqueiro.
- **Dying Light:** HUD de sobrevivência limpo com uma tipografia suja característica.
- **Dead Island 2:** menus barulhentos, pop/quadrinho, no estilo de pôster turístico de Los Angeles, e uma marca que coloca o gore na frente.
- **Back 4 Blood / Left 4 Dead:** painéis de status da equipe. L4D usa pichações no cenário como UI narrativa.
- **This War of Mine:** UI em esboço a carvão. O estilo desenhado à mão faz um jogo pequeno parecer autoral.

O que evita uma HUD genérica: uma metáfora visual forte aplicada em tudo (HUD, menus, fontes, sons, animações); posicionamento diegético ou semi-diegético; paleta limitada; ícones próprios em vez de ícones de banco; e reação ao estado do jogo (rachaduras, cintilação, glitches ao tomar dano) em vez de barras paradas.

Fontes: [Dead Space 2: interface diegética](https://www.hudsandguis.com/2012/08/22/dead-space-2-diegetic-interface-design), [TheGamer: UI de terror de Dead Space](https://www.thegamer.com/dead-space-horror-ui/), [Wayline: interfaces diegéticas](https://www.wayline.io/blog/diegetic-interfaces-game-design), [Indieklem: o dilema diegético](https://indieklem.substack.com/p/19-the-diegetic-dilemma-benefits), [Game Developer: 6 exemplos de UI para estudar](https://gamedeveloper.com/audio/6-examples-of-ui-design-that-every-game-developer-should-study), [TheGamer: UIs estilosas](https://www.thegamer.com/games-with-stylish-great-user-interfaces-ui-hud-menus/), [Game Developer: UX de This War of Mine](https://gamedeveloper.com/design/learning-and-improving-upon-this-war-of-mine-a-ux-ui-analysis), [Motionographer: Dead Island 2](https://motionographer.com/2025/01/27/dead-island-2-a-stunning-visual-zombie-gore-feast/)

### Três direções para um jogo de zumbi em floresta alienígena

**A) "Bio-scanner" (semi-diegético, tecnologia alienígena)**
- Um aparelho de pulso ou o visor do capacete projeta UI holográfica ciano ou verde que dá glitch ao tomar dano.
- A vida é uma linha de biomonitor pulsando.
- O combustível e a vida do buggy aparecem num painel holográfico dentro do carro (totalmente diegético).
- O marcador do objetivo é o sinalizador do sobrevivente pingando num radar. As plantas bioluminescentes podem usar a mesma linguagem de cor.

**B) "Diário de campo / fita de guarda-parque" (grunge desenhado à mão)**
- Ícones em esboço de tinta sobre papel rasgado e fita adesiva.
- O mapa é um caderno desenhado à mão com círculos de caneta.
- A vida é uma barra rabiscada e a munição são cartuchos desenhados a lápis.
- Barato de produzir, muito característico, e contrasta bem com o mundo alienígena.

**C) "Ficção científica pulp de filme B" (quadrinho)**
- Estilo de pôster de invasão alienígena dos anos 50: retícula de pontos, tipografia grossa com contorno, onomatopeias de quadrinho nos abates ("SPLAT!") e nas batidas do carro.
- Os títulos das zonas aparecem como quadros de HQ.
- Combina melhor se o jogo for mais divertido e exagerado do que terror.

Minha escolha: A para a HUD, com B ou C para menus e mapa. A UI dentro do carro deve ser diegética (mostradores do painel) em qualquer caso.

---

## Top 10 mudanças recomendadas (em ordem)

1. Trocar a divisão "primeira metade carro, segunda metade a pé" por 4 ciclos alternados de carro e a pé, cada um com 1,5 a 2,5 minutos, seguindo a tabela de zonas da seção 2.
2. Adicionar um medidor de combustível e 1 ou 2 peças do carro que só se acham a pé, para que sair do carro sempre tenha um motivo.
3. Fazer os zumbis interagirem com o buggy: subir no carro (derrubar ziguezagueando), agarrar e deixar mais lento, causar dano, e barricadas de corpos na estrada. Dar vida ao carro e um estado de fumaça, fogo e explosão.
4. Criar um AI Director simples (float de intensidade com estados de construção, pico e alívio, spawn fora da visão, limite de spawns) no lugar de spawns fixos.
5. Remover a estrada linear com paredes. Fazer um vale aberto com 2 ou 3 opções de rota e bloqueios naturais (pedras, penhascos, mata densa, água).
6. Colocar um bloqueio em cada transição de zona (árvore alienígena caída, ponte quebrada, entreposto trancado) que exige uma tarefa a pé e dispara uma horda pelo barulho.
7. Adicionar loot em camadas: carcaças dão itens comuns, casas e entrepostos dão itens médios, pontos de interesse perigosos e bloqueados dão itens raros (a escopeta, peças do carro).
8. Preencher o cenário em camadas: Landscape Grass Type para a cobertura do chão, PCG ou pintura de Foliage para arbustos e árvores ao longo das splines da estrada, mais 1 marco visível por zona e um horizonte com bruma.
9. Escolher uma identidade de HUD (bio-scanner alienígena) com painel diegético no carro e glitch ao tomar dano, em vez de barras genéricas.
10. Terminar com uma sequência de defender e depois extrair, em que o sobrevivente vai no buggy (e poderia atirar do banco do passageiro), para que a última direção seja a recompensa.

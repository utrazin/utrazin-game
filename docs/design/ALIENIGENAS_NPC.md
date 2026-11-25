# Villa Star: alienígenas, veículos e o que gerar

> Versão 0.1, 17/11/2026. Ficha de cada personagem e veículo para você gerar o modelo 3D (Tripo ou outro).
> Complementa `docs/design/REMAP_CIDADE_ARENA.md`. Nomes e espécies são provisórios: mude o que quiser.

## 1. O mundo em 3 linhas

**Villa Star** é um entreposto num planeta na beira da galáxia onde vivem espécies de todos os cantos: comerciantes, refugiados, mecânicos, cientistas. Lá fora, além da muralha, tem a praga de zumbis e criaturas alienígenas hostis. A colônia sobrevive atrás da muralha e do campo de força, e você, o único humano da cidade, que chegou na nave que caiu, vira o caçador que sai para as arenas.

Inimigos: os **zumbis atuais são o inimigo padrão** da arena (os que enchem a tela). Depois entram **alienígenas hostis** (predadores, saqueadores), que você também vai gerar; não precisam ser infectados.

## 2. Regras para gerar (vale para todos)

1. **Um personagem por arquivo**, corpo inteiro, sem chão nem cenário, fundo liso.
2. **Pose:**
   - Humanoide (2 braços, 2 pernas, cabeça): **pose em A** (braços abertos uns 45 graus, pernas um pouco afastadas), olhando para a frente, pés no chão. Assim dá para usar animações do Mixamo.
   - Não humanoide (flutua, tentáculos, 4 patas): pose neutra parada. Esses eu animo com movimento procedural (flutuar, balançar) ou com o Forge 3D.
3. **Tamanho real**: diga a altura na hora de gerar e no nome do arquivo (ex.: `NPC_Armeiro_2m40.glb`).
4. **Estilo de todos igual:** "semi-realistic stylized, clean PBR materials, saturated colors, game-ready", sem texto e sem logotipo, sem cabelo fino demais (fica ruim em tempo real). Se a ferramenta deixar, mande junto a imagem de referência da cidade para manter o mesmo estilo.
5. **Formato:** GLB ou FBX com textura. Até ~40 mil triângulos por personagem (eu reduzo se vier maior). Textura 2K.
6. **Acessórios grandes** (avental, ferramenta na mão, mochila) podem vir junto. Arma na mão não: eu coloco depois.
7. **Gere primeiro uma imagem 2D** (frente) e aprove; depois gere o 3D a partir dela. Fica bem mais consistente.

Depois que você me manda o arquivo, eu: confiro no Noct3DViewer, faço o rig (Mixamo para os humanoides), corrijo a escala (sem o problema do Hips em escala 100), importo com colisão e coloco no balcão com as animações.

## 3. Os vendedores e moradores com função

Ordem de prioridade: **1 a 3 primeiro** (são do protótipo).

| # | Função | Nome | Espécie | Corpo | Altura |
|---|---|---|---|---|---|
| 1 | **Armeiro** (compra de armas) | Krug | Torvak | humanoide | 2,4 m |
| 2 | **Bancada** (melhoria de armas) | Ix-Vel | Kitrin | humanoide pequeno | 1,3 m |
| 3 | **Guarda do Portão** (sai para a arena) | Kaar | Avari | humanoide | 2,2 m |
| 4 | Laboratório (pesquisa) | Dra. Oorra | Medusiana | flutuante | 1,8 m |
| 5 | Clínica (vida, cura) | Sêmea | Florani | humanoide alto | 2,1 m |
| 6 | Garagem (bicicleta e moto) | Brumm | Rochoso | humanoide grande | 2,3 m |
| 7 | Rádio / contratos | Lia-7 | Sintética | humanoide | 1,75 m |
| 8 | Mercado (consumíveis) | Tuk | Pelúcio | humanoide pequeno | 1,1 m |
| 9 | Prefeitura | Prefeito Glub | Anfíbio | humanoide largo, sentado | 1,9 m |
| 10 | Bar | Zé Seis-Braços | Polvoide | não humanoide | 1,6 m |
| 11 | Armazém | Mmb | Gelatinoso | não humanoide | 1,4 m |
| 12 | Casa do herói | Bip | robô | flutuante | 0,5 m |

### Fichas (descrição + texto para gerar)

**1. Krug, o Armeiro (Torvak)**
Grandalhão reptiliano com **4 braços**, couraça cinza-esverdeada nas costas e ombros, mandíbula larga, olhos amarelos pequenos. Avental de couro grosso com bolsos de munição, braçadeiras de metal. Calmo, fala pouco, ri grosso.
> Full body 3D character, stylized semi-realistic alien arms dealer, huge reptilian humanoid with four muscular arms, grey-green armored carapace on back and shoulders, wide jaw, small yellow eyes, thick leather apron with ammo pouches, metal bracers, A-pose, front view, plain background, game-ready, clean PBR textures, 2.4 meters tall

Obs.: 4 braços não seguem o Mixamo nos braços de baixo. Eu animo os de baixo à parte (cruzar, apoiar no balcão). Se quiser simples, gere com 2 braços.

**2. Ix-Vel, a da Bancada (Kitrin)**
Pequena, insetoide, magra, pele azul-esverdeada brilhante como besouro, **olhos com lentes de aumento** presas na cabeça, antenas, 3 dedos longos. Cinto de ferramentas, luvas grossas. Rápida, fala muito.
> Full body 3D character, stylized semi-realistic small insectoid alien engineer, slim body with glossy blue-green beetle-like shell, large compound eyes covered by brass magnifying goggles, two antennae, long three-fingered hands, tool belt, thick work gloves, A-pose, front view, plain background, game-ready, 1.3 meters tall

**3. Kaar, o Guarda do Portão (Avari)**
Guerreiro alto com cabeça de ave de rapina (bico, crista de penas vermelhas), armadura leve de placas escuras, capa curta, lança de energia (pode vir na mão). Sério, protetor.
> Full body 3D character, stylized semi-realistic alien gate guard, tall bird-like humanoid with raptor head, curved beak, red feather crest, dark plated light armor, short cape, holding an energy spear, A-pose, front view, plain background, game-ready, 2.2 meters tall

**4. Dra. Oorra, do Laboratório (Medusiana)**
Ser parecido com água-viva dentro de um **traje de vidro e metal** (cúpula de vidro na cabeça, corpo de tecido técnico), tentáculos luminosos saindo por baixo, flutua a uns 20 cm do chão. Cor lilás com brilho ciano.
> Full body 3D character, stylized semi-realistic floating jellyfish-like alien scientist inside a glass dome helmet and technical suit, glowing translucent tentacles hanging below, lilac body with cyan bioluminescence, hovering pose, front view, plain background, game-ready, 1.8 meters tall

**5. Sêmea, da Clínica (Florani)**
Alta e esguia, corpo de **planta** (pele em casca lisa verde-clara, folhas no lugar de cabelo, flores brancas que brilham no peito e nas mãos). Roupa de enfermaria simples. Fala devagar.
> Full body 3D character, stylized semi-realistic tall slender plant alien healer, smooth pale green bark skin, leaves instead of hair, glowing white flowers on chest and hands, simple medic robe, A-pose, front view, plain background, game-ready, 2.1 meters tall

**6. Brumm, da Garagem (Rochoso)**
Mecânico enorme de **pedra** com veias de magma laranja, mãos gigantes, macacão rasgado sujo de graxa, chave inglesa no cinto. Bonachão.
> Full body 3D character, stylized semi-realistic huge rock golem alien mechanic, stone skin with glowing orange magma cracks, oversized hands, torn greasy overalls, big wrench on belt, A-pose, front view, plain background, game-ready, 2.3 meters tall

**7. Lia-7, do Rádio (Sintética)**
Androide de aparência gentil, rosto liso de porcelana branca, **antena e fones** na cabeça, corpo com placas brancas e juntas azuis, cabos saindo das costas para o painel de rádio.
> Full body 3D character, stylized semi-realistic female android radio operator, smooth white porcelain face, antenna and headset on head, white plated body with glowing blue joints, cables coming from back, A-pose, front view, plain background, game-ready, 1.75 meters tall

**8. Tuk, do Mercado (Pelúcio)**
Pequeno e peludo (laranja e creme), orelhas enormes, cauda grossa, **mochila gigante** cheia de coisas penduradas. Vendedor esperto.
> Full body 3D character, stylized semi-realistic small furry alien merchant, orange and cream fur, huge ears, thick tail, carrying an oversized backpack full of hanging goods, A-pose, front view, plain background, game-ready, 1.1 meters tall

**9. Prefeito Glub (Anfíbio)**
Sapo enorme e redondo, pele verde-oliva úmida, papada, **manto cerimonial** roxo com medalha dourada, bengala. Burocrata vaidoso. Pode ficar sempre sentado.
> Full body 3D character, stylized semi-realistic large round toad-like alien mayor, moist olive green skin, double chin, purple ceremonial robe with golden medal, walking cane, A-pose, front view, plain background, game-ready, 1.9 meters tall

**10. Zé Seis-Braços, do Bar (Polvoide)**
Polvo de **6 tentáculos**, cabeça grande, colete de garçom, um pano em um tentáculo e copo em outro. Fica atrás do balcão (só aparece da cintura para cima).
> 3D character, stylized semi-realistic octopus-like alien bartender with six tentacles, large head, waiter vest, holding a cloth and a glass, neutral pose, front view, plain background, game-ready, 1.6 meters tall

**11. Mmb, do Armazém (Gelatinoso)**
Bolha de gelatina verde translúcida com **caixas e objetos boiando dentro** do corpo, dois olhos grandes, braços que se formam e somem.
> 3D character, stylized semi-realistic translucent green slime alien warehouse keeper, crates and small objects floating inside its body, two big eyes, short stretchy arms, neutral pose, front view, plain background, game-ready, 1.4 meters tall

**12. Bip, da Casa (robô)**
Pequeno drone redondo flutuante com um olho de tela. Esse eu posso fazer no Forge 3D se você preferir.

### Moradores (sobreviventes resgatados)
Um grupo de **6 espécies simples** (humanoides, para usar as animações do Mixamo) com 2 ou 3 variações de cor cada. Andam pela cidade, trabalham nos prédios e aparecem conforme você resgata. Sugestão: reaproveitar as espécies acima em versão "comum" (outra roupa) e criar mais 2: uma espécie de pele cristalina e uma de pele escamosa azul.

## 4. Veículos com pegada alienígena

Regra técnica para os dois: **rodas como peças separadas** (eu giro elas no jogo), dizer o diâmetro da roda, vir em pé, de lado, sem piloto.

**Bicicleta "Casulo"**
Quadro orgânico de **quitina** (parece osso polido de inseto), guidão em forma de chifres, **rodas sem raio** (aro com brilho por dentro), selim de couro alienígena. ~1,8 m de comprimento, rodas de 70 cm.
> 3D model, stylized semi-realistic alien bicycle, organic frame made of polished insect chitin, horn-shaped handlebars, hubless wheels with glowing inner rim, alien leather saddle, side view, plain background, game-ready, 1.8 meters long, wheels 70 cm diameter, wheels as separate parts

**Moto elétrica "Arraia"**
Formato baixo e largo inspirado numa **arraia**, carenagem lisa roxa/escura com linhas luminosas, rodas sem raio grossas com brilho, painel holográfico. ~2,1 m, rodas de 65 cm.
> 3D model, stylized semi-realistic alien electric motorcycle shaped like a manta ray, low wide smooth dark purple fairing with glowing light lines, thick hubless wheels with glowing rims, holographic dashboard, side view, plain background, game-ready, 2.1 meters long, wheels 65 cm diameter, wheels as separate parts

## 5. Lugares que precisam de referência sua

1. **Uma rua da Villa Star** (imagem 2D): 2 ou 3 fachadas, chão, iluminação. Define o estilo de tudo.
2. **Portão da Arena + um pedaço de muralha** (com o campo de força).
3. **Monumento da praça** (a sua nave caída, que vai sendo restaurada).

Depois dessas três, eu retrabalho as construções que já existem para combinarem.

### 5.1 Prompts da arte da vila (18/11)
Estilo fixo: o da `referencias/rua_villa_star_v2.png` e da `fachada_armeiro_v2_aprovada.png` (pintado, contorno escuro, céu roxo com planeta de anel, pedra cinza esverdeada, brilhos ciano, lampião âmbar). No Gemini, anexe a rua v2 como referência de estilo em toda geração.
Duas etapas por prédio: (A) cena para aprovar o visual; (B) versão isolada para o Tripo (fundo branco liso, frente e costas).

**Bancada (Ix-Vel, inseto engenheiro)**
> (A) Same art style as the attached reference image. A small alien engineering workshop facade on the same street: walls of polished amber insect chitin plates riveted to dark iron, a big round workshop door half open showing a workbench with tools and glowing cyan parts, brass gears and thin antenna-like pipes on the roof, a hanging sign with a wrench-and-gear symbol (symbol only, no letters), warm amber lamp post at the side, crates and spare parts on the sidewalk, purple dusk sky with ringed planet. No people, no text, no measurement lines.
> (B) Same building as the attached image, isolated, centered, full building visible from the ground to the roof, plain white background, no ground plane, no sky, no lamp post, no loose crates, game asset concept, front view. (Depois o mesmo com "back view".)

**Portão da Arena + muralha**
> (A) Same art style as the attached reference image. The massive arena gate of an alien frontier town: two tall stone-and-iron towers with claw-shaped tops, a wide arched gate between them filled with a shimmering cyan energy force field, a section of thick town wall continuing on both sides with battlements and glowing cyan crystals embedded in the stone, warning lights, a guard post booth beside the gate, purple dusk sky with ringed planet. No people, no text, no measurement lines.
> (B) Isolar em duas peças separadas: só o portão com as duas torres; e só um trecho reto de muralha de 20 metros (para repetir). Plain white background, front view, depois back view.

**Prédio comum (encher os quarteirões, 2 variações)**
> (A) Same art style as the attached reference image. Two small alien residential houses side by side on the same street, each a different style: one rounded house made of stacked grey stone shells with a small round window glowing cyan, one narrow two-story house of rusty iron plates with pipes and a satellite dish, small balconies, potted alien plants, purple dusk sky with ringed planet. No people, no text, no measurement lines.
> (B) Uma casa por imagem, isolada, plain white background, front view e back view.

Regras de sempre: sem texto e sem régua na imagem; frente e costas no Tripo Multiview (não 3/4); me mandar a imagem (A) antes de gerar a (B).

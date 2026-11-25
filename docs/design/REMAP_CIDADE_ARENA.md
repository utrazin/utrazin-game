# Remap: Villa Star, cidade + arena (incremental 3D)

> Versão 0.2, 17/11/2026. Incorpora as respostas do usuário (seção 0). Substitui a estrutura "fase com metade carro, metade a pé" do GDD 0.4.
> Nada aqui foi implementado. Números de economia são proposta inicial, conferidos só numa simulação (`tools/design/sim_economia.py`).
> Mapa da cidade em rascunho: `docs/design/mapa_cidade_proposta.png`. Personagens e veículos para gerar: `docs/design/ALIENIGENAS_NPC.md`.

---

## 0. Decisões do usuário (17/11)

| # | Decisão |
|---|---|
| Q1 | Planeta alienígena. A cidade é um entreposto onde vivem **espécies de toda a galáxia**; cada função da cidade é um **alienígena diferente** (o usuário gera os modelos a partir das fichas em `ALIENIGENAS_NPC.md`) |
| Q2 | **Bicicleta e moto elétrica**, as duas com visual alienígena |
| Q3 | **Sim, poder temporário dentro da arena estilo Archero**: junta energia matando, sobe de nível, escolhe 1 entre 3 bônus que só valem naquela corrida (seção 6.6) |
| Q4 | Pensar bem o que se perde ao morrer, sem quebrar a sensação de incremental (seção 7.5) |
| Q5 | Não ter só um modo. Modo principal **sem tempo**: fica até sair ou morrer. Modos com tempo como variação (seção 6.7) |
| Q6 | **Nada acontece com o jogo fechado** |
| Q7 | Sem prestígio na v1 |
| Q8 | **Infinito**, sem final de história (seção 8.1) |
| Q9 | Dia e noite visual; noite com arena de risco opcional |
| Q10 | Os 2 personagens com bônus pequenos diferentes |
| Q11 | 3ª pessoa com a mira atual |
| Q12 | Sem veículo na arena |
| Q13 | Cidade segura; invasão como evento raro depois |
| Q14 | Trabalhar melhor o mapa (seção 3.5) |
| Q15 | PC, teclado e mouse e controle |
| Q16 | Por enquanto **não vai ser vendido** (pode ser no futuro). O Noct3DViewer pode ser usado agora; rever antes de vender |
| Q17 | Low poly só em props de fundo e pickups (seção 10) |
| Q18 | 400 x 400 m é a área dentro da muralha |
| Q19 | Nome provisório: **Villa Star** |
| Q20 | v1 com 3 setores e 5 armas |

---

## 1. Ideia em uma frase

**Villa Star**, um entreposto murado de 400 x 400 m num planeta alienígena onde vivem espécies de toda a galáxia, é a sua base e o seu "menu" (você é o único humano, chegou na nave que caiu; a praga que cria os zumbis infecta qualquer espécie): você anda (ou pedala) pela cidade, conversa com as pessoas, compra e melhora armas, e quando está pronto sai pelo **Portão** para uma **arena gerada na hora**, mata zumbis, junta dinheiro e materiais, resgata sobreviventes e volta mais forte. A cidade cresce com o que você traz.

É o casamento de três coisas que estão dando certo agora:

| Referência | O que pegar | O que evitar |
|---|---|---|
| **Megabonk** (3D survivors, solo dev, 2025) | Arena 3D gerada a cada ida, baús, santuários que mudam a corrida, missões (quests) que liberam conteúdo, visual simples que roda bem | Ataque automático (aqui o tiro é do jogador, nosso combate já existe) |
| **BALL x PIT** (2025) | Corridas curtas de 10 a 15 min e uma cidade entre elas onde você constrói prédios que dão bônus permanentes e liberam personagens | A parte de construir a cidade foi a mais criticada (mover peças em grade é chato). Aqui a cidade é fixa e você só "reforma" |
| **Hades** | Voltar para casa depois de morrer é parte da história: personagens comentam a corrida, a casa muda, cada morte rende progresso | Diálogo em massa (caro). Começar com poucas falas por NPC |
| **CoD Zombies** | Comprar arma na parede, máquina de melhoria (Pack-a-Punch), dinheiro por matar | Preços fixos sem curva |
| **Brotato / Vampire Survivors** | Loja com escolhas, ouro entre corridas que vira melhoria permanente, "nenhuma corrida é perdida" | Telas de menu; aqui a loja é um lugar com uma pessoa |
| **Jogos incrementais** (Cookie Clicker, Nodebuster) | Custo cresce em curva (x 1,15 por nível), produção cresce devagar, árvore de melhorias visível | "Prestígio" (recomeçar do zero) fica para depois, se precisar |
| **Dave the Diver** | Dois loops que se alimentam (mergulhar de dia, restaurante à noite) | Novidade constante cansa se o núcleo for raso |

Pesquisa detalhada e fontes na seção 13.

---

## 2. O loop

```
CIDADE (calma, sem combate)                          ARENA (combate, 5 a 10 min)
 conversar, comprar, melhorar, escolher contrato  ->  Portão: escolhe setor e nível
            ^                                         ondas pelo Diretor, baús, santuários, objetivo
            |                                         sobrevivente para resgatar (opcional)
            |                                                    |
   gastar créditos, sucata e cristais  <-  volta: relatório da corrida (ganhos, recorde)
   sobrevivente resgatado vira morador                morrer = volta com parte do que juntou
```

- **Loop curto (arena, 5 a 10 min):** ondas, abates, coletar, decidir se sai agora ou arrisca mais uma onda.
- **Loop médio (cidade, 1 a 3 min):** gastar o que trouxe. Meta: toda volta da arena compra pelo menos uma coisa.
- **Loop longo (horas):** setores novos, armas novas, prédios reformados, moradores, contratos, recordes.

Regra de ouro (da pesquisa): **nenhuma corrida é perdida.** Mesmo morrendo você volta com algo.

---

## 3. A cidade (400 x 400 m)

### 3.1 Tamanho e deslocamento
- 400 x 400 m de área jogável dentro da muralha. A pé correndo (~5 m/s): de ponta a ponta ~80 s. De bicicleta (~9 m/s): ~45 s. Moto elétrica (~16 m/s): ~25 s.
- **Tudo que é usado a cada volta fica a no máximo ~120 m da praça** (25 s a pé). O resto da cidade é para explorar, segredos, ruínas que abrem com o progresso.
- Anel viário de 10 m de largura a ~150 m do centro e 4 avenidas em cruz: bom para pedalar.
- Ponto de chegada da arena é **na praça**, ao lado do portão, para não andar à toa.
- Opcional (decidir depois): ponto de ônibus/teleporte entre a praça e cada bairro, liberado com progresso.

### 3.2 Bairros (rascunho, ver o PNG)
| Lugar | Onde | Função |
|---|---|---|
| Praça central | centro | começo do jogo, monumento (nave de resgate restaurada aos poucos), quadro de recordes |
| Portão da Arena | norte, na muralha | escolher setor e nível, sair para a arena |
| Rádio / Contratos | ao lado do portão | contratos (missões), mensagens de resgate, história |
| Rua comercial | leste | Armeiro, Mercado, Bar |
| Oficinas | oeste | Garagem (veículo), Bancada (melhoria de armas) |
| Residencial | sul | Casa do herói, Clínica, casas dos moradores resgatados |
| Laboratório | nordeste | pesquisa com cristais (árvore de melhorias permanentes) |
| Armazém | sudeste | produção passiva dos moradores, estoque |
| Prefeitura | sudoeste | reformar a cidade (abrir ruínas, melhorar prédios) |
| Ruínas | espalhadas | áreas fechadas que abrem com progresso (lugares novos para explorar) |

### 3.3 O que tem em volta (para não ficar "zoado")
O problema: 400 x 400 m, e depois? A proposta é contar isso com a própria história, sem parede invisível no meio do nada:

1. **Muralha da colônia** (8 a 12 m) com torres, andaimes, holofotes, portões fechados. Em cima, um **campo de força** em cúpula bem leve (brilho quando chega perto). É o limite físico e faz sentido no mundo: lá fora tem zumbi.
2. **Do alto da muralha (escadas em 2 ou 3 torres) dá para ver o vale**: é o terreno de 2 x 2 km do L01 que já existe, reaproveitado como paisagem (não jogável), com zumbis vagando ao longe, a nave caída, a colmeia, a floresta alienígena e os planetas no céu. Isso vende o mundo grande sem precisar jogar nele.
3. **Um lado com penhasco e rio tóxico** (já existe no L01) para variar a borda.
4. A cidade fica num **platô** um pouco acima do vale: a muralha esconde o chão de perto e o horizonte fica bonito.
5. Técnico: o vale vira uma malha de fundo barata (HLOD/impostores, sem colisão, sem IA real; zumbis lá fora são silhuetas animadas simples). A borda tem colisão na muralha e uma parede extra só por segurança.

A pesquisa mostra que os jogos misturam tipos de borda (água, penhasco, montanha, campo de força, cercas e prédios) e que o pior é deixar algo interessante do outro lado sem dar acesso (seção 13). Aqui o "lado de fora" é exatamente para onde a arena leva você.

### 3.4 Reaproveitar o que já existe
| Já existe (L01) | Vira na cidade |
|---|---|
| Loja de conveniência do posto (10 x 14 m, balcão, gôndolas) | **Armeiro** (balcão = conversa e compra; gôndolas viram expositores de armas) |
| Escritório do posto (sala trancada) | **Prefeitura** (mesa do prefeito, mapa da cidade na parede) |
| Oficina da estrada (12 x 10 m, portão de 4 m, elevador de carro) | **Garagem** (bicicleta/moto, melhorias do veículo) |
| Oficina/cabana da vila (bancada de ferramentas) | **Bancada** de melhoria de armas (o "Pack-a-Punch") |
| Cabana do pesquisador (cristais brilhando) | **Laboratório** (pesquisa com cristais) |
| Galpão de abrigo (14 x 10 m, estantes) | **Armazém** (produção dos moradores) |
| Casa da vila (sala, cozinha, quarto) | **Casa do herói** (salvar, trocar roupa/personagem, troféus) |
| Casa saqueada | **Clínica** (vida máxima, consumíveis) depois de reformada |
| Cabine da torre de rádio | **Rádio / Contratos** |
| Contêiner do acampamento | **Mercado** de rua (consumíveis) ou caixa de entrega |
| Portas AJRDoor, 133 móveis, câmera de interior (AJRCameraZone) | continuam iguais |
| Nave caída, abertura do jogo (AJRIntroDirector) | abertura: a nave cai perto da colônia, você chega ao portão (história) |
| Terreno 2 x 2 km, vegetação, marcos | paisagem fora da muralha **e** temas das arenas |
| Zumbis, Diretor de IA, Horda, armas, roda de itens, HUD, game feel | arena (quase tudo serve) |

"Retrabalhar": as construções foram feitas para um vale rural. Na cidade elas ganham fachada nova (letreiro, toldo, iluminação, vitrine), um NPC dentro e algo que mostra a função (expositor de armas, bancada acesa). Ver seção 10 sobre o que precisa de modelo bom.

### 3.5 Mapa, navegação e marcadores (Q14)
A cidade não pode virar "andar procurando a loja". Três camadas, reaproveitando o minimapa v4, a bússola e os pinos que já existem:

**Na cidade**
1. **Minimapa** no canto com o ícone de cada prédio (ícones do Forge 2D, um por função) e o herói no centro.
2. **Ponto de exclamação** em cima do prédio e no minimapa quando tem novidade lá: arma nova à venda, melhoria que você já pode pagar, contrato concluído para entregar, morador novo chegou. É o que diz "vá ali agora".
3. **Mapa grande (tecla M)**: a cidade inteira de cima, com os prédios nomeados, as ruínas fechadas (com o custo para abrir) e as estações de **tubo de transporte**. Clicar num prédio marca o caminho (linha no chão + pino na bússola).
4. **Tubo de transporte** (viagem rápida, visual alienígena): 4 a 5 estações, liberadas na Prefeitura. A pé, bicicleta ou tubo: o jogador escolhe.
5. **Placas e letreiros** (Forge 2D, em escrita alienígena com ícone grande) na frente de cada prédio: dá para se achar sem mapa.
6. Ao **voltar da arena** você aparece na praça e o HUD mostra por 5 s "você pode comprar: X na Bancada" com a seta.

**Na arena**
1. Minimapa com: extração, objetivo, sobrevivente, santuários, baús já vistos.
2. **Setas na borda da tela** de onde vem a próxima leva de zumbis (o diretor sabe; ajuda a ler o combate).
3. Barra de energia (nível da corrida) e barra da onda.
4. "Se morrer agora: fica com X" sempre visível perto do dinheiro da corrida (ver 7.5).

---

## 4. Prédios com função (cada um é uma pessoa + um sistema)

Comprar é **conversar com alguém**, não abrir um menu solto: você chega no balcão, aperta E, a câmera de interação (já existe) enquadra o vendedor, ele fala uma frase e abre uma lista simples ao lado dele.

Todos os vendedores são **alienígenas de espécies diferentes** (fichas completas para gerar em `ALIENIGENAS_NPC.md`).

| Prédio | NPC (espécie) | O que faz | Moeda |
|---|---|---|---|
| Armeiro | Krug (Torvak, 4 braços) | compra armas novas, munição extra, **equipamentos de risco** (7.5) | créditos |
| Bancada | Ix-Vel (Kitrin, insetoide) | melhora a arma que você tem: dano, pente, recarga, cadência, efeito especial no nível máximo | créditos + sucata |
| Laboratório | Dra. Oorra (Medusiana, flutua) | árvore de pesquisa permanente (vida, velocidade, sorte, ímã, mais dinheiro, **seguro**, cartas novas para a arena) | cristais |
| Clínica | Sêmea (Florani, planta) | vida máxima, cura melhor, bandagens e kits para levar | créditos |
| Mercado | Tuk (Pelúcio) | consumíveis (bandagem, kit, Fúria, granada) | créditos |
| Garagem | Brumm (Rochoso) | bicicleta, depois moto elétrica, melhorias e cores | créditos + sucata |
| Rádio | Lia-7 (Sintética) | contratos (missões), avisa de sobreviventes para resgatar, modos novos | dá recompensas |
| Prefeitura | Prefeito Glub (Anfíbio) | reformar prédios, abrir ruínas, estações de tubo | sucata + créditos |
| Armazém | Mmb (Gelatinoso) | produção dos moradores a cada volta da arena | gera créditos/sucata |
| Bar | Zé Seis-Braços (Polvoide) | conversa, dicas, comentários sobre a última corrida (estilo Hades) | nada |
| Casa do herói | Bip (robô) | salvar, trocar personagem e skin, troféus, cama (passa o dia) | nada |
| Portão | Kaar (Avari) | escolhe modo, setor e nível; mostra ameaça e recompensa | nada |

Os **sobreviventes resgatados** viram moradores: cada um aparece andando na cidade, vai trabalhar num prédio e libera algo (um vendedor novo, um item novo na loja, produção no armazém). Isso mantém o tema "Jogo de Resgate" e dá o crescimento visual da cidade, que é o que segura o jogador em BALL x PIT e Hades.

---

## 5. Locomoção: bicicleta primeiro, moto elétrica depois

Decidido: **começar com bicicleta** e liberar a **moto elétrica na Garagem** como recompensa grande (é progresso incremental que você sente no corpo). As duas com visual alienígena: bicicleta "Casulo" (quadro de quitina, rodas sem raio com brilho) e moto "Arraia" (formato de arraia, linhas de luz). Fichas para gerar em `ALIENIGENAS_NPC.md`. Até chegar o modelo, uso um genérico.

| | Bicicleta | Moto elétrica |
|---|---|---|
| Velocidade | ~9 m/s (32 km/h) | ~16 m/s (58 km/h) |
| Libera | início | Garagem, depois de X setores |
| Melhorias | velocidade, pulo, cor | velocidade, turbo (o nitro atual), bateria, cor |
| Som | corrente, campainha | zumbido elétrico |

**Técnica (importante):** a pesquisa mostra que veículo de 2 rodas no Chaos Vehicles é problemático: um desenvolvedor contou que perdeu dois ou três meses tentando antes de escrever o próprio sistema, e no fórum da Epic a solução comum é um carro de 4 rodas invisível com a bicicleta por cima. Proposta: **4 rodas invisíveis estreitas (reaproveitando o `AJRVehiclePawn` e o tuning do buggy) + bicicleta visual que inclina nas curvas**. Na cidade não tem combate nem rampas loucas, então o "andar de verdade" de 2 rodas não compensa o custo. Entrar e sair com E já existe.

O que sai do carro atual: gasolina, zumbi agarrando o carro, dano/explosão do carro, bomba no carro. O que fica: entrar/sair, câmera, nitro (vira turbo da moto), HUD de velocidade.

Na arena não tem veículo (decisão aberta: talvez em setores grandes no futuro).

---

## 6. A arena procedural

### 6.1 O que é
- Um **nível separado** (carregado ao sair pelo portão), montado na hora a partir de um **kit de peças** e de uma **semente** (seed). Mesmo setor, nível diferente, montagem diferente.
- Tamanho 80 x 80 a 160 x 160 m (cresce com o nível). Duração alvo 5 a 10 min.
- Temas reaproveitam o L01: **Posto abandonado**, **Floresta alienígena**, **Ponte/colmeia**, **Vila em ruína**, **Base de pesquisa** (cada tema = um "setor").

### 6.2 Como monta (gerador em camadas)
1. **Forma:** escolhe um molde (círculo, cruz, "U", dois pátios ligados, rua com becos) e uma grade de células de 8 m.
2. **Bloqueio:** marca células como livre, cobertura baixa, cobertura alta, parede, buraco/perigo, seguindo regras: sempre existe caminho entre todos os pontos, nenhuma área fechada, linhas de visão longas limitadas, pelo menos 3 rotas de fuga do centro.
3. **Peças:** troca cada célula por peças do kit do tema (carro destruído, barricada, contêiner, árvore, cristal, mureta) com giro e variação.
4. **Pontos de surgimento:** anel de pontos fora da visão do jogador, longe o bastante (o `MinSpawnDistance` atual já faz isso).
5. **Interativos:** baús (pagos e grátis), caixotes de sucata, **santuários** (modificadores estilo Megabonk: "mais zumbis, mais dinheiro", "ímã", "chefe agora"), sobrevivente preso (objetivo opcional).
6. **Conferência automática** antes de abrir: navmesh ligado, todos os objetivos alcançáveis, nada sobreposto (o registro anti-sobreposição A-062 serve aqui).

### 6.3 Diretor por "créditos" (estilo Risk of Rain 2)
O `AJRAIDirector`/`AJRHordeDirector` atual vira um diretor com orçamento: ele ganha pontos com o tempo (mais rápido em níveis altos) e gasta para criar grupos. Cada inimigo tem um custo; o diretor evita gastar com coisa barata demais quando está rico (vira elite). Isso dá curva de tensão sozinha e aproveita o que já existe.

| Inimigo (atual ou novo) | Custo | Observação |
|---|---|---|
| Zumbi comum (ZombieMelee) | 1 | |
| Corredor | 2 | |
| Cuspidor/arqueiro (ZombieArcher) | 3 | |
| Atirador (ZombieGunner) | 4 | |
| Tanque | 8 | |
| Elite (ZombieElite, ou qualquer um com aura) | x 6 | |
| Chefe do setor | 100 | a cada 5 níveis |

### 6.4 Objetivos (sorteados por arena)
Sobreviver X minutos; matar N; **resgatar o sobrevivente** (achar, soltar, escoltar até a saída; usa o `AJRRescueTarget` e o sobrevivente que segue); coletar cristais e levar ao ponto de extração; defender um gerador; chefe.

### 6.5 Fim da corrida (modo principal, sem tempo)
- As ondas não acabam: cada onda é mais forte que a anterior. Você fica **até querer sair ou morrer** (Q5).
- **Sair:** a cada 3 ondas abre uma **nave de extração** por 30 s num ponto do mapa. Chegou nela, sai com tudo. Não quis, ela vai embora e o **multiplicador de recompensa sobe** (x1,0 nas ondas 1 a 3, x1,25 nas 4 a 6, x1,5 nas 7 a 9, e assim por diante). É a decisão "levar o que tenho ou arriscar mais".
- **Morrer:** ver o contrato de morte em 7.5.
- **Relatório:** ondas, abates, combo máximo, dano recebido, nível da corrida, créditos, recorde do setor.

### 6.6 Poder temporário dentro da arena, estilo Archero (Q3)
Como funciona no Archero: ao subir de nível dentro do capítulo você escolhe uma habilidade entre 3, e ela só vale naquele capítulo; morrendo, perde essas habilidades temporárias. Aqui:

1. Zumbi morto solta **energia** (orbezinha que voa até você; o ímã da pesquisa aumenta o alcance). Energia por zumbi = custo dele no diretor (comum 1, tanque 8...).
2. Encheu a barra, **sobe de nível da corrida**: o tempo fica lento (0,2x) e aparecem **3 cartas**. Escolhe 1. Volta o tempo.
3. Energia para o próximo nível: **20 x 1,17^(nível-1)** (nível 1: 20; nível 5: 37; nível 10: 82). Com o orçamento do diretor da seção 6.3 isso dá **mais ou menos 1 nível por onda até a onda 10** e depois fica mais lento (conferido com conta: nível 10 na onda 10, nível 16 na onda 20).
4. **Tudo isso some no fim da corrida** (saindo ou morrendo). O poder permanente é o da cidade.
5. A cada 5 ondas aparece um **mercador misterioso** (alienígena encapuzado) com uma oferta arriscada: "perde 20% da vida máxima e ganha +40% de dano", ou "carta lendária por 30% dos créditos da corrida". Igual ao anjo e ao demônio do Archero.
6. Laboratório libera: **trocar cartas** (1 por corrida), **banir** uma carta, **começar já no nível 2**, cartas novas no baralho.

Cartas (primeira lista, ~30 na v1, com raridade comum, rara, épica):
| Tipo | Exemplos |
|---|---|
| Atributo | +15% dano; +15% cadência; +20% velocidade; +25% vida máxima; +1 tiro por rajada |
| Tiro | tiro atravessa 1 inimigo; ricochete; tiro dividido em 2 no impacto; chance de crítico |
| Elemento | tiro incendeia; choque que pula para 2 vizinhos; gelo que deixa lento |
| Sobrevivência | cura 2% ao matar; escudo que recarrega; revive 1 vez (épica, rara de aparecer) |
| Economia | +30% créditos nesta corrida; ímã gigante; baú grátis a cada 5 ondas |
| Companheiro | drone que atira; torreta no chão a cada 30 s |
| Combinação | "dano + incêndio" vira "explosão de chamas" se tiver as duas (as combinações são o que dá vontade de jogar de novo) |

### 6.7 Modos (Q5)
Para não ficar um modo só. Vão abrindo pelo Rádio conforme você joga:

| Modo | Como é | Tempo | Para que serve |
|---|---|---|---|
| **Sobrevivência** (principal) | ondas sem fim, extração a cada 3 ondas | sem tempo | progresso, dinheiro |
| **Caçada** | mate o máximo em 5 minutos | 5 min | recorde, pontuação, ranking local por setor |
| **Resgate** | ache e escolte 1 a 3 sobreviventes até a extração enquanto as ondas vêm | sem tempo | moradores novos para a cidade |
| **Expedição** | mapa maior, 3 objetivos em sequência e chefe no fim | ~15 min | abre o próximo setor, cristais |
| **Desafio do dia** | semente fixa do dia (mesmo mapa e mesmas regras o dia todo) e um modificador maluco ("só escopeta", "zumbis rápidos") | 5 a 10 min | recompensa extra 1 vez por dia, variedade |
| **Lua Vermelha** (noite) | sobrevivência com elites desde a onda 1 | sem tempo | mais risco, mais cristais |

"Desafio do dia" usa a data do relógio do computador só para a semente, sem nada rodando com o jogo fechado (Q6).

---

## 7. Economia

### 7.1 Moedas (só 3, de propósito)
| Moeda | Vem de | Serve para |
|---|---|---|
| **Créditos** (dinheiro) | abates, baús, fim da corrida, armazém | armas, munição, consumíveis, Bancada, Clínica |
| **Sucata** | caixotes na arena, carros destruídos, armazém | Bancada (junto com créditos), Garagem, Prefeitura |
| **Cristais** | elites, chefes, contratos, santuários | Laboratório (pesquisa permanente) |

Mais uma "não moeda": **moradores** (sobreviventes resgatados). Não se gasta; abre coisas e produz.

### 7.2 Fórmulas (proposta inicial)
Padrão dos incrementais: **custo cresce exponencial, poder cresce devagar**. A fórmula clássica é custo_próximo = custo_base x taxa^quantidade.

| O quê | Fórmula | Exemplo |
|---|---|---|
| Nível da Bancada (dano +10%) | 300 x 1,17^nível (o nível conta junto das armas anteriores) | nível 1: 351, nível 10: 1.442 |
| Armas | preço fixo por arma | Escopeta 2.000; Rifle 8.000; Rifle de precisão 28.000; Lança-plasma 90.000 |
| Vida do zumbi comum no nível L | 60 x 1,14^(L-1) | L1: 60; L10: 195; L20: 723 |
| Créditos por zumbi comum | 6 x 1,11^(L-1) | L1: 6; L10: 15; L20: 44 |
| Orçamento do diretor por corrida | 160 x (1 + 0,22 x (L-1)) pontos | L1: 160; L10: 477; L20: 829 |
| Bônus de fim de corrida | 120 x L | |
| Laboratório (cada nó) | 5 x 1,5^nós já comprados (cristais) | |

### 7.3 O que a simulação mostrou (`tools/design/sim_economia.py`)
Simulação de um jogador que compra sempre o melhor que pode (bancada até 3 antes de trocar de arma):

| Corrida | Nível da arena | Arma | Minutos de combate | Ganho na corrida |
|---|---|---|---|---|
| 2 | 1 | Pistola (bancada 5) | 2,5 | 1.193 |
| 4 | 3 | **Escopeta** | 3,6 | 2.264 |
| 9 | 8 | **Rifle** | 5,2 | 6.618 |
| 17 | 15 | **Rifle de precisão** | 8,9 | 20.669 |
| 33 | 20 | **Lança-plasma** | 9,5 | 42.768 |
| 40+ | 21 a 25 | Lança-plasma | ~8,5 | começa a moer (1 compra a cada 3 corridas) |

Leitura: com só créditos e bancada, o conteúdo dura ~33 corridas (~4 a 5 h de combate) com tempo de abate entre 0,5 e 0,9 s por zumbi comum (bom para tiro em 3ª pessoa). Depois disso falta o que comprar. Por isso as outras moedas (cristais, sucata, moradores) e os contratos existem: são o que segura a partir da 5ª hora. A simulação ignora consumíveis, Laboratório e morte; é só ordem de grandeza.

### 7.4 Pontuação (separada do dinheiro)
- Pontos por abate x **combo** (abates seguidos sem levar dano aumentam o multiplicador; o game feel já tem hit-stop e feedback).
- Bônus: sem dano, tiro na cabeça, tempo, objetivo opcional.
- Serve para **recorde por setor** (quadro na praça) e para contratos ("faça 50.000 pontos no setor 2"). Não vira dinheiro, para não confundir.

### 7.5 O que se perde ao morrer: o "contrato de morte" (Q4)
O que a pesquisa diz: jogador odeia sentir que perdeu progresso; o roguelite moderno separa **o que é da corrida** (some ao morrer) do **que é permanente** (fica sempre). E a punição tem que ser **clara e escolhida**: perder tudo sem ter entendido o risco parece um soco. Por isso a regra aqui é simples, sempre mostrada na tela, e o risco maior é opcional.

**Nunca se perde (permanente):** armas compradas, níveis da Bancada, pesquisa do Laboratório, prédios reformados, moradores, contratos, recordes.

**Sempre some ao fim da corrida (morrendo ou saindo):** cartas e nível da corrida (6.6), consumíveis gastos.

**Ao morrer:**
| O que você carrega | Saindo pela extração | Morrendo |
|---|---|---|
| Créditos e sucata da corrida | 100% x multiplicador | **40%** (o Laboratório sobe até 70% com o nó "Seguro") |
| Cristais da corrida | 100% | **0%** (cristal é o prêmio de quem arrisca e sai) |
| Energia da corrida | vira **experiência de conta** | vira experiência de conta (nunca perde) |
| **Equipamento de risco** que você levou | volta com você | **perde**, a não ser que tenha pago o seguro |

**Equipamento de risco (a sua ideia de "perder um equipamento que levou"):**
- O Armeiro e a Bancada vendem **módulos** que você encaixa antes de sair: mira laser (+precisão), carregador estendido, implante de vida, amuleto de sorte. São fortes e opcionais.
- Morreu com eles, **perdeu**. Saiu, continuam seus.
- Antes de sair pelo Portão, o guarda oferece **seguro** de cada módulo (25% do preço). Com seguro, volta mesmo morrendo.
- Assim quem quer jogar seguro nunca perde nada permanente, e quem quer arriscar ganha poder extra com algo em jogo. É a ideia do seguro dos jogos de extração (Tarkov e parecidos), só que leve.

**Experiência de conta** (Hades: toda morte rende algo): a energia de toda corrida soma na sua conta e, a cada nível de conta, libera algo (carta nova no baralho, desconto, cosmético). Nenhuma corrida termina com zero.

**Na tela:** perto do dinheiro da corrida fica sempre "se morrer: fica com X". No relatório de morte aparece o que voltou e o que ficou, sem surpresa.

---

## 8. Progressão do personagem

Duas camadas, para não brigar com as armas:
1. **Laboratório (permanente, cristais):** árvore visível estilo Nodebuster com ~30 nós em 4 ramos: Sobrevivência (vida, armadura, cura), Mobilidade (velocidade, estamina, esquiva), Fortuna (sorte nos baús, ímã, mais créditos) e Tecnologia (habilidade ativa nova, segunda arma no cinto, drone).
2. **Contratos (Rádio):** 3 ativos de cada vez, trocam ao completar. Liberam conteúdo (arma nova no Armeiro, santuário novo, setor novo, skin). Megabonk usa 240 missões assim para dar sempre "um próximo objetivo".

Personagens jogáveis (Hero01, Hero02) têm bônus pequenos diferentes (Q10): um com +10% vida, outro com +10% velocidade.

### 8.1 Jogo infinito (Q8)
Sem final de história. O que mantém o jogador indo atrás de algo:
- **Setores com camadas**: cada setor tem níveis infinitos; a cada 5 níveis um chefe, a cada 25 uma "camada" nova com visual mais escuro e inimigos novos (alienígenas infectados das espécies da cidade).
- **Restaurar a nave** na praça em etapas (monumento que muda), sem que isso "termine" o jogo: cada etapa libera uma função nova (ex.: radar que mostra baús na arena).
- **Nível da cidade** (soma de prédios reformados e moradores) com metas visíveis no mapa.
- **Recordes** por setor e por modo, desafio do dia.
- Se a progressão travar depois de muitas horas, aí sim pensar em prestígio (Q7, fora da v1).

---

## 9. O que muda no projeto (técnico)

### 9.1 Fica
Personagem e combate (`JRCharacter`, `JRWeaponComponent`, `JRWeaponDefinition` já é por dados), zumbis e IA, Diretor e Horda (viram base do diretor por créditos), roda de itens, HUD, game feel, áudio, portas, baús, interiores, câmera de interação, abertura, save com migração.

### 9.2 Sai ou fica guardado
Estrutura de zonas e checkpoints do L01, tarefas da fase (`l01_tasks.py`), gasolina, carro agarrado por zumbi, bomba no carro, sobrevivente sentando no buggy. O mapa L01 vira: paisagem fora da muralha + fonte de peças das arenas. Nada é apagado; fica em `Levels/_Arquivo`.

### 9.3 Novo (C++, prefixo JR)
| Sistema | O que faz |
|---|---|
| `UJREconomySubsystem` | créditos, sucata, cristais, moradores; ganhar, gastar, eventos para o HUD |
| `UJRUpgradeSubsystem` + DataTable | níveis da bancada, Laboratório, Clínica, Garagem; fórmulas da seção 7 em dados |
| `AJRShopkeeper` + `UJRShopWidget` | NPC com balcão, fala curta, lista de compra ao lado (usa `JRInteractable` e a câmera de interação) |
| `AJRCityGate` + tela do portão | escolher setor e nível, mostrar ameaça e recompensa, viajar |
| `UJRRunSubsystem` | estado da corrida: semente, nível, objetivo, ganhos, multiplicador, relatório, morte |
| `AJRArenaGenerator` | gerador da seção 6.2 (semente -> células -> peças -> pontos -> conferência) |
| `AJRArenaDirector` | diretor por créditos (estende o atual) |
| `AJRShrine` | santuários modificadores |
| `AJRBikePawn` | bicicleta/moto (4 rodas invisíveis + visual que inclina) |
| `UJRContractSubsystem` | contratos do Rádio |
| `UJRCitySubsystem` | estado da cidade: prédios reformados, ruínas abertas, moradores e onde trabalham |
| `UJRRunBuildComponent` + DataTable de cartas | energia, nível da corrida, sorteio de 3 cartas, efeitos temporários, combinações, mercador misterioso (6.6) |
| `AJRExtractionShip` | nave de extração a cada 3 ondas, multiplicador (6.5) |
| `UJRLoadoutComponent` | módulos de risco, seguro, o que volta ao morrer (7.5) |
| `UJRAccountSubsystem` | experiência de conta e o que cada nível libera |
| `UJRModeDefinition` (Data Asset) | modos de arena (6.7): regras, tempo, recompensas, semente do dia |
| `UJRCityMapWidget` + `AJRTransitTube` | mapa grande, marcar caminho, exclamações, tubos de transporte (3.5) |
| Save v3 + migração | moedas, armas compradas, níveis, pesquisa, cidade, moradores, contratos, módulos e seguro, conta, recordes |

### 9.4 Níveis (mapas)
- `L_Cidade` (400 x 400, umap único, sem World Partition; HLOD para o vale de fundo).
- `L_Arena_Base` (vazio, só luz/céu por tema) + o gerador monta em tempo de execução.
- Viagem: `OpenLevel` com tela de carregamento curta (ou streaming se der para manter a cidade carregada; decidir no protótipo).

---

## 10. Arte: o que pode ser low poly e o que precisa de modelo bom

Regra: **o que o jogador olha de perto e toca precisa estar no nível do herói**. Low poly (Forge 3D) só onde ninguém fica encarando.

| Categoria | Qualidade | Quem faz |
|---|---|---|
| Herói, zumbis | atual (bom) | já existe |
| **Vendedores alienígenas (12) e moradores** | **bom** | **você gera a partir das fichas em `ALIENIGENAS_NPC.md`; eu faço rig, escala e animação** |
| **Bicicleta "Casulo" e moto "Arraia"** | **bom** | **você gera (fichas no mesmo arquivo); eu uso um genérico até lá** |
| Inimigos alienígenas infectados (depois) | bom | versão infectada dos alienígenas da cidade (mesmo modelo, outro material) |
| **Fachadas dos prédios com função** | **bom** | você gera uma referência de estilo; eu retrabalho as construções existentes em cima dela |
| Muralha, torres, portão da arena, monumento da praça | bom | você gera referência; eu modulo em peças |
| Armas na mão (5) | bom | você gera; Forge 3D pode fazer rascunho para testar tamanho |
| Móveis dos interiores | médio | já existem 133 |
| Props de fundo (caixote, barril, lixo, placa, entulho, cone) | low poly ok | **Forge 3D** |
| Kit das arenas (barricada, mureta, contêiner, carro destruído) | médio | Forge 3D com textura lisa, **depois de você aprovar 1 amostra** |
| Pickups (moeda, cristal, sucata), santuários | low poly ok (estilizado brilha bem) | Forge 3D |
| HUD, ícones de loja, moedas, árvore do Laboratório, letreiros das lojas, cartazes | 2D | **Forge 2D** |
| Efeitos (fogo, fumaça, faísca de compra) | 2D animado | Forge 2D |
| Vale de fundo | paisagem | já existe (L01) |

**Lista do que eu preciso que você gere (em ordem; textos prontos em `ALIENIGENAS_NPC.md`):**
1. Uma imagem de referência do estilo da cidade (rua com 2 ou 3 fachadas). Com isso eu decido o resto.
2. Krug (Armeiro), Ix-Vel (Bancada) e Kaar (Guarda do Portão): são os 3 do protótipo.
3. Bicicleta "Casulo".
4. Portão da arena e um pedaço de muralha.
5. Os outros vendedores e a moto "Arraia", conforme os prédios forem entrando.

---

## 11. Plano de etapas

| Etapa | Entrega | Pronto quando |
|---|---|---|
| **F0** | Este documento (v0.2) aprovado + perguntas da seção 12 | você aprova |
| **F1 Protótipo cinza do loop** | cidade cinza 400 x 400 com praça, Armeiro, Bancada, Portão (NPCs em cápsula até chegarem os modelos); arena fixa simples com ondas sem fim, extração a cada 3 ondas, energia e 3 cartas por nível; créditos; comprar 1 arma e 1 melhoria; save | você joga 3 voltas seguidas sem bug |
| **F2 Arena procedural v1** | gerador com 1 tema (Posto abandonado), diretor por créditos, 2 objetivos, relatório, contrato de morte (7.5) | 10 sementes seguidas sem arena quebrada |
| **F3 Economia completa** | 3 moedas, Laboratório, Clínica, Mercado, contratos, módulos de risco e seguro, experiência de conta, mapa grande | simulação + 1 h de teste seu |
| **F4 Bicicleta** | AJRBikePawn com genérico; moto na Garagem | cruzar a cidade sem capotar |
| **F5 Cidade com arte** | prédios retrabalhados com NPCs, muralha, vale de fundo, ruínas | prints aprovados |
| **F6 Conteúdo** | 3 setores, 5 armas, ~30 cartas, chefes, santuários, moradores, modos Caçada e Resgate | |
| **F7 Balanceamento e polimento** | ajustar curvas com dados reais de teste; modos Expedição, Desafio do dia, Lua Vermelha | |

F1 é o mais importante: prova se o loop é divertido antes de gastar com arte.

### 11.1 F1 em andamento (2026-11-18)
Código pronto, ainda não compilado (A-080). Como testar:
1. Feche a Unreal e rode `E:\game\compilar_remap.bat` (log em `E:\game\_compilar_log.txt`).
2. Abra a Unreal e, na caixa Cmd (modo Python): `py "E:/game/utrazin-game/tools/unreal/build_remap_f1.py"`.
3. Com `L_Cidade` aberto, Play. Fale com Kaar (E) e escolha "Arena nível 1".
4. Na arena: sobreviva, escolha cartas (1/2/3), entre no círculo da nave quando ela aparecer (a cada 3 ondas) ou arrisque mais.
5. De volta à cidade: relatório, compre a escopeta com Krug (2.000) e calibre na Ix-Vel. Atalho de teste: console `JRCreditos 5000`.
Pronto quando: 3 voltas seguidas sem bug.

Anotado no teste de 18/11 (fazer depois que o combate estiver ok):
- Zumbi com brilho (contorno/emissivo leve) para enxergar no escuro da arena.
- HUD de interação e da loja feia (é cinza de propósito; refazer no estilo do HUD v2).
- Som da escopeta ruim (retrabalho de áudio).
- Vila e arena com arte de verdade (hoje são blocos).
- Zumbi andando "duro/deslizando": a animação não acompanha o movimento. Primeira tentativa (bUseAccelerationForPaths) fez eles pararem; desfeita.

### 11.2 F2 em andamento (2026-11-18): arena procedural v1
Código pronto, ainda não compilado (A-084). O que tem:
- **Planta** (`FJRArenaLayout`, lógica pura com teste): grade de células de 8 m, 10 células (80 m) no nível 1 e +1 por nível até 20 (160 m). Molde sorteado entre círculo, cruz, U, dois pátios e rua com becos. Centro 3 x 3 sempre livre e saídas nos 4 lados. Bloqueio: primeiro quebra as linhas de visão retas maiores que 64 m com cobertura alta, depois grupos de cobertura (sozinha, linha de 2 ou 3, "L"), sempre com um corredor de 8 m entre grupos. Conferência: tudo alcançável a partir do centro (flood fill), nenhuma área fechada, nenhuma visão reta maior que 8 células, 3+ saídas do centro, 6+ pontos de surgimento, 2+ pontos da nave, 3+ pontos de objetivo. Falhou, tenta outra semente (até 12; último recurso: círculo sem cobertura extra). No teste fora da engine: 2.000 plantas, 0 quebradas, 98% na primeira semente.
- **Peças** (`AJRArenaGenerator`, tema "Posto abandonado", só malhas que já existem): muro com contêineres, ônibus, caminhão, muro do L01; coberturas altas com carros batidos do usuário, SM_CarWreck, contêineres, picape; baixas com barricadas, bloqueios, barris/caixas/pneus/gerador em grupinhos; enfeites (sacos de lixo, ossos, placas); marco do posto (cobertura com 2 bombas e a loja); postes com luz no muro. Visual em malhas instanciadas sem colisão; colisão em caixas simples invisíveis do tamanho de cada peça (entram na navmesh dinâmica). Muro: caixas de 6 m na borda. Cada peça cabe na sua célula, então nada se sobrepõe (e o gerador confere).
- **Diretor por créditos**: orçamento por onda (8 + 3W) x (1 + 0,12 (L-1)), renda (1,2 + 0,12W) x (1 + 0,15 (L-1)) pontos/s, carteira inicial 35%. Compra grupos: comum 1 (3 a 5), corredor 2 (comum mais rápido, 2 a 4), arqueiro 3, atirador 4, tanque 8; elite = custo x 6, vida x 4, maior e com luz roxa, a partir da onda 4 (mais provável quando o diretor está rico). Ritmo: junta pressão até o pico (6 + 2W), espera a horda cair para 35% e respira 3 s (+2,5 s se o herói estiver com menos de 40% de vida). Surgimento só fora da visão, com rosnado no lugar de onde vêm, poeira e aviso "Horda chegando pela esquerda"; elite com rugido e aviso. Ondas, nave a cada 3 ondas, multiplicador, cartas, energia e créditos como no F1.
- **Objetivos (2 por arena)**: "Sobreviva 3 ondas" (+80 x nível) e um opcional sorteado pela semente (+150 x nível): elite marcado (luz dourada, chega na onda 2), destruir 3 ninhos (os ninhos também viram ponto de surgimento) ou combo de 10 + 2 x nível abates sem levar dano (12 a 30).
- **Relatório**: objetivos cumpridos e maior combo (abates seguidos sem levar dano; zera ao levar dano).
- **Baús grátis**: até 2 por arena (munição 40, vida 25, 1 bandagem, 40 créditos x nível).

Como testar:
1. Feche a Unreal e rode `E:\game\compilar_remap.bat`.
2. Abra a Unreal e, na caixa Cmd (modo Python): `py "E:/game/utrazin-game/tools/unreal/build_remap_f2.py"` (deixa `L_Arena_F1` só com a base). Se o log reclamar da navegação: Build > Build Paths e salve.
3. Play na cidade (Kaar, "Arena nível 1") ou direto na arena. A semente aparece no aviso de entrada e no log (`LogJR`, com o desenho da planta em texto).
4. Para repetir ou trocar: console `jr.Arena.Seed 1234` (0 = sorteia) e `jr.Arena.Shape 0` a `4` (-1 = sorteia), depois `RestartLevel`.
5. Testes: `Automation RunTests JR.Remap` (planta: 500 sementes; regras do diretor) e `python -m pytest tests/python/test_build_remap_f2.py -q`.
Pronto quando: 10 sementes seguidas sem arena quebrada.

---

## 12. Perguntas que ainda faltam

As 20 primeiras foram respondidas (seção 0). Sobraram estas, menores; se não responder, sigo a recomendação.

| # | Pergunta | Recomendação |
|---|---|---|
| Q21 | O herói é **humano** (o único da cidade) como neste doc? | Sim, usa os Hero01/Hero02 que já existem |
| Q22 | Os **zumbis atuais** continuam (são "infectados" de uma espécie) e depois entram alienígenas infectados? | Sim |
| Q23 | Ao subir de nível na arena o **tempo fica lento** (0,2x) para escolher, ou pausa total? | Lento (mantém a tensão) |
| Q24 | Morrendo, ficar com **40%** de créditos e sucata e **0%** de cristais está bom? | Sim, ajustar no teste |
| Q25 | **Módulos de risco com seguro** (7.5) entram já na v1? | Sim, na F3 |
| Q26 | Os NPCs **falam com voz** ou só texto com "som de fala alienígena" (tipo Animal Crossing)? | Texto + som alienígena (barato e combina) |
| Q27 | Escrita das placas: **alienígena com ícone** ou português? | Alienígena com ícone grande; nome em português ao chegar perto |

---

## 13. Pesquisa: o que está dando certo (resumo)

- **Survivors 3D vende muito, mesmo simples.** Megabonk (dev solo, low poly, mapas gerados a cada corrida) passou de 1 milhão de cópias em duas semanas (set/2025), com estimativa de ~1,3 milhão e pico de 117 mil jogadores. Deep Rock Galactic: Survivor ~1,2 milhão. O visual simples não atrapalhou.
- **Corrida curta + cidade entre corridas funciona.** BALL x PIT: corridas de 10 a 15 min e uma cidade em grade onde prédios dão bônus permanentes e liberam heróis. 1 milhão em ~6 semanas, 2 milhões em 10 meses. **Mas** a parte de construir a cidade foi a mais criticada (mover peças é chato). Lição: cidade fixa, progresso por reforma, sem gerenciar grade.
- **Hub com pessoas transforma morte em progresso.** Hades: voltar para casa depois de morrer traz falas novas, melhorias e a casa muda; o hub tem loja, lugar para testar arma e a história. A meta-progressão do Hades separa eixos: o que a corrida começa tendo, a dificuldade opcional (Pacto) e a identidade da arma.
- **Vampire Survivors:** ouro da corrida compra melhorias permanentes entre corridas; o segredo é dar progresso rápido em 15 a 30 min e liberar melhorias aos poucos (pior erro: a primeira melhoria exigir várias vitórias).
- **Brotato:** loja entre ondas com 4 ofertas, rolar de novo custa pouco, preços sobem com as ondas (inflação). Ondas de 20 a 90 s.
- **CoD Zombies:** pontos por abate compram armas na parede, portas, vantagens e a melhoria de arma (Pack-a-Punch por 5.000); preços estáveis e conhecidos ajudam a planejar.
- **Diretor por créditos (Risk of Rain 2):** o diretor junta créditos que crescem com o tempo e gasta em grupos de inimigos, evitando grupos baratos demais quando tem muito crédito.
- **Matemática dos incrementais (Kongregate/AdVenture Capitalist):** custo cresce exponencial e produção cresce linear/polinomial; prestígio cria a sensação de "subir a escada". 
- **Incrementais estão em alta no Steam:** 940 jogos com a etiqueta Idler em 2025 (572 em 2024); 7 dos 50 demos mais jogados de um Next Fest eram incrementais; preço de 10 a 15 dólares teve mais sucesso que abaixo de 5.
- **Bordas de mapa:** jogos combinam água, penhasco, montanha, campo de força, mata fechada, cercas e prédios; evitar parede invisível e não deixar algo interessante do outro lado sem acesso.
- **Moto em UE5:** 2 rodas no Chaos é difícil; relatos de meses perdidos e solução comum de 4 rodas invisíveis.
- **Archero:** a cada nível dentro do capítulo, escolhe 1 entre 3 habilidades que só valem ali; morrendo, perde as habilidades temporárias (de nível, anjos, demônios). Anjo e demônio oferecem trocas entre corridas.
- **Morte em roguelites:** o jogador não quer sentir que perde progresso; o padrão é separar o que é da corrida do que é permanente; punição grande só funciona se for clara e escolhida ("contrato de morte"). Jogos "extração leve" (inspirados em Helldivers e Deep Rock) usam a decisão de guardar o que tem ou arriscar mais.
- **Modos:** Deep Rock Galactic: Survivor ganhou desafios diários, corridas de maestria e mergulhos com anomalias, cada um com modificadores, para dar variedade.

Fontes:
- Megabonk: https://opencritic.com/news/22116 ; https://dataconomy.com/2025/10/08/megabonk-sells-over-one-million-copies-on-steam ; https://www.destructoid.com/reviews/megabonk-review-an-absurd-charming-yet-potent-evolution-of-the-survivors-like-formula/
- BALL x PIT: https://www.gematsu.com/2025/12/ball-x-pit-sales-top-one-million-three-free-content-updates-set-for-2026 ; https://wnhub.io/news/investment/item-51689 ; https://www.aol.com/articles/ball-x-pit-review-003153390.html ; https://bloxodes.com/wiki/ball-x-pit
- Hades: https://saschb2b.github.io/game-mechanics/games/hades/ ; https://saschb2b.github.io/game-mechanics/games/hades/meta-progression ; https://criticalvideogamestudies.com/hades-death-and-the-players-experience/
- Vampire Survivors: https://game-wisdom.com/critical/success-vampire-survivors
- Brotato: https://shapes.inc/fandom/brotato ; https://earlyguides.pages.dev/brotato
- CoD Zombies: https://segmentnext.com/call-of-duty-black-ops-3/mechanics ; https://www.hxchector.com/call-of-duty-black-ops-walkthrough/zombies
- Risk of Rain 2: https://riskofrain2.wiki.gg/wiki/Difficulty
- Matemática idle: https://gamedeveloper.com/design/the-math-of-idle-games-part-i ; https://gamedeveloper.com/design/the-math-of-idle-games-part-iii
- Mercado idle/incremental: https://www.steampageanalyzer.com/niches/idler ; https://pcgamer.com/software/platforms/the-50-most-played-steam-next-fest-demos-include-7-incremental-games-4-ai-disclosures-and-only-one-instance-of-haystack-slop/
- Bordas: https://gamedev.net/forums/topic/659628-map-borders-in-an-open-world-game/5173252/
- Moto UE5: https://80.lv/articles/creating-a-custom-motorcycle-system-for-unreal-engine-5 ; https://forums.unrealengine.com/t/please-help-me-fix-weird-behaviour-of-vehicle/786443
- Dave the Diver: https://www.rpgamer.com/review/dave-the-diver-review/
- Archero (habilidades temporárias ao subir de nível): https://www.supercheats.com/archero/walkthrough/ ; https://theriagames.com/?p=80837 ; https://www.androidauthority.com/archero-guide-heroes-abilities-1086651
- Punição e morte em roguelites: https://www.gamedeveloper.com/design/how-punishment-systems-hurt-gameplay ; https://www.cloudspress.com/how-roguelite-rpg-runs-progression-and-permadeath-work/ ; https://longform.social/post/did:plc:krsrxc3rujq5r5ko6mjw5y7p/3mm3q6bm4m752 ; https://thegameswiki.com/blight-survival/wiki/risk-and-reward/history/8d38f31c-fc2b-4adf-bf5c-8893b22e10f9
- Modos em survivors (Deep Rock Galactic: Survivor): https://egw.news/gaming/news/29828/deep-rock-galactic-survivor-10-review-mining-survi-WcuwdR2Rt

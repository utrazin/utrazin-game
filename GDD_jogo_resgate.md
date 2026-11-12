# GDD: Jogo de Resgate (título provisório)

> Versão 0.4 (rascunho). Documento vivo. Itens marcados com **[DEFINIR]** dependem de decisão. A seção 14 lista as perguntas em aberto.
> Valores provisórios propostos para cada **[DEFINIR]** estão em [`docs/decisions/ASSUMPTIONS.md`](docs/decisions/ASSUMPTIONS.md) e **não foram aprovados**. Este GDD só muda quando o usuário aprovar.

---

## 1. Visão geral

Jogo **single player, offline**, em **terceira pessoa**, com foco em **salvar uma pessoa**. Cada fase tem um trajeto a cumprir: **metade dirigindo um carro, metade a pé**, com combate, obstáculos físicos e uma horda final antes do resgate.

**Pilares**
1. **Física crível** de carro e de personagem (suspensão, amortecimento, dano, terreno irregular).
2. **Duas jogabilidades fortes** (veículo e a pé) com transição fluida entre elas.
3. **Combate com IA legível** (inimigos com comportamento claro por distância e tipo).
4. **Identidade própria**: personagens, carro, armas, fonte, efeitos e animações exclusivos.
5. **Escalável**: novas fases, personagens e skins podem ser adicionados sem refatorar.

---

## 2. Escopo inicial (MVP)

| Item | Quantidade inicial | Expansível |
|---|---|---|
| Fases | 3 (um mapa cada) | Sim |
| Personagens jogáveis | 2 (criados para o jogo) | Sim |
| Skins por personagem | 2 | Sim |
| Armas | 1 (pistola alienígena, exemplo) | Sim |
| Veículos | 1 carro base **[DEFINIR]** | Sim |
| Tipos de inimigo (fase 1) | Zumbi corpo a corpo, zumbi arqueiro, zumbi com pistola | Sim |

---

## 3. Plataforma e requisitos técnicos

- **Offline, single player**, sem servidor.
- **Sem banco de dados**: persistência apenas local/cache (arquivo de save simples, ex.: JSON ou SaveGame da engine).
- Engine e ferramentas: **Unreal Engine + Blender, somente ferramentas e assets gratuitos** **[confirmar]**.
- Plataforma alvo: **[DEFINIR]** (PC? Windows/Linux/Mac?).
- Desempenho alvo: **[DEFINIR]** (FPS mínimo, hardware mínimo).

### 3.1 Persistência (cache local)
Dados salvos localmente:
- Personagem e skin selecionados
- Fase atual e checkpoints alcançados
- Fases desbloqueadas
- Configurações (áudio, vídeo, controles, idioma)
- (Opcional) recordes/estatísticas **[DEFINIR]**

---

## 4. Estrutura de fases

Cada fase contém:
- Um **mapa próprio** (terreno com montanhas, morros, buracos, obstáculos)
- Um **trajeto** com ~50% de carro e ~50% a pé
- **Checkpoint(s)**, com um checkpoint principal na transição carro para a pé
- **Horda final** antes do resgate
- **Cena de resgate** com animação de reencontro (abraço)

### 4.1 Fluxo de uma fase

1. Início da fase: jogador já dentro do carro (cinemática curta opcional)
2. **Trecho de carro**: seguir trajeto, desviar de obstáculos e buracos, enfrentar inimigos à distância
3. **Checkpoint**: fim do trecho de carro, transição para fora do carro (animação de saída)
4. Progresso salvo
5. **Trecho a pé**: combate, exploração do trajeto, mapa/indicador de direção
6. **Horda final** (a mais difícil da fase)
7. **Resgate**: libertar a pessoa presa (grade/cela), animação do abraço
8. Tela de conclusão da fase

### 4.2 Lista de fases (a definir)

| Fase | Tema | Inimigos | Objetivo/Resgate | Ambiente |
|---|---|---|---|---|
| 1 | Zumbis | Zumbis (mão, arco, pistola) | **[DEFINIR]** | **[DEFINIR]** |
| 2 | **[DEFINIR]** | **[DEFINIR]** | **[DEFINIR]** | **[DEFINIR]** |
| 3 | **[DEFINIR]** | **[DEFINIR]** | **[DEFINIR]** | **[DEFINIR]** |

---

## 5. Personagens e skins

- **2 personagens** originais, criados para o jogo (modelagem, rig e animações).
- **2 skins por personagem** (4 variações no total).
- **Seleção e troca**: o jogador escolhe antes de começar e pode trocar depois (menu de personagem), sem perder progresso.
- Diferenças entre os personagens (apenas visual ou também mecânica/atributos): **[DEFINIR]**
- Skins: apenas visuais (cores/roupas/texturas); desbloqueio livre ou por progressão **[DEFINIR]**

### 5.1 Requisitos de arte/animação por personagem
- Modelo 3D + rig humanoide compatível com a engine
- Animações: idle, andar, correr, pular, agachar **[DEFINIR]**, mirar, atirar, recarregar, tomar dano, morrer
- Animações de contexto: entrar/sair do carro, empurrar objeto, abraço (resgate)
- Possibilidade de usar **bibliotecas de animação gratuitas** onde existirem e criar as que faltarem

---

## 6. Jogabilidade: veículo

### 6.1 Física do carro
- Modelo de veículo com **suspensão e amortecimento** por roda
- **Tração, freio, direção, derrapagem** realistas o suficiente para terreno acidentado
- **Terreno íngreme**: subidas, descidas, morros, nunca em linha reta
- **Buracos e obstáculos** que exigem desvio
- **Colisões** com obstáculos físicos (o carro reage; objetos empurráveis/destrutíveis quando fizer sentido na vida real)

### 6.2 Sistema de dano do carro
- **Vida do carro** (barra de integridade)
- **Dano por zonas** **[DEFINIR]** (pneus, motor, lataria, vidros)
- **Pneu estourado**: altera a física (puxa para um lado, mais derrapagem, menos tração)
- Efeitos visuais de dano (fumaça, faíscas, amassados)
- Consequência de destruição total do carro: **[DEFINIR]** (game over, reinício do checkpoint)

### 6.3 Combate durante a condução
- Inimigos atiram (arco/pistola) enquanto o carro se move
- Jogador **desvia** dirigindo; inimigos de frente podem ser atropelados, mas isso causa dano ao carro **[DEFINIR]**
- O jogador pode **atirar de dentro do carro**? **[DEFINIR]**
- Atropelar inimigos: permitido? dano ao carro? **[DEFINIR]**

### 6.4 Transição carro para a pé
- No checkpoint, animação de **sair do carro** (suave, "bonitinha")
- O carro fica estacionado no checkpoint (ou é descartado) **[DEFINIR]**
- Progresso salvo automaticamente

---

## 7. Jogabilidade: a pé

- Controle em terceira pessoa (câmera, mira, movimentação)
- **Física do personagem**: colisão com objetos, **empurrar objetos** quando plausível, ser bloqueado/atingido por obstáculos
- **Armas**: começa com **pistola alienígena** (referência: pistola alienígena do modo zumbi de Black Ops 2; usar design **original**, apenas inspirado)
- Sistema de armas expansível (novas armas depois)
- Sistema de munição, recarga e troca de arma **[DEFINIR]**
- **Vida do personagem**, regeneração/itens de cura **[DEFINIR]**
- **Mapa/minimapa** e indicador de objetivo/trajeto

---

## 8. Inimigos e IA

### 8.1 Tipos (fase 1: zumbis)
| Tipo | Comportamento |
|---|---|
| Corpo a corpo | Persegue e ataca de perto |
| Arqueiro | Mantém distância, atira flechas com antecipação do alvo |
| Atirador (pistola) | Mantém distância, atira em rajadas curtas |

### 8.2 Controle de IA
- **Gatilhos por distância**: o inimigo só ativa/persegue quando o jogador entra em certo raio (aggro radius); fora disso, permanece em idle/patrulha
- **Máquina de estados**: idle, patrulha, alerta, perseguição, ataque, morte
- **Orçamento de inimigos ativos** simultâneos para controlar performance
- **Hordas**: ondas com escalonamento de dificuldade; a **horda final** é a mais difícil da fase
- Reação a veículo (desvio, ataque ao carro, arma de longo alcance)

---

## 9. Mundo, ambiente e otimização

- Terrenos com **montanhas, morros, vales** e elementos de cenário para o mundo não parecer vazio
- **Técnicas de otimização de renderização**:
  - Streaming/carregamento por distância (World Partition ou level streaming)
  - **LOD** (níveis de detalhe) para modelos
  - **Culling** (frustum/oclusão) e HLOD para objetos distantes
  - Instanciamento de vegetação e props
  - Spawn de inimigos por proximidade, não todos de uma vez
- Cenário "preenchido" ao redor do trajeto (props, vegetação, ruínas) sem renderizar tudo
- Iluminação, clima e hora do dia por fase **[DEFINIR]**

---

## 10. Interface (UI/HUD)

- **Fonte personalizada** (uma para o projeto todo ou uma por fase **[DEFINIR]**); licença livre ou criada do zero
- HUD: vida do personagem, vida do carro, munição/arma, **minimapa/mapa**, objetivo atual
- Menus: principal, seleção de personagem/skin, pausa, configurações, seleção de fase
- Telas: game over, checkpoint, fase concluída
- Idioma(s) da interface: **[DEFINIR]**

---

## 11. Áudio e efeitos

- **Efeitos visuais (VFX)**: tiros, impacto, sangue/efeitos de zumbi **[DEFINIR intensidade]**, fumaça do carro, poeira, faíscas
- **Áudio**: motor do carro, pneu estourado, tiros, passos, zumbis, ambiente, trilha sonora por fase
- Fonte de áudio (livre/licenciado/criado): **[DEFINIR]**

---

## 12. Pipeline de produção de assets

| Categoria | Ferramenta | Observação |
|---|---|---|
| Modelagem 3D (personagens, carro, armas) | Blender | Criação própria |
| Rig e animação | Blender + bibliotecas gratuitas | Criar as que faltarem |
| Texturas/imagens | Blender, GIMP, Krita **[confirmar]** | |
| Engine, física, IA, UI | Unreal Engine | |
| Áudio | Audacity, bibliotecas livres **[DEFINIR]** | |
| Fonte | Criar ou escolher livre (OFL) | |

Regras: usar apenas assets com **licença compatível com uso comercial** (caso o jogo seja distribuído) e manter um registro de licenças.

---

## 13. Roadmap sugerido

1. **Pré-produção**: fechar GDD, escolher estilo de arte, repositório e pipeline
2. **Protótipo cinza** (greybox): carro com física boa + personagem a pé + um mapa simples
3. **Vertical slice da Fase 1**: trajeto completo com zumbis, checkpoint, horda final, resgate
4. **Sistemas**: save/cache, seleção de personagem/skin, HUD, mapa
5. **Arte final** dos 2 personagens, carro, pistola, inimigos
6. **Fases 2 e 3**
7. **Polimento**: VFX, áudio, otimização, balanceamento
8. **Testes e build**

---

## 14. Perguntas em aberto (gaps)

### Engine e plataforma
1. Confirma **Unreal Engine** (qual versão) com **Blueprint, C++ ou ambos**?
2. Plataforma alvo (Windows, Mac, Linux) e hardware mínimo?
3. ~~Teclado/mouse, controle ou os dois?~~ **Os dois.**

### Estilo e tom
4. ~~Estilo visual?~~ **Cartunesco**, sem realismo elevado (física continua crível, o visual é que é estilizado).
5. Tom e classificação: gore pesado, mais leve, humor?
6. Referências de jogo (visual e jogabilidade)?

### Personagens e história
7. Quem são os 2 personagens (nome, aparência, história)? Mudam algo na jogabilidade?
8. Quem é a pessoa a ser salva em cada fase (a mesma ou diferente)? Existe história/narrativa e cinemáticas?
9. Dublagem/vozes e diálogos, ou jogo sem falas?

### Fases
10. Tema, ambiente e objetivo específico das fases 2 e 3?
11. ~~Quanto tempo de duração por fase?~~ **Fase 1: no máximo 10 min.** Fases 2 e 3 a definir.
12. Dificuldade: um nível só ou fácil/normal/difícil?

### Carro
13. Qual carro (tipo/modelo original)? Um só ou carros diferentes por fase?
14. O carro pode ter armas ou o jogador atira de dentro? Pode atropelar inimigos?
15. Dano por zonas (pneu, motor, etc.) e há reparo/combustível?

### Combate e progressão
16. Só a pistola alienígena no MVP, ou mais armas? Munição limitada?
17. Há itens, upgrades, loot ou moeda? Ou progressão apenas linear?
18. ~~Morreu: volta ao último checkpoint?~~ **Sim** (também quando o carro é destruído). Quantidade de checkpoints: início + transição por padrão.

### Produção
19. Time: só você, ou há outras pessoas (artistas, animadores)?
20. Meta de prazo e se o jogo será distribuído/vendido (afeta licenças de assets e fonte)?
21. Nome do jogo (provisório ou definitivo)?

---

## 15. Histórico do documento

| Versão | Data | Mudança | Autor |
|---|---|---|---|
| 0.1 | 2026-11-11 | Rascunho inicial (arquivo original `GDD_jogo_resgate_1.md`) | utrazin |
| 0.2 | 2026-11-11 | Repositório criado; links para ASSUMPTIONS/OPEN_DECISIONS. Nenhuma decisão de design alterada. | Claude (M0) |
| 0.4 | 2026-11-11 | Estilo visual decidido: **cartunesco** (OD-004). | utrazin |
| 0.3 | 2026-11-11 | Decididos: teclado/mouse **e** controle (OD-003); morte ou carro destruído voltam ao último checkpoint (OD-018); Fase 1 com **no máximo 10 min** (OD-011). | utrazin |

Regra: toda alteração de decisão registra versão, data, motivo e referência ao item de `OPEN_DECISIONS.md` resolvido.


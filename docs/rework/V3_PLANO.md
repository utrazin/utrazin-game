# Retrabalho v3: plano por etapas (2026-11-15)

Feedback do usuário sobre a v2 (resumo):
- **Mundo:** está vazio ("jogou uma pedra aqui, uma planta ali"). Ao olhar para o lado quase não deveria ver chão. Árvores cortadas pela metade nos morros. As muralhas de pedra/cristal ficaram feias. As curvas e a rampa ficaram ruins.
- **Carro:** desliza como no gelo, cai por baixo da parede e da rampa, e não tem motorista visível.
- **Zumbis:** não atacam nem interagem com o carro. Os spawns são fixos; quer spawn procedural.
- **Estrutura:** "metade carro, metade a pé" ficou ruim. Quer achar o carro no caminho e regras de onde o carro pode ou não ir.
- **HUD e ícones:** sem identidade, "parece gerado por IA".
- **Som:** não tem nenhum; quer mapeamento completo.
- **Céu:** não faz sentido céu de nuvens num planeta alienígena; quer planetas (tipo Saturno).
- **Forma de trabalhar:** dividir em etapas, cada uma num "chat"/agente separado, e validar no fim.

Pesquisas: [design](../research/PESQUISA_DESIGN_ZUMBI_CARRO.md), [técnica UE5](../research/PESQUISA_TECNICA_UE5.md).

## Novo roteiro (v3): ciclos carro/a pé alternados (~12 min)

Premissa: sua nave de resgate cai no vale. Você precisa achar um veículo, chegar ao posto de pesquisa, soltar a sobrevivente e fugir até a plataforma de extração.

| # | Zona | Modo | O que acontece | Recompensa/obstáculo |
|---|---|---|---|---|
| 1 | Queda da nave | a pé (~1,5 min) | começa sem arma entre destroços pegando fogo; graveto; poucos zumbis lentos (tutorial) | acha o **posto de gasolina** com o buggy sem combustível |
| 2 | Posto de gasolina | a pé | saquear o posto (galão de combustível + munição); horda pequena quando liga a bomba (barulho) | **buggy liberado** (E para entrar) |
| 3 | Deserto vermelho | carro (~2 min) | vale aberto com 2 caminhos, destroços com loot, zumbis agarram o carro e batem; rampas naturais | termina numa **árvore alienígena gigante caída** bloqueando |
| 4 | Fazenda / vila | a pé (~2 min) | casas para saquear (baú com pistola), achar o **guincho** no celeiro; ao usar, horda de barulho | volta ao carro, puxa a árvore |
| 5 | Floresta alienígena | carro (~2 min) | floresta densa, ravina com salto natural OU ponte, manada no caminho | **portão da base** fechado (sem energia) |
| 6 | Posto de pesquisa / nave caída | a pé (~3 min) | religar 3 geradores (Diretor aumenta a pressão), zumbi elite com escopeta, cela da sobrevivente | sobrevivente liberada |
| 7 | Fuga | carro (~1,5 min) | sobrevivente no banco do carona; horda perseguindo; estrada curta até a plataforma de extração | fim |

Regras do carro: áreas a pé (vilas, base, posto) cercadas por cercas/rochas naturais em que o carro não passa. O carro fica onde você deixou (marcado no minimapa). Combustível acaba devagar; galões no mapa.

Zumbis: **Diretor** (estilo Left 4 Dead): intensidade sobe com combate, picos e calmarias, spawns fora da visão em pontos válidos do navmesh, limite de vivos; grupos por zona; hordas por barulho (bomba, guincho, geradores). Sem spawn fixo, exceto chefes e encontros marcados.

Loot em níveis: destroços = comum (munição, sucata); casas = médio (vida, pistola); lugares perigosos = raro (escopeta, Fúria, peças).

Mundo em camadas (por zona): chão (grama/flores densas), pequenos (pedras, cogumelos), médios (arbustos, plantas), árvores, **marcos grandes** (1 por zona, visíveis de longe), horizonte (montanhas + planetas no céu).

## Etapas (cada uma é um agente/"chat" separado)

| Etapa | Agente | Arquivos que pode mexer | Depende de |
|---|---|---|---|
| E1 Plano e roteiro | principal | docs/rework, docs/gameplay | - |
| E2 Carro | carro | Source/.../Vehicles/*, AI/JREnemyCharacter.* (só a parte do carro), tools/unreal/setup_car_v3.py | - |
| E3 Mundo e céu | mundo | tools/blender/*, assets/work/levels/L01/*, tools/unreal/build_l01.py, tools/unreal/setup_sky_v3.py | E1 |
| E4 Jogabilidade (Diretor, loot, combustível, portões) | jogabilidade | AI/JRAIDirector.*, Gameplay/*, Interactions/*, Core/JRGameMode.* | E2 (arquivo do inimigo) |
| E5 Som | audio | novos arquivos Audio/*, assets/work/audio/*, tools/unreal/setup_audio_v3.py; ganchos só por lista | - |
| E6 HUD e ícones | hud | UI/*, assets/work/ui/*, tools/blender/make_ui*.py | - |
| E7 Integração e validação | validacao | todos (só correções) | E2..E6 |

## Regras para todos os agentes
- Usuário iniciante: instruções finais simples, numeradas, em pt-BR. Nunca usar o travessão longo (em dash) em texto nem código.
- Repo no PC do usuário via `mcp__remote-devices__device_bash` em `$HOME/mnt/utrazin-game` (não apaga arquivos; usar `_to_delete/` se precisar). A nuvem tem Blender (bpy 5.2 em /home/claude/bpy52/bin/python), PIL, numpy; sem internet geral.
- Não compilamos aqui: revisar o C++ com cuidado (includes, UFUNCTION em delegates, sombra de variáveis, float/double).
- Scripts Unreal: rodam pelo usuário com `py "E:/game/utrazin-game/tools/unreal/<script>.py"`, gravam relatório JSON em reports/, podem rodar de novo sem duplicar. A Unreal não sobrescreve assets em retarget (usar pasta nova).
- Mexa só nos arquivos da sua etapa. Se precisar de mudança fora, escreva em docs/rework/PEDIDOS.md.
- No fim, escreva docs/rework/E<n>_RESULTADO.md: o que fez, comandos para o usuário, o que testar, dúvidas.
- Não fazer commit/push.

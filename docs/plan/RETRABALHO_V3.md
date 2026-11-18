# Retrabalho v3 "Vale Alienígena" (2026-11-15)

Feedback do usuário sobre a v2 (resumo): cenário vazio e "jogado" (quer olhar para o lado e quase não ver chão),
árvores bugadas/cortadas no morro, muralhas de cristal sem graça, curvas e saltos ruins (carro cai por baixo da rampa),
carro "no gelo" (desliza, sem controle), ninguém aparece dirigindo, zumbi ignora o carro, metade carro/metade a pé
ficou chato, HUD e ícones genéricos ("cara de IA"), mensagens feias, sem som nenhum, céu de nuvens não combina com
planeta alienígena (quer planetas tipo Saturno). Pediu pesquisa, roteiro novo, etapas separadas e agentes por área.

## Pesquisa (resumo)
- Jogos de referência: Pacific Drive, Dying Light: The Beast, Days Gone, State of Decay, Drive Beyond Horizons,
  Overland/Deadly Days Roadtrip, Blood Drive. Padrão comum: sair do carro VÁRIAS vezes, sempre com motivo
  (combustível, peça, portão, loot); o carro é frágil e valioso; zumbis atrapalham o carro (sobem, agarram, bloqueiam).
- AI Director (Left 4 Dead): intensidade sobe com dano/mortes; ciclo preparação > pico > alívio; spawn fora da visão.
- Densidade: camadas (chão variado, cobertura rasteira, tralhas pequenas em grupos, arbustos, árvores em bosques,
  1 marco grande por zona, horizonte). Denso onde o jogador olha; longe barato (névoa).
- Carro "no gelo": causas comuns = malha visual com colisão, centro de massa alto, atrito baixo, tração traseira,
  física sem substep/async. Ver docs da pesquisa no fim.

## Novo roteiro (12 a 15 min, alterna carro e a pé 4 vezes)
| # | Zona | Modo | O que acontece |
|---|---|---|---|
| 0 | Acampamento caído (início) | a pé | sem arma; graveto; 3 a 5 zumbis lentos; acha a CHAVE do buggy numa barraca; rádio: "siga o sinal" |
| 1 | Vale aberto A | carro | 2 caminhos; carcaças para saquear (munição/sucata); grupos do Director; combustível começa em ~40% |
| 2 | Posto de pesquisa | a pé | combustível acabando: pegar galão; baú com PISTOLA; mini-horda quando liga a bomba de gasolina |
| 3 | Floresta alienígena | carro | trilha mais fechada e densa; zumbis sobem no capô (balançar para soltar); barricada de corpos/carcaças |
| 4 | Árvore gigante caída | a pé | bloqueia a estrada: buscar explosivo na colmeia; zumbi ELITE com ESCOPETA; explosão chama horda |
| 5 | Fuga da horda | carro | horda atrás; salto opcional na ravina; zumbis pesados batem no carro |
| 6 | Nave caída / sobrevivente | a pé | limpar, achar a sobrevivente, defender 60 a 90 s |
| 7 | Extração | carro | sobrevivente no banco do carona; dirigir até o ponto de resgate; fim |
Regra: nenhum trecho passa de ~2,5 min; toda troca carro/a pé tem motivo. Entrar e sair do carro a qualquer hora (E).

## Etapas e donos (cada agente só mexe nos arquivos dele)
| Etapa | Agente | Dono de |
|---|---|---|
| E1 Carro | "carro" | Source/JogoResgate/Vehicles/*, Core/JRPlayerController.*, Characters/JRCharacter.* (só entrar/sair do carro e motorista), tools/unreal/setup_vehicle_v3.py |
| E2 Mapa | "mapa" | tools/blender/gen_l01.py, make_l01_props*.py, tools/unreal/build_l01.py, assets/work/levels/L01/*, assets/raw/env/*, Source/JogoResgate/Environment/* (novo) |
| E3 Jogabilidade/IA | "jogabilidade" | Source/JogoResgate/AI/*, Gameplay/*, Interactions/*, Levels/* (exceto o que E1 tocar), tools/unreal/setup_gameplay_v3.py |
| E4 Audiovisual (som + céu) | "audiovisual" | Source/JogoResgate/Audio/* (novo), assets/raw/audio/*, assets/work/sky/*, tools/unreal/setup_audio.py, tools/unreal/setup_sky.py |
| E5 HUD/arte de UI | "hud" | Source/JogoResgate/UI/*, assets/work/ui/*, tools/blender/make_ui.py, tools/unreal/setup_ui_v3.py |
| E6 Integração e validação | "validacao" | revisão de compilação, ganchos de som nos outros arquivos, testes, docs, relatório final |

## Contratos entre etapas (para não pisar no pé)
- Carro (E1) expõe em AJRVehiclePawn (públicos): GetFuel()/AddFuel(float 0..1)/IsOutOfFuel(); ApplyZombieImpact(AActor* Zombie, float Damage);
  TryAttachGrabber(ACharacter* Zombie) -> bool / DetachGrabber; GetSpeedKmh(); delegate OnVehicleHit. E3 usa isso do lado do zumbi.
- E3 expõe: AJRGateBlocker (exige item), item "chave do carro" e "galão" (EJRPickupType novos: CarKey, FuelCan, Explosive),
  AJRDirector (spawn procedural). Pickups novos só em Gameplay/JRPickup.*.
- E4 expõe: UJRAudio::Play2D / PlayAt(WorldContext, FName Cue, FVector) e um DA com a lista de sons; E6 coloca as chamadas nos outros arquivos.
- E5 lê do jogo só por getters públicos já existentes (ou pede em relatório).
- Ninguém roda git commit. Ninguém apaga arquivo (o shell do PC não deixa); arquivo velho vai para _antigo/.
- Sem travessão longo nos textos. Textos do jogo e docs em pt-BR.

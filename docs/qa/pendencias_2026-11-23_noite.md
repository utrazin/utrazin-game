# Pendências da Villa Star: o que melhorar na próxima rodada (23/11, noite)

Este documento junta o feedback do usuário depois de testar a cidade v5, os interiores e a bicicleta (A-096/A-097), mais o que dá para concluir pelos prints. É o ponto de partida do próximo chat.

Contexto técnico: veja `claude/handoff-2026-11-23-noite.md` e `docs/decisions/ASSUMPTIONS.md` (A-094 a A-097).

Regras que continuam valendo:
- Respostas em pt-BR informal, sem travessão.
- Sem parede invisível. Nada low poly.
- Não fazer commit sem pedir. Backup em `$HOME/bk_*`.
- Ser honesto sobre o que foi escrito, compilado, rodado e visto no Play.

---

## Prioridade 1: está quebrado

### 1. Não dá para andar dentro dos cômodos
O herói entra pela porta (o fade e o teleporte funcionam), mas não anda lá dentro. Isso vale para todos os 5 interiores.

Suspeitas, em ordem:
- O `AJRInteriorPortal` chama `SetIgnoreMoveInput(true)` e depois `false`. Se o E for apertado duas vezes ou a interação disparar de novo, o contador não zera. Trocar por `ResetIgnoreMoveInput()` no fim, ou por um bloqueio próprio.
- O ponto de chegada (150 cm da porta) pode cair dentro da colisão de algum móvel ou da caixa UCX de um balcão. O herói fica preso.
- O modo de movimento pode ficar travado em Falling ou None depois do teleporte, ou o personagem pode ficar a uns 4 cm acima do piso sem pousar. Forçar `SetMovementMode(MOVE_Walking)` depois do teleporte.
- A `AJRCameraZone` mexe no braço da câmera. Conferir se ela não mexe em mais nada.
- Conferir também se a Remap GameMode trava o input fora de áreas conhecidas.

Como verificar: log de `[fix_land]` / `[interiores]`, print com `stat` ou `showdebug`, e testar `ResetIgnoreMoveInput` pelo console.

### 2. A bicicleta está bugada
No print, o herói está alto demais. As pernas atravessam o quadro, os pés flutuam ao lado da roda da frente e as mãos não pegam o guidão. A pose é a de dirigir o buggy (`DrivingAnim`) com a malha erguida 32 cm. Isso não serve.

O que fazer:
- Usar uma animação de ciclista de verdade: pesquisar opções gratuitas (Mixamo e afins), ou fazer uma pose e um ciclo de pedalada no Blender com o rig do herói.
- Ajustar com IK: mãos no guidão, pés nos pedais, quadril no selim (Control Rig ou Two Bone IK no AnimBP).
- O pedivela da bicicleta tem que girar junto com a pedalada. Para isso precisa separar a malha do pedivela.
- Reajustar `RiderMeshOffset` e a escala da bicicleta em relação ao herói (no print, a bicicleta parece pequena para ele).

### 3. Krug está "zoado"
O modelo é uma criatura tipo tartaruga, estática, sem rig, enorme. Ele atravessa o balcão (no print, o casco passa por cima e as garras saem pelos lados).

O que fazer:
- Rever o modelo do Krug (ver `claude/npc-krug.md`): rig, idle e escala certa.
- Colocar ele atrás do balcão com folga, ou aumentar o cômodo e afastar o balcão.

### 4. Carro flutuando
Os carros batidos (`PRP_CarroBatido1/2`) ou o buggy aparecem no ar. Provavelmente estão a uma altura fixa ou usam o chão antigo da v4. Colocar no chão pelo heightmap e alinhar à inclinação.

### 5. Prédios não entráveis com parede invisível
A colisão em volta deles é maior que o modelo: caixa UCX ou "complex" mal fechada. Isso viola a regra de nada de parede invisível.

O que fazer:
- Colisão justa (UCX de várias caixas que sigam as paredes).
- Ou tornar mais prédios entráveis, se fizer sentido na história.

### 6. Sobreposição de malhas (z-fighting)
Várias partes das casas piscam ou se sobrepõem.

O que fazer:
- Checar casas que se cruzam (o `try_house` só olha o raio, não a caixa girada).
- Checar faces duplicadas nos modelos do Tripo.
- Checar o piso do interior colado no piso de outra peça.

---

## Prioridade 2: aparência

### 7. Grama em billboard ficou ruim e tem grama no meio da rua
O usuário pediu para pesquisar como se faz direito. A versão atual é um card que gira para a câmera (World Position Offset) com o atlas `T_Grama_Atlas`. Ficou feio.

Pesquisar e decidir:
- Grama em tufos de cards cruzados (2 a 3 quads por tufo, sem girar para a câmera).
- Normais viradas para cima (iguais às do terreno, sem sombra estranha).
- Cor puxada do terreno (Runtime Virtual Texture ou cor do Landscape).
- Vento sutil.
- Densidade e cull distance bem definidas.
- Variação de altura e cor.
- Ver referências estilizadas (Ghibli/Genshin) e o Landscape Grass Type + Procedural Foliage da Unreal.

Grama na rua: a saída de grama (`LandscapeGrassOutput`) usa `1 - soma das camadas` vinda da máscara projetada por posição no mundo. Pode estar desalinhada ou com o `MaskOrigin` errado no momento em que a grama é gerada.
- Conferir o alinhamento.
- Pensar em camadas pintadas de verdade no Landscape (paint layers geradas a partir da máscara), que a grama respeita sem erro.

### 8. Objetos não respeitam o desnível
Árvores, props e casas no morro ficam retos ou meio enterrados ou flutuando.

Regra nova a implementar no `dress`:
- Casas e prédios: plataforma plana (já existe no heightmap; conferir se pega todos) e sentar no ponto médio, não no mais baixo.
- Árvores e plantas: inclinar até um pouco a favor do terreno (parte da normal, limite de uns 10 graus) e afundar a base pela inclinação.
- Pedras, props e carros: alinhar à normal do chão.
- Ler a normal do heightmap (o r16 já está no script).

### 9. Iluminação fraca, principalmente nas casas
- **Interiores:** mais pontos de luz (luminárias de teto como malha + luz), janelas com brilho, luz de destaque nos balcões e luz vazando pela porta.
- **Exterior:** luz na frente das portas, janelas acesas à noite (emissivo nos modelos das casas), lanternas e postes com mais presença.
- Rever exposição e skylight da cidade (`fix_luz_v4.py`).

### 10. Interior com cara de "caixa"
No print do Armeiro, o teto de tábuas ciano tem um padrão estranho, as paredes são lisas e bege, e o cômodo não combina com o exterior alienígena roxo.

O que fazer:
- Kit de interior no estilo da Villa (paredes com tábuas e metal roxo-azulado, cristais, janelas redondas).
- Mais objetos de contexto por cômodo: armas expostas no Armeiro, peças e faíscas na Bancada.

---

## Prioridade 3: sentido e contexto da cidade

### 11. As coisas estão "socadas" sem contexto
Cristal dentro de árvore, contêineres empilhados um embaixo do outro, casa aqui e casa ali.

O que fazer:
- Cada bairro com função e história (residencial, oficinas, comércio, armazém, ruínas do ataque, posto de vigia no portão).
- Props agrupados por história: oficina com peças e gerador, armazém com contêineres alinhados em fileira e empilhados com lógica, mercado com barracas e caixas de fruta.
- Regras de distância entre tipos de objeto: nada de cristal ou árvore dentro de outro objeto. Checar colisão por caixa girada, não só por raio.
- Revisar o gerador `gen_city_v5.py`: contêineres, cristal do laboratório, ruínas e árvores do jardim.

### 12. Histórias para ir desbloqueando a cidade
Ideia do usuário:
- Missões curtas dos moradores (Krug, Ix-Vel, Kaar e novos) que liberam partes da cidade, lojas e interiores aos poucos.
- Bilhetes e lore dentro das casas (a leitura de bilhete com E já estava nos planos).
- Ligar com o loop da arena.

### 13. Minimapa e radar
Melhorar como as coisas são apontadas:
- Ícones diferentes por tipo (loja, missão, porta, bicicleta).
- Seta na borda para alvos fora do alcance.
- Nome ao chegar perto.
- Distância só do alvo da tarefa.
- Mapa grande (M) com a planta da cidade.

---

## Prioridade 4: som

### 14. Som da bicicleta e da cidade
Hoje está sem graça.
- **Bicicleta:** roda livre (catraca), corrente ao pedalar, pneu no asfalto, na terra e na grama (por superfície), freio, campainha, vento com a velocidade e batida ao cair.
- **Cidade:** ambiente de dia e de noite, NPCs, portas e interiores com acústica diferente (reverb).

---

## Pendências antigas que continuam abertas
- Defeitos nas malhas dos prédios (11).
- Physics Asset (26).
- IK (27).
- Primeira pessoa (28).
- Ver `claude/arte-vila-pendencias.md`.
- Ligação do ruído no campo de força (`setup_vila_glow.py`, aviso "Position").
- Arena procedural: conferir no Play as regras de A-089.

## Ordem sugerida para o próximo chat
1. Itens 1 a 6 (quebrados).
2. Itens 7 a 10 (aparência), com pesquisa da grama antes de refazer.
3. Itens 11 a 13 (contexto, histórias, mapa).
4. Item 14 (som).

# Passagem de bastão para a próxima conversa (2026-11-17)

Leia isto inteiro antes de mexer em qualquer coisa. Os prints citados estão em `docs/handoff/2026-11-17/print_NN.png`.

## Quem é o usuário e como trabalhar

- Iniciante em Unreal, fala português do Brasil. Respostas em pt-BR, com passos simples e numerados.
- **Nunca usar o travessão "—"** em nada (respostas, código, docs).
- Ele compila e roda os scripts. Você não consegue rodar a Unreal: escreva com cuidado e revise o C++ antes de entregar.
- Ele pediu para dividir o trabalho em etapas pequenas e usar subagentes, cada um com uma parte, e depois validar.
- Ele quer **prints e prévias** do que está ficando pronto (renderize no Blender da nuvem e mande com SendUserFile).

## Projeto

- Repo: `E:\game\utrazin-game` (GitHub utrazin/utrazin-game). UE 5.8.4 em `E:\UE_5.8`. Módulo C++ `JogoResgate`, prefixo `JR`.
- Acesso: `device_bash` (pasta montada em `$HOME/mnt/utrazin-game`, sem rede, não apaga arquivos). Os assets do usuário ficam em `C:\Users\enzor\OneDrive\Área de Trabalho\assets-game` (2d, 3d, texture).
- Compilar (PowerShell, editor fechado):
  `& "E:\UE_5.8\Engine\Build\BatchFiles\Build.bat" JogoResgateEditor Win64 Development -Project="E:\game\utrazin-game\unreal\JogoResgate\JogoResgate.uproject" -WaitMutex`
- Scripts do editor: `py "E:/game/utrazin-game/tools/unreal/<script>.py"` na caixa Cmd. Cada um grava `reports/<script>.json`; leia os relatórios direto do PC.
- Plano geral (Claude Doc): https://claude.ai/artifact/QgqWrFeZMZFWcactxHQD71 . Decisões em `docs/decisions/ASSUMPTIONS.md` (já vão até a **A-061**). Fase: `docs/gameplay/L01_STORYBOARD.md` (v3, 8 zonas). Animações: `docs/gameplay/ANIMATIONS.md`.

## Armadilhas já conhecidas (não repetir)

- O compilador trata como **erro** uma variável local com o mesmo nome de um membro (C4458/C4456).
- `UEnhancedInputComponent::BindKey` é deletado: use `static_cast<UInputComponent*>(Input)->BindKey(...)`.
- `meta=(Units="...")` só aceita unidades conhecidas (`cm`, `s`, `cm/s`, `km/h`, `Degrees`, `m`).
- Para o sistema de navegação use `FNavigationSystem::GetCurrent<UNavigationSystemV1>(World)`.
- `IKRetargetBatchOperation.duplicate_and_retarget` **nunca sobrescreve**: retarget só do que falta, em pasta nova, e salve na hora.
- Arquivos `.uasset` somente leitura quebram o salvamento: `attrib -R "E:\game\utrazin-game\unreal\JogoResgate\Content\*.*" /S /D`.
- Python 5.8: `RuntimeFloatCurve.editor_curve_data` e `PhysicsAsset.skeletal_body_setups` não existem (já há `JRVehicleTuningLibrary` em C++ para isso). `MaterialEditingLibrary.get_used_textures` falha com MaterialInstance.

## Estado atual (tudo compilou e os scripts rodaram em 16/11 23:50 a 17/11 00:00)

Já existe: carro com freio e anticapotagem, motorista sentado, zumbi x carro (agarrar, atropelar, barricada, fogo), diretor de IA (Subida/Pico/Calmaria), zumbis que passeiam e escutam, mapa v3 de 8 zonas com carro e a pé alternando, céu com planetas, modelos do Tripo do usuário, primeira pessoa (V), roda de itens com abas (Tab), cura (H), rifle com luneta, coice, tiros de plasma, sangue, câmera de interação, HUD v2 no estilo das referências do usuário (`assets/raw/ui_refs`), vegetação (1,15 milhão de instâncias), 126 sons e música.

Erros e avisos dos relatórios que ainda precisam de atenção:
- `fix_weapon_grips.json`: erro no Hero02 (`'Object' object has no attribute 'get_play_length'`), linha ~320. O encaixe da Victoria não foi aplicado.
- `setup_zombie_models.json`: os 4 personagens (ZMB_Comum, ZMB_Corredor, ZMB_Tanque, NPC_Sobrevivente) ficaram **sem textura** (material de reserva) e **sem Physics Asset**.
- `scatter_l01.json`: a recoloração da grama da Quaternius falhou (`get_used_textures` com MaterialInstance).

## O que o usuário pediu para arrumar agora (pela ordem dos prints)

1. **Itens sem colisão** (print_01: herói dentro do barril). A maioria dos objetos colocados pelo `build_l01.py` v3 e pelo `l01_user_dressing.py` não tem colisão nem interação. Dar colisão simples a tudo que é sólido. Barris, caixas e objetos pequenos devem ter física (empurráveis por tiro e carro).
2. **Restos das versões antigas, sem cor e sem motivo** (print_02: palete branco no chão). Limpar tudo que não pertence à v3: apagar atores antigos de qualquer tag (L01Gen, Quaternius brancos, props v1/v2) e reconstruir. Todo objeto precisa de textura e de um motivo para estar ali.
3. **Contêiner oco** (print_03): ou fecha a entrada, ou tem interior de verdade. Em lugares fechados a câmera em terceira pessoa precisa se aproximar e ficar dentro (hoje fica por cima e não se vê o personagem).
4. **Zumbis invisíveis** (print_04). Começou depois do `setup_zombie_models.py`. Investigar: malha, material sem textura, ABP retargetado (pose quebrada pode sumir a malha), LOD, bounds. Os tamanhos importados estão certos (180, 170, 260, 170 cm). Se não resolver rápido, existe `UNDO=True` no topo do script para voltar ao zumbi anterior.
5. **Item voando, sem cor e sem nada** (print_05: caixa branca flutuando perto da barraca). É um pickup ou prop flutuando com malha sem textura. Itens devem ficar no chão ou em cima de algo (mesa, caixa), com textura.
6. **Objetos sobrepostos** (print_06: árvore atravessando cristal e grama). A vegetação (`scatter_l01_v3.py`) e os enfeites (`l01_user_dressing.py`) não se evitam. Precisa de espaçamento por raio de cada malha e exclusão em volta dos objetos já colocados.
7. **Morros vazios e estrutura do mapa** (print_07). Os morros em volta estão vazios, só com pedras soltas sem sentido. O usuário pede um **remapeamento completo**, e talvez mudar a estrutura do mapa para as coisas fazerem sentido. Antes de mexer, mostre a ele uma prévia de cima e uma de olho do personagem.
8. **Brilho exagerado** (print_08: sofá e destroços brancos estourados). Materiais emissivos fortes demais (`M_L01_Glow` multiplica por 6; algumas malhas pegam esse material sem querer) e possíveis luzes pontuais dentro de objetos. A nave também brilha demais. Reduzir e conferir quais malhas usam material de brilho.
9. **Kit médico flutuando** (print_09). Pickups giram e flutuam a 0,8 m. Colocar no chão ou em superfícies, de forma que faça sentido.
10. **Animação de bandagem.** Hoje `heal_anim` usa "Drinking" do Mixamo, que não serve. Ele quer o herói enrolando uma bandagem no braço, girando o braço. O Mixamo não tem "bandage": procurar algo parecido ("Rubbing Arm", "Arm Stretching", "Checking Wrist") ou fazer animação procedural.
11. **Baú não abre.** Investigar `JRLootChest` + `JRInteractionComponent` (traço e proximidade), o modelo do baú dividido em base e tampa (`SM_PRP_Bau_Base/Tampa`), e a câmera de interação, que pode estar travando o fluxo.
12. **Marcador para itens interativos.** Ele demorou para achar o graveto. Quer um marcador bonito (no mundo e no minimapa) para cada coisa que precisa pegar ou usar, como o graveto, o baú da chave e o galão. O losango amarelo atual é feio.
13. **Objetivo inconsistente** (vários prints). O painel diz "Siga a pé pelas vilas até a nave caída" e mostra 1450 m enquanto a tarefa real é "pegue o graveto" ou "procure a chave". O objetivo e o marcador devem seguir a tarefa atual da zona, não um checkpoint distante.
14. **Minimapa "escrotaço".** Refazer bonito: mapa estilizado no tema do HUD v2, ícones claros, estradas, zona atual, rotação ou norte fixo bem feito.
15. **Aviso na tela** "YOUR SCENE CONTAINS A SKYDOME MESH WITH A SKY MATERIAL BUT IT DOES NOT COVER THAT PART OF THE SCREEN" (prints 02, 05, 09). Vem do `setup_alien_sky.py`: algum material com "Is Sky" (estrelas, planeta ou aurora) não cobre a tela. Tirar o "Is Sky" dos corpos ou ajustar o domo.
16. **Textura do terreno** repetindo muito nos morros (padrão de mosaico visível, print_04).

## Pendências antigas que continuam abertas

- Não existe medidor de gasolina de verdade (só o item Fuel).
- A sobrevivente não entra no carro.
- A zona 7 não tem checkpoint.
- O ABP da Victoria (`ABP_Unarmed_H02`) não tem o slot UpperBody (passo manual).
- Fazer commit e push de tudo, com Git LFS para as imagens grandes em `assets/work/`.
- Confirmar se o plano do Tripo permite uso comercial.
- O usuário também pode trazer mais modelos e texturas do Tripo se você pedir uma lista.

## Sugestão de ordem para a próxima conversa

1. **Diagnóstico com prova:** peça ao usuário prints do Outliner e de detalhes, ou use o controle do computador (computer use) para olhar a Unreal com permissão. Leia os relatórios.
2. **Correções que travam o jogo:** zumbis invisíveis, baú que não abre, colisão dos objetos, objetivo correto.
3. **Limpeza do mapa:** remover lixo antigo, brilho, flutuação, sobreposição, texturas.
4. **Remapeamento do mapa e dos morros:** mostrar prévias e só aplicar depois do OK do usuário.
5. **Visual:** minimapa, marcadores, animação de bandagem.

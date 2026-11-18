# Catálogo dos modelos do usuário (Tripo 3D)

Origem: pasta do usuário `assets-game/3d/` (56 GLB `tripo_convert_<uuid>.glb`, gerados no Tripo 3D a partir das
referências 2D de `assets-game/2d/`). Licença: própria do usuário (gerado por IA no Tripo; plano/termos a confirmar,
ver `assets/manifest/assets.json`). Identificação feita por renderização de cada GLB com a própria textura e
comparação visual com as 56 imagens 2D (prévia: [`_catalog_preview.png`](_catalog_preview.png); escala real lado a lado,
baú dentro da barraca e plano da L01 em [`previews/`](previews/)).

## Como os arquivos vieram

- 1 malha, 1 material só com **cor base 4096 x 4096** (sem normal/rugosidade), **maior lado = 1 m** (tamanho falso).
- 4 a 20 mil triângulos cada (nenhum passa de 40 mil: não foi preciso decimar).
- **Nenhum tem rig, osso, peso ou animação** (personagens em T-pose, malha estática).
- Todos olham para **+X do Blender** (= +X da Unreal no FBX exportado pelo `prep_tripo.py`).

## Arquivos

- `assets/raw/tripo/<Nome>.glb`: cópia exata do original, renomeada (originais intactos na pasta do usuário).
- `assets/raw/tripo/tripo_catalog.json`: tabela usada pelos scripts (nome, uuid, regra de tamanho, colisão...).
- `assets/work/tripo/SM_<Nome>.fbx`: tamanho real em metros, origem no centro de baixo, frente +X, colisão UCX;
  `textures/T_<Nome>_D.jpg` (1024 ou 2048); `tripo_processed.json` (medidas finais). Gerados por
  `tools/blender/prep_tripo.py`. Extras: `SM_PRP_Bau_Base.fbx` / `SM_PRP_Bau_Tampa.fbx` (baú dividido para o
  AJRLootChest) e `SM_<Personagem>_mixamo.fbx` (textura embutida, olhando para a frente do Mixamo).
- Unreal: `tools/unreal/import_user_assets.py` -> `/Game/Environment/User/<Categoria>/SM_<Nome>`.

Colisão: `box` = caixa da malha toda (props e casas decorativas: a porta fica fechada); `trunk` = só tronco/poste;
`complex` = a própria malha (dá para entrar/passar por baixo: barraca, cobertura do posto, arco, marcos);
`none` = sem colisão (itens, armas, flores, arbustos, personagens).

| Nome final | GLB original (uuid) | Referência 2D | Tamanho final (m) X x Y x Z | Tris | Textura | Colisão | Notas |
|---|---|---|---|---|---|---|---|
| NPC_Sobrevivente | `32ceba9b-6639-4169-9187-c06104b5219b` | Wasteland Scientist Survivor Character | 0.469 x 1.154 x 1.7 | 18893 | 4096 -> 2048 | none | sem rig; T-pose |
| ZMB_Comum | `4df1ff59-fecb-4107-88a7-28852faa9af3` | Alien Zombie Character Reference | 0.342 x 1.413 x 1.8 | 19668 | 4096 -> 2048 | none | sem rig; T-pose; de botas |
| ZMB_Corredor | `0ccb1557-54ba-4790-916b-d1cf9883f119` | Glowing Veins Zombie in T-Pose | 0.416 x 1.341 x 1.7 | 19002 | 4096 -> 2048 | none | sem rig; descalço, magro (corredor); T-pose curvada |
| ZMB_Tanque | `3c471557-5eb3-4d4f-97bb-c5c941b29e6c` | Cyan Vein Crystal Tank Zombie | 1.28 x 2.907 x 2.6 | 19137 | 4096 -> 2048 | none | sem rig; T-pose; cristais roxos nas costas |
| ARM_Escopeta | `bd3fc20b-1b76-4611-a1e3-9a2757c00de5` | Elongated Alien Plasma Blaster | 0.9 x 0.382 x 0.347 | 17508 | 4096 -> 1024 | none | arma: origem na empunhadura, cano em +X |
| ARM_Graveto | `073f570f-ccef-448a-ae1d-284ce8d137a0` | Glowing Purple Gnarled Fantasy Staff | 0.9 x 0.104 x 0.231 | 17093 | 4096 -> 1024 | none | arma: origem na pegada, lâmina em +X, fio em +Z |
| ITM_Chave | `513e791f-38bb-43a8-a45a-44702c65a586` | Buggy Key with Alien Fang Charm | 0.03 x 0.077 x 0.12 | 18480 | 4096 -> 1024 | none |  |
| ITM_Explosivo | `b39a5e4d-cf3d-4c4d-820e-59f51b8f436e` | Fantasy Dynamite Crystal Bundle | 0.235 x 0.224 x 0.35 | 19126 | 4096 -> 1024 | none |  |
| ITM_Galao | `a7ffe774-5fb3-4716-8f7b-881cf777eef4` | Battered Red Jerrycan Fuel Icon | 0.215 x 0.385 x 0.5 | 17982 | 4096 -> 1024 | none |  |
| ITM_KitMedico | `c866cd29-c9f2-4767-867c-f205b6a22699` | Stylized Green Medical First-Aid Kit | 0.245 x 0.4 x 0.333 | 4707 | 4096 -> 1024 | none |  |
| ITM_Municao | `c2ee5c8b-ba5c-420c-a300-3f9810a57966` | Futuristic Cyan Energy Ammo Crate | 0.323 x 0.4 x 0.305 | 18278 | 4096 -> 1024 | none |  |
| PRP_Barricada | `985ba99b-ab55-4b87-844e-b482961765ca` | Stylized Wooden Tire Barricade | 1.943 x 3 x 1.344 | 18266 | 4096 -> 1024 | box | comprimento ao longo de Y |
| PRP_Barril | `066cd04c-3d60-4347-816b-3f212abf3ab7` | Stylized Red Explosive Barrel | 0.808 x 0.763 x 0.9 | 4974 | 4096 -> 1024 | box |  |
| PRP_Bau | `4af866b3-02d4-4577-8485-5ba90998ab0c` | Stylized Military Loot Chest | 1 x 0.722 x 0.53 | 4769 | 4096 -> 1024 | box | girado: frente em +Y (padrão do AJRLootChest); também sai em _Base e _Tampa (tampa com origem na dobradiça) |
| PRP_CarroBatido1 | `d9838a9a-cb6e-47e7-b851-3754e4315046` | Overgrown Wrecked Sedan Asset | 4.5 x 2.739 x 1.752 | 18079 | 4096 -> 2048 | box | sedã, frente em +X |
| PRP_CarroBatido2 | `9e6496d1-4e16-4f04-b3d5-649837e62555` | Overturned Burned Pickup Truck Asset | 5 x 4.472 x 1.751 | 4898 | 4096 -> 2048 | box | picape capotada, frente em +X |
| PRP_Gerador | `5e0be74b-0149-4c72-a222-eec89e15dd50` | Weathered Stylized Diesel Generator | 0.819 x 1.5 x 1.212 | 17963 | 4096 -> 1024 | box |  |
| PRP_Onibus | `7965908c-49cd-4d2b-9cac-1df7d9e9e7e7` | Wrecked Overturned ESCOLAR School Bus | 10 x 4.795 x 3.386 | 17994 | 4096 -> 2048 | box | girado: comprimento em X; tombado de lado |
| PRP_Ossos | `e43de724-bc32-46c5-b727-83c289ba941f` | Alien Beast Skeleton Carcass | 2.46 x 3 x 1.063 | 18815 | 4096 -> 2048 | box |  |
| PRP_Placa | `da751174-9b4b-40c6-a995-1174ba5adb86` | Rustic Perigo Warning Sign | 0.474 x 1.327 x 2 | 4988 | 4096 -> 1024 | box | placa PERIGO, lida de +X |
| PRP_Poste | `7a4a4d05-afaa-4bae-8abc-050c1ad31b06` | Alien Blossom Sci-Fi Lamp Post | 1.399 x 1.399 x 5 | 18340 | 4096 -> 1024 | trunk |  |
| CON_Barraca | `e40f22a8-cd93-4b5b-9412-18b84890c3df` | Stylized Open Military Camp Tent | 5.101 x 6.5 x 4.21 | 4698 | 4096 -> 2048 | complex | 6,5 m (não 4): só nesse tamanho a abertura da frente (+X) passa de 2 m de altura; sem chão (o terreno aparece) |
| CON_Cabana | `a7ba59d5-41b2-46d1-b1e8-63e64333200e` | Rustic Wooden Cabin Game Asset | 5.718 x 6 x 5.178 | 4545 | 4096 -> 2048 | box | decorativa (porta em +X): caixa de colisão fecha a porta |
| CON_CasaVila | `ec2c1c27-3c8e-481c-82bf-89343f2d5023` | Alien-Vine Enchanted Cottage | 9.139 x 10 x 8.004 | 17902 | 4096 -> 2048 | box | decorativa (porta em +X): caixa de colisão fecha a porta |
| CON_Cela | `f92b2d15-1916-41af-9cff-1633d02f4078` | Alien Metal Cage Cell | 3 x 3 x 2.965 | 18351 | 4096 -> 1024 | complex | porta em +X |
| CON_Cerca | `b7a70bbe-4e2d-47d4-8b0b-6cdd1bec270c` | Stylized Wooden Chain-Link Fence | 0.274 x 4 x 1.104 | 16249 | 4096 -> 1024 | box | comprimento ao longo de Y |
| CON_Conteiner | `36cc2117-dc28-46f1-9999-044417bc6d76` | Stylized Shipping Container Facade | 4.38 x 6 x 2.337 | 16665 | 4096 -> 2048 | box | comprimento ao longo de Y, porta em +X |
| CON_Ponte | `e42d01c9-cd0e-4d3e-8b05-2b3c29fd1d7f` | Stylized Rope Suspension Bridge Asset | 14 x 5.178 x 4.521 | 18344 | 4096 -> 2048 | complex | girada: comprimento em X; tábuas a ~1,65 m do pé (meio) e 2,2 m (pontas) |
| CON_Portao | `fe6f8012-65d7-4c62-9562-a693b86ed02c` | Stylized Iron Gate with Chain Lock tshama | 1.28 x 6 x 3.065 | 4896 | 4096 -> 2048 | box | largura ao longo de Y |
| CON_PostoBomba | `f97e1765-679e-4e09-8d78-cdec5114e699` | Retro 1950s Gasoline Pump | 0.468 x 0.757 x 1.8 | 4631 | 4096 -> 1024 | box | frente em +X |
| CON_PostoCobertura | `74c9a36f-4434-43fe-9a85-cdd9afdf5976` | Stylized Posto Gas Station Canopy | 9.652 x 12 x 5.847 | 4668 | 4096 -> 2048 | complex | comprimento ao longo de Y; dá para passar por baixo |
| CON_PostoLoja | `8a4e2289-edba-467e-adb5-b3b9eaf01ca6` | Abandoned Loja de Conveniência Frontage | 8.474 x 10 x 6.673 | 16358 | 4096 -> 2048 | box | decorativa (porta em +X): caixa de colisão fecha a porta |
| CON_TorreRadio | `b2cd9c88-ae40-4e6e-9fba-0529a4e098cc` | Stylized Red and Gray Communication Tower | 8.17 x 8.268 x 25 | 4397 | 4096 -> 2048 | complex |  |
| MRC_Arco | `1a0ee63a-8a28-4b6f-8dff-a5f2742fab27` | Stylized Red Sandstone Rock Arch | 19.515 x 36 x 18.106 | 5070 | 4096 -> 2048 | complex | 36 m (não 20): o vão sob o arco fica com ~13 m de largura e altura para a estrada de 12 m passar; vão ao longo de X |
| MRC_ArvoreMae | `5e89dea8-5d94-47d1-a5ba-966181f6a94a` | Bioluminescent Alien Mother Tree | 28.608 x 35.568 x 30 | 16722 | 4096 -> 2048 | complex |  |
| MRC_Colmeia | `7bfa5971-22d9-4cbd-ab1e-4bb6dbe29363` | Alien Hive with Glowing Amber Caverns | 13.415 x 15 x 13.18 | 18960 | 4096 -> 2048 | complex | boca da caverna em +X |
| MRC_Cristal | `75c09f6d-ea7e-4b75-ab58-d2924adb8224` | Purple and Turquoise Crystal Cluster | 7.969 x 7.781 x 8 | 4542 | 4096 -> 2048 | complex |  |
| MRC_DiscoVoador | `21fb7d23-245b-4863-9bf1-d002f1452626` | Crashed Retro UFO Game Asset | 24.413 x 25 x 10.812 | 17553 | 4096 -> 2048 | complex | já vem enterrado num monte de terra |
| MRC_NaveResgate | `6448cff4-2b37-4ff9-8221-8ae56d762a3f` | Crashed Rescue Ship Split Apart | 10.841 x 20 x 6.458 | 19085 | 4096 -> 2048 | complex | nave partida em 2 pedaços, deitada, comprimento ao longo de Y |
| NAT_Arbusto1 | `3af9862a-bd61-45c3-9110-03e2a03ef122` | Bioluminescent Alien Shrub | 1.124 x 1.5 x 0.848 | 18539 | 4096 -> 1024 | none |  |
| NAT_Arbusto2 | `b6f11f9d-b887-4bb9-b539-d3908093eea5` | Crystal-Thorn Fantasy Bush | 1.2 x 1.181 x 1.162 | 19073 | 4096 -> 1024 | none | arbusto de espinhos de cristal |
| NAT_Arbusto3 | `c4bddc28-4e21-4250-8e62-6d51d161154a` | Stylized Purple Alien Shrub Asset | 1.477 x 1.5 x 1.418 | 4762 | 4096 -> 1024 | none | extra (fora da lista): arbusto roxo |
| NAT_Arvore1 | `148a7d4b-ad62-4096-8ae6-dbaeafae1cc3` | Spiraling Purple Alien Tree | 6.477 x 8.239 x 10 | 4884 | 4096 -> 2048 | trunk | árvore espiral |
| NAT_Arvore2 | `1b8d315b-38f1-43cd-ad0b-37d05079402f` | Stylized Alien Mushroom Tree | 13.155 x 13.418 x 12 | 4309 | 4096 -> 2048 | trunk | árvore guarda-chuva |
| NAT_Arvore3 | `87646808-0e63-4857-bd66-5c603a98463f` | Twisted Dead Tree Fantasy Render | 4.023 x 7.75 x 8 | 19366 | 4096 -> 2048 | trunk | árvore morta |
| NAT_Arvore4 | `762503ff-3859-4f64-8e75-e3185d343ade` | Bioluminescent Alien Tree Asset | 7.652 x 9.883 x 10 | 19150 | 4096 -> 2048 | trunk | extra (fora da lista): árvore bioluminescente |
| NAT_Cogumelo | `5efd5c98-cac6-4fb0-8f91-9172c3b10398` | Glowing Red-Capped Fantasy Mushroom | 4.98 x 4.883 x 5 | 19373 | 4096 -> 2048 | trunk |  |
| NAT_Cogumelos | `ad08aa81-8f17-4f2a-88c6-2ffe5c19c409` | Glowing Fantasy Mushroom Cluster | 0.347 x 0.492 x 0.5 | 19050 | 4096 -> 1024 | none |  |
| NAT_Flor | `1289bd80-d952-465d-b550-e489556c6787` | Alien Bioluminescent Lotus Flower | 0.55 x 0.587 x 0.8 | 19091 | 4096 -> 1024 | none |  |
| NAT_Flor2 | `b6fab463-ae02-46b7-909a-daf6d92d80f3` | Alien Trumpet Blossom Cluster | 0.719 x 0.759 x 0.8 | 19364 | 4096 -> 1024 | none | extra (fora da lista): flores-trombeta |
| NAT_Pedra1 | `1cdafae4-dc49-4630-a82e-8db00eacb5c2` | Stylized Terracotta Game Rock | 0.5 x 0.48 x 0.379 | 19562 | 4096 -> 1024 | none |  |
| NAT_Pedra2 | `d191e0f5-c08d-414d-8dbe-dfa808d1ad83` | Mossy Crystal-Bound Fantasy Rock | 1.898 x 2 x 1.945 | 19261 | 4096 -> 1024 | box |  |
| NAT_Pedra3 | `cc8c2f6b-07ef-4ca8-afca-cafd0ca228ee` | Mossy Stylized Rock Fortress | 5.883 x 6 x 4.544 | 17279 | 4096 -> 2048 | complex |  |
| NAT_Penhasco | `95f5e654-3c26-49ac-be11-dfc9bf37d170` | Stylized Red Layered Cliff Wall | 13.503 x 20 x 13.346 | 4889 | 4096 -> 2048 | complex | comprimento ao longo de Y |
| NAT_Tentaculo | `5e21235c-b020-419a-b88b-a907c4e675b1` | Alien Tentacle Plant Cluster | 1.178 x 1.726 x 2 | 18666 | 4096 -> 1024 | none |  |
| NAT_Tronco | `35992113-da44-42b3-b405-4a0f4bb730bf` | Bioluminescent Alien Moss Log | 2.427 x 8 x 2.333 | 18457 | 4096 -> 2048 | box | tronco deitado ao longo de Y |

## Faltando / extras

- Todos os 53 itens da lista do plano têm modelo 3D (e todas as 56 imagens 2D têm um GLB).
- 3 extras fora da lista: `NAT_Arvore4` (árvore bioluminescente), `NAT_Flor2` (flores-trombeta), `NAT_Arbusto3` (arbusto roxo).
- Tamanhos diferentes do plano, de propósito: `CON_Barraca` 6,5 m (com 4 m a abertura teria 1,4 m de altura e o herói
  não entraria) e `MRC_Arco` 36 m (com 20 m o vão teria ~7 m e a estrada tem 12 m). Ver A-051 em ASSUMPTIONS.
- Personagens (ZMB_Comum, ZMB_Corredor, ZMB_Tanque, NPC_Sobrevivente): **sem rig**. Passos para riggar no
  relatório do agente e em A-051; o projeto já tem o pipeline de retarget (`tools/unreal/setup_mixamo.py`).

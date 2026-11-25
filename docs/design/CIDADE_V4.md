# Villa Star v4: cidade refeita por regras (A-091)

Decisões do usuário (23/11): chão = **Landscape**; portão do Kaar = **saída norte da muralha** (a arena fica lá fora);
**Bancada, Armeiro + 3 casas exploráveis** nesta etapa (Casa do herói, Casa saqueada, Bar).

Arquivos:
- Gerador (roda fora da Unreal, Python + numpy/scipy/Pillow): `tools/city/gen_city_v4.py` -> `assets/work/city_v4/`
  (`city_height.png` 16 bits, `city_height.r16`, `city_mask.png`, `city_layout.json`, `city_preview.png`).
- Chão: `tools/unreal/setup_city_landscape.py` (M_Cidade_Chao + máscara + MI no Landscape).
- Montagem: `tools/unreal/dress_city_v4.py` (lê a planta e o heightmap; refaz tudo a cada rodada; tag CidadeV4).
- Brilho e campo de força: `tools/unreal/setup_vila_glow.py` (rodar antes do dress).

## Planta (seguindo `mapa_cidade_proposta.png`)
- 400 x 400 m dentro da muralha; Landscape de 1008 x 1008 m (1 m por vértice), praça em Z = 0.
- Ruas: anel de raio 150 m (10 m) e 4 avenidas (9 m) com calçada de 2 m e meio-fio de 12 cm; 13 ruas tortas (6 m)
  do anel para os bairros; trilha de terra da porta de cada prédio até a rua.
- Prédios com função nos lugares do rascunho, de frente para a rua mais perto: Armeiro (leste), Bancada (oeste),
  Garagem, Rádio, Bar, Laboratório, Mercado (3 barracas), Armazém (pátio de contêineres), Prefeitura, Casa do herói,
  Casa saqueada. Monumento: nave no centro da praça.
- Casas: primeiro em **frente de rua** (lotes dos dois lados, a cada 17 a 20 m, recuo 3 a 6,5 m, giro ±6 graus,
  escala 0,9 a 1,15, mais densas no sul, raras perto do portão), depois poucas nos fundos. ~95 casas (antes ~200 em grade).
- Props com regra: postes no anel e nas avenidas a cada 32 m alternando lados (luz em 1 de cada 2, 40 cd); 8 na praça;
  árvores em volta da praça e numa faixa dentro do anel; jardim na frente das casas e árvore nos fundos às vezes;
  barris/geradores só perto de garagem, bancada e armazém; placa só na frente de prédio com função; ruínas nos 5 pontos
  hachurados; pedras ao pé da muralha.
- Borda: muralha com torre a cada ~48 m, portão norte com torres dos dois lados e campo de força; fora: fosso raso,
  morros até 230 m com penhascos e árvores, rio de lama tóxica a noroeste, Árvore-mãe/cristais/colmeia ao longe.
  Não dá para sair (muralha de 8,2 m) e o horizonte é mundo de verdade, não fim de mapa.
- Chão: grama alienígena + terra (borda irregular por ruído) + concreto + asfalto + lama tóxica (brilho fraco) + rocha
  nas encostas pela inclinação; duas escalas de textura contra repetição.

## Passo a passo no editor (uma vez)
1. Abrir `/Game/Levels/Remap/L_Cidade`.
2. `py "E:/game/utrazin-game/tools/unreal/setup_vila_glow.py"`.
3. Landscape (Shift+2) > **Manage** > **New** > **Import from File**:
   - Heightmap File: `E:\game\utrazin-game\assets\work\city_v4\city_height.png`
   - Location: X **-50400**, Y **-50400**, Z **0** | Rotation 0 | Scale **100, 100, 100**
   - Section Size **63x63 Quads**, Sections Per Component **1x1**, Number of Components **16 x 16**
     (Overall Resolution 1009 x 1009); Material: vazio
   - **Import**. Sair do modo Landscape (Shift+1). Ctrl+S.
4. `py "E:/game/utrazin-game/tools/unreal/setup_city_landscape.py"`.
5. `py "E:/game/utrazin-game/tools/unreal/dress_city_v4.py"`.
6. Build > Build Paths, Ctrl+S, Play.
Para mudar a cidade: editar o gerador, rodar `python tools/city/gen_city_v4.py assets/work/city_v4` e repetir 5.

## Próximo (A-092 em diante)
- Interiores: Bancada e Armeiro com o NPC dentro, Casa do herói, Casa saqueada e Bar (porta com AJRDoor, bilhetes,
  segredos). Precisa cortar a porta e montar o cômodo nas malhas (Blender) e de móveis (imagens do usuário).
- Grama em cards (imagem do usuário) via Landscape Grass Output na máscara (onde não é rua/terra).
- Malhas dos prédios com defeito (arte-vila-pendencias).

## v5 (A-096/A-097, 23/11): 200 x 200 m, relevo, interiores e bicicleta
Gerador `tools/city/gen_city_v5.py` -> `assets/work/city_v5/` (os scripts da Unreal usam a v5 quando ela existe).
Landscape: `city_v5/city_height.png`, Location **-25200, -25200, 0**, Scale **100, 100, 100**, Section Size **63x63**,
Sections Per Component **1x1**, Number of Components **8 x 8** (resolução 505 x 505).
Ordem no editor (L_Cidade aberta):
1. compilar (compilar_remap.bat): AJRInteriorPortal, AJRBike, guardas da bicicleta no JRCharacter;
2. `import_user_assets.py` (traz SM_VEH_BikeQuadro e SM_VEH_BikeRoda);
3. `fix_city_landscape.py`: apaga o Landscape de 1008 m e diz os números; importar o novo (acima); rodar de novo:
   ele confere, roda `setup_city_landscape.py`, `dress_city_v4.py` e `build_interiors_vila.py`;
4. Build > Build Paths, Ctrl+S, Play.

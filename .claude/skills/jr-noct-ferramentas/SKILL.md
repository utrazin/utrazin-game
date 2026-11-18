---
name: jr-noct-ferramentas
description: Ponto de entrada para gerar ou conferir assets do Jogo de Resgate com as ferramentas Noct (Forge 3D, Forge 2D, Noct3DViewer, GamejamProject). Use sempre que o pedido for criar um modelo 3D, prop, icone, HUD, sprite, efeito, textura, animacao de objeto, inspecionar um FBX/Mixamo ou revisar o design de uma mecanica, ANTES de modelar no chute.
---

# Ferramentas Noct no Jogo de Resgate

Regra principal: quando precisar de um asset, nao invente geometria ou imagem "na mao" dentro da Unreal nem no chute. Escolha a ferramenta abaixo, gere com receita salva, confira, entregue no repositorio e importe com o script do projeto.

Mapa completo do processo: `docs/pipeline/NOCT_TOOLS.md`.

## Onde as ferramentas ficam

Fora do repositorio, em `E:\game\noct-tools\` (as licencas proibem redistribuir, e o repositorio vai para o GitHub):

| Pasta | Ferramenta | Para que serve |
|---|---|---|
| `forge3d\` | Noct Asset Forge 3D (Python) | Props, pecas de cenario, personagens estilizados com esqueleto, animacao de objetos, texturas pintadas. Sai GLB. |
| `forge2d\` | Noct Asset Forge 2D v2.5 (TypeScript) | Icones de HUD, roda de itens, pinos do minimapa, placas e cartazes (decal), sprites animados de efeito. Sai PNG + JSON de atlas. |
| `viewer3d\Noct3DViewer.exe` | Visualizador | Abrir FBX/GLB (Mixamo, Blender, Tripo) e ver ossos, escala e animacao ANTES de importar. Licenca so uso pessoal nao comercial. |
| `gamejam\.agents\skills\` | Skills de design | Critica de design (red team), QA, direcao de arte. Usar como referencia de processo. |

Se a pasta nao existir: `powershell -ExecutionPolicy Bypass -File tools\noct\setup_noct_tools.ps1`.

## Qual skill usar

| Pedido | Skill |
|---|---|
| Modelo 3D, prop, movel, peca de cenario, personagem estilizado, animacao de objeto (porta, bau, bandeira) | `jr-asset-3d` |
| Icone, HUD, UI, placa, cartaz, sprite de fogo/fumaca/faisca | `jr-asset-2d` |
| "Essa animacao/modelo esta certo?", Mixamo novo, osso com escala estranha | `jr-inspecionar-animacao` |
| Mecanica nova, revisar design, plano de teste | `jr-design-critica` |

## Regras que valem sempre

1. Nunca copiar codigo das ferramentas Noct para dentro do repositorio. So entram no repositorio: as receitas que NOS escrevemos (`assets/source/forge3d|forge2d`), os arquivos gerados (`assets/work/forge3d|forge2d`) e os scripts `tools/noct/*`.
2. Todo GLB do Forge 3D passa pelo bake de escala (`tools/noct/entregar_asset.py glb ...`). Sem isso o no raiz vem com escala 0.0625 e personagem quebra igual aos zumbis (Hips em escala 100).
3. Toda importacao na Unreal passa por `tools/unreal/import_forge_asset.py`: confere tamanho, cria colisao (UCX nao funciona neste projeto, A-078), confere osso raiz e Physics Asset.
4. Nomes: `SM_` malha estatica, `SK_` com esqueleto, `T_` textura, `T_Icone_` icone de HUD, `FB_` flipbook.
5. Escala do Forge 3D: 16 unidades = 1 m. Galao de 51 cm = 8,2 unidades de altura. Personagem de 1,80 m = 28,8 unidades.
6. Estilo: o Forge 3D faz low poly / estilizado. Se o asset tem que combinar com modelos realistas (Tripo), avisar o usuario antes (decisao aberta OD-P09).
7. Separar sempre: gerado / conferido na nuvem / importado / visto no Play. Pedir print do Play.
8. Respostas em pt-BR, passos numerados, nunca usar o travessao.

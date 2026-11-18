---
name: jr-inspecionar-animacao
description: Conferir um modelo ou animacao (FBX do Mixamo, rig exportado do Blender, GLB do Forge 3D ou do Tripo) no Noct3DViewer antes de importar na Unreal; achar escala errada de osso, nomes de ossos e retarget quebrado.
---

# Inspecionar modelo e animacao antes da Unreal

Ferramenta: `E:\game\noct-tools\viewer3d\Noct3DViewer.exe` (executavel, nao precisa instalar nada).
Licenca: SO uso pessoal e nao comercial. Se o jogo for vendido, parar de usar (decisao aberta OD-P10). Os arquivos do jogo nao dependem dele, e so para olhar.

O visualizador e uma janela: o Claude nao le o resultado sozinho. Ou o usuario manda print, ou o Claude usa a tela dele (computer use), sempre pedindo acesso.

## Quando usar

- Antes de importar animacao nova do Mixamo para os zumbis ou o heroi.
- Quando uma animacao retargetada "some com o corpo" ou estica: e o sintoma do osso raiz com escala diferente de 1 (Hips em escala 100, ver handoff B6).
- Para comparar o rig reexportado do Blender com o antigo.

## Passo a passo

1. Copiar o arquivo para `viewer3d\assets\models\` (modelo) ou `viewer3d\assets\animations\` (clipe). Ou importar pela interface.
2. Abrir `Noct3DViewer.exe`.
3. Na Hierarchy, clicar no osso raiz (Hips ou root) e olhar o Inspector: escala tem que ser 1, 1, 1. Se for 100 ou 0,01, o FBX esta com unidade errada: reexportar do Blender com escala aplicada antes de importar.
4. Tocar a animacao na Timeline (0,25x ajuda a ver pe deslizando e joelho virando).
5. Testar o retarget automatico do viewer com o modelo do jogo: se ate no viewer o corpo quebra, o problema esta no arquivo, nao na Unreal.
6. Anotar o resultado (print) no relatorio de QA (`docs/qa/reports/`).

Mixamo: baixar em FBX, "Without Skin" para clipes, e colocar na pasta `assets\animations` do viewer.

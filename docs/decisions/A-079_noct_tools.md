# Texto para colar em docs/decisions/ASSUMPTIONS.md e OPEN_DECISIONS.md

## ASSUMPTIONS.md

**A-079** Ferramentas Noct integradas ao pipeline (17/11/2026).
- Forge 3D, Forge 2D, Noct3DViewer e GamejamProject ficam fora do repositorio em `E:\game\noct-tools\` (licencas proibem redistribuir; repositorio vai para o GitHub). Entram no repositorio so as nossas receitas (`assets/source/forge3d|forge2d`), os arquivos gerados (`assets/work/forge3d|forge2d`), `tools/noct/*`, `tools/unreal/import_forge_asset.py` e as skills `.claude/skills/jr-*`.
- Todo GLB do Forge 3D passa por `tools/noct/bake_glb_scale.py` (via `entregar_asset.py`): o forge exporta com `scale 0.0625` no no raiz e ossos em unidades do forge (16 = 1 m), o mesmo tipo de problema do Hips em escala 100 dos zumbis.
- Toda importacao de asset Noct passa por `import_forge_asset.py`, que cria colisao caixa quando nao ha nenhuma (A-078: UCX ignorado) e confere escala do osso raiz e Physics Asset.
- Palpites ainda nao confirmados: frente +Z do forge chega certa na Unreal; Interchange cria Physics Asset para SK_ em GLB.

## OPEN_DECISIONS.md

**OD-P09** Estilo dos assets do Forge 3D (low poly/estilizado) junto dos modelos realistas do Tripo.
- A: usar o Forge 3D so para props de fundo e interiores, texturizados para nao destoar.
- B: usar para tudo que for novo e aceitar a mistura.
- C: migrar o jogo aos poucos para estilizado (combina com o Forge e reduz custo).

**OD-P10** O Noct3DViewer so pode ser usado em projeto pessoal e nao comercial. O jogo vai ser vendido?
- A: projeto pessoal: usar normalmente.
- B: vai ser vendido: usar so ate decidir; inspecionar FBX pelo Blender/Unreal depois.

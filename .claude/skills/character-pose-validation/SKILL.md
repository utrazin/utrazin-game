---
name: character-pose-validation
description: Use quando mãos, pés ou armas estão fora de posição, o encaixe de arma falha, o personagem treme em terreno irregular, ou a arma some em primeira pessoa. Define validação por sockets, IK e viewmodel.
---

# /character-pose-validation

Garante mãos no lugar certo em todas as poses e armas visíveis em qualquer câmera.

## Pré-requisitos
- Rig e animações importados; arma com sockets (`hand_r_weapon`, `hand_l_foregrip`) em `docs/gameplay/ANIMATIONS.md`
- `tools/blender/grip_check.py` (já existe) e `blender-rigging`

## Passos
1. **Mapa de encaixe**: por arma, escreva o socket da mão direita e o ponto da mão esquerda (empunhadura, coronha). Offsets ficam no Data Asset da arma, não no código.
2. **Verificação em Blender**: por animação (idle, andar, correr, mirar, atirar, recarregar), amostre quadros-chave e meça a distância mão-socket. Meta: <= 2 cm no idle e na mira, <= 5 cm em corrida. Salve JSON em `reports/` (formato de `grip_check_*.json`).
3. **IK de mão**: aplique Two Bone IK ou Control Rig para a mão esquerda seguir o socket de empunhadura; deixe a direita no socket. Na Unreal, no ABP, camada `UpperBody` (Layered Blend per Bone em `spine_01`) para tiro e mira sem quebrar as pernas.
4. **Retargeting**: ao retargetar (`RTG_*`), confira a chain de braços e dedos; pose de bind compatível; rode a checagem do passo 2 nos dois heróis. Erro de um rig não se aplica ao outro (Victoria tem coluna reta).
5. **Primeira pessoa**: a arma e os braços ficam sempre visíveis na frente. Opções por ordem: (a) malha de braços e arma só para a câmera de primeira pessoa; (b) recurso de renderização em primeira pessoa da própria engine (confirme a API na 5.8.4); (c) empurrar o conjunto para frente e para cima. Inclua respiração parada, balanço no ritmo da corrida e subida na mira.
6. **Terreno**: tremedeira ao andar vem de degraus nas emendas da colisão, `MaxStepHeight`, `WalkableFloorAngle` ou IK de pé; teste cada hipótese isolada e registre o resultado.
7. **Evidência**: prints de 6 poses por arma e herói em `docs/qa/reports/`.
8. Rode `/visual-qa-gate`.

## Ferramentas necessárias
- Blender, `tools/blender/grip_check.py`, Unreal (ABP, Control Rig)

## Diretórios afetados
- `unreal/JogoResgate/Content/Characters/`, `tools/blender/`, `docs/gameplay/ANIMATIONS.md`, `reports/`

## Verificações
- JSON de grip sem violações acima da meta em todas as poses
- Arma visível em primeira pessoa parado, correndo e mirando
- Sem tremedeira em teste de caminhada de 30 s no pior trecho do mapa

## Erros comuns
- Corrigir só o idle e esquecer correr e mirar
- Aplicar offset no código em vez de no Data Asset
- Ajustar o rig de um herói e quebrar o outro

## Critério de sucesso
Todas as armas e heróis passam na checagem de grip, e a arma aparece em primeira pessoa em todas as ações.

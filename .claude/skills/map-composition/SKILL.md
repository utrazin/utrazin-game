---
name: map-composition
description: Use para compor ou refazer o mapa de uma fase (morros, biomas, estradas, vegetação, rochas, props): hierarquia macro/meso/micro, motivos narrativos, espaçamento e exclusão entre objetos, prévias antes de aplicar.
---

# /map-composition

Transforma "objetos jogados no mapa" em um lugar coerente, sem sobreposição.

## Pré-requisitos
- Roteiro da fase (`docs/gameplay/L01_STORYBOARD.md`) com zonas, rota e landmarks
- Registro de posicionamento (`tools/pipeline/placement_registry.py`) acessível aos scripts de colocação

## Passos
1. **Macro (forma)**: terreno em camadas (vale, rota, cristas, morros). Defina onde o jogador passa, o que vê de longe e o que fica proibido (encostas íngremes sem acesso). Morro não é vazio: tem trilha, afloramento de rocha seguindo a crista, vegetação por inclinação e altitude.
2. **Meso (lugares)**: landmarks visíveis de longe (nave, torre, posto), vilas, acampamentos, ruínas de acidente. Cada lugar tem um motivo (`reason`) e uma silhueta própria.
3. **Micro (detalhe)**: props em grupos com história (carro batido + cones + mala aberta), nunca um por um aleatório. Entulho segue a rota; vegetação circunda e emoldura.
4. **Registro de footprints**: todo script que coloca objeto (`build_l01.py`, `scatter_l01*.py`, `l01_user_dressing.py`) consulta e grava no registro (x, y, raio, tag, motivo). Antes de colocar, `registry.can_place(...)`; vegetação usa `poisson_sample(...)` com o raio da malha.
5. **Exclusão**: estradas, trilhas, portas de prédios, pontos de spawn e checkpoints reservam corredores. Nada atravessa nada.
6. **Paleta e transição**: uma paleta por bioma; bordas entre biomas com mistura (pintura de camadas do terreno, vegetação de transição). Evite repetir a mesma textura no morro (use variação e escala).
7. **Limpeza**: remova o que não pertence à versão atual (tags antigas) antes de reconstruir. Anote o que saiu.
8. **Prévia obrigatória**: render de cima e de olho de herói (170 cm) por zona. Mostre ao usuário e só aplique com OK.
9. Rode `/visual-qa-gate`.

## Ferramentas necessárias
- `tools/pipeline/placement_registry.py`, scripts de `tools/unreal/` e `tools/blender/plot_l01_v3.py`, `scatter_l01_v3.py`

## Diretórios afetados
- `tools/unreal/`, `tools/blender/`, `reports/`, `docs/gameplay/LEVELS.md`

## Verificações
- Zero pares sobrepostos no registro (`registry.find_overlaps()` vazio)
- Cada objeto de marco/prop tem `reason`
- Prévias aprovadas pelo usuário antes da aplicação em massa

## Erros comuns
- Espalhar rochas e árvores sem relação com o terreno
- Ignorar o raio real da malha ao colocar
- Reconstruir sem apagar a versão anterior

## Critério de sucesso
Mapa legível de cima e do chão, sem sobreposição, sem restos antigos, com o usuário tendo aprovado as prévias.

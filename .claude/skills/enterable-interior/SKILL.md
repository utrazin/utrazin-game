---
name: enterable-interior
description: Use para criar ou revisar construções onde o jogador entra (posto de gasolina, loja, galpão, contêiner): tamanho, interior com props interativos, luz, colisão, câmera em espaço fechado e decisão de quais prédios ficam fechados.
---

# /enterable-interior

Garante que todo lugar com porta tenha dentro algo que justifique entrar.

## Pré-requisitos
- Papel do lugar no roteiro (`docs/gameplay/L01_STORYBOARD.md`): o que o jogador ganha ali
- Escala do herói (cápsula Unreal, ~34 cm de raio e ~88 de meia altura; confirme no Blueprint)

## Passos
1. **Decida: entrável ou fechado.** Só é entrável se o roteiro dá uma recompensa (item, história, abrigo, perigo). Senão fica fechado de verdade (sem porta aberta, sem vão) e com fachada convincente.
2. **Dimensione.** Referência mínima: porta 120 x 220 cm; pé-direito 280 a 320 cm; corredores >= 150 cm; loja de posto >= 10 x 7 m, com balcão, caixa, 4+ prateleiras, geladeira, depósito ou banheiro. Contêiner entrável: 2,4 x 2,6 x 6 m com as duas pontas abertas ou uma porta.
3. **Programa de interior** (lista do que existe): cada espaço tem >= 1 interação (saque, chave, história, armadilha), >= 3 props de contexto, 1 ponto focal visível da porta.
4. **Modele em casca oca** no Blender (`blender-prop-artist`, `blender-scene-assembly`): paredes com espessura real (>= 20 cm), teto, piso, batentes. Nunca um cubo com a porta pintada.
5. **Colisão**: paredes/piso/teto com colisão simples por caixas (`blender-collision-proxy`), vão da porta livre, props com colisão própria; confirme que o herói e o carro (se couber) passam.
6. **Luz**: teto fecha a luz do céu; 1 a 3 luzes pontuais ou retangulares com raio curto e intensidade baixa, cor coerente (fluorescente fria, lanterna quente), `Post Process Volume` de interior com exposição fixa. Sem luz dentro de malhas.
7. **Câmera**: um volume de câmera cobre o interior e encurta o braço (`camera-systems`, `/camera-shots-and-cutscenes`): braço 150 a 220 cm, inclinação limitada, colisão ligada; a câmera nunca fica no teto.
8. **Dressing**: 3 camadas (grandes, médias, detalhes) com `/map-composition` para espaçamento; nada flutuando, nada sem textura.
9. **Teste do olho do herói**: renderize ou grave da porta e de dentro (170 cm); confirme que a câmera de terceira pessoa mostra o personagem.
10. Revise no `docs/gameplay/LEVELS.md` a lista de entráveis vs fechados e rode `/visual-qa-gate`.

## Ferramentas necessárias
- Blender e scripts de `tools/blender/`; scripts de `tools/unreal/` (`build_l01.py` como ponto de integração)

## Diretórios afetados
- `blender/scenes/`, `assets/work/`, `unreal/JogoResgate/Content/Levels/`, `docs/gameplay/LEVELS.md`

## Verificações
- Cada entrável tem lista de interações e props escrita e conferida
- Herói entra, anda e sai sem travar; câmera ok dentro
- Prédios fechados não têm porta aberta

## Erros comuns
- Interior oco por falta de roteiro
- Prédio menor que o herói precisa (porta apertada, teto baixo)
- Câmera de 3ª pessoa por cima do telhado

## Critério de sucesso
Todo prédio com porta aberta tem interior com interação, luz e câmera corretos, e o `visual-qa-gate` passa.

---
name: intro-sequence
description: Use para criar a abertura do jogo: tela de start, botão Jogar, herói na nave perdendo o controle, queda, nave caída e herói ao lado, depois entrega do controle com objetivo. Também serve como modelo para cenas de abertura de outras fases.
---

# /intro-sequence

Abertura em atos, com Sequencer, sem teletransporte do jogador.

## Pré-requisitos
- Modelo da nave e do herói em `assets/` com licença registrada; mapa da fase com ponto da queda
- `/camera-shots-and-cutscenes` lido

## Passos
1. **Ato 0, Start**: mapa de menu com câmera lenta ao redor de algo icônico; menu com Jogar, Opções, Sair (pt-BR, String Table); música de menu (`/music-production-acestep` se instalado).
2. **Ato 1, Cabine**: fade in; herói na nave, alarmes, luz vermelha, tremor leve. Plano médio frontal, 6 a 8 s.
3. **Ato 2, Perda de controle**: plano externo da nave descendo desgovernada (spline ou keyframes), cabine com tremor forte, faíscas Niagara, áudio de falha de motor. 8 a 12 s.
4. **Ato 3, Impacto**: corte seco no impacto, tela branca curta, camera shake, poeira e fumaça, silêncio de 1 s com zumbido.
5. **Ato 4, Pós-queda**: plano aberto da nave caída em chamas e destroços; corte para o herói em pé ao lado, dando o primeiro passo. 6 a 10 s.
6. **Entrega de controle**: blend de 1 s para a câmera do jogo, input liberado, objetivo na HUD ("Procure ... " conforme a primeira tarefa da zona 1).
7. **Salvar estado**: flag `IntroSeen` em `USaveGame`; botão de pular (segurar) vai direto ao Ato 4 final com tudo posicionado.
8. **Teste**: rode pulando e sem pular; confirme herói, câmera, HUD e objetivo idênticos nos dois casos.
9. Rode `/visual-qa-gate`.

## Ferramentas necessárias
- Unreal Sequencer, Niagara, Audio; Blender para pré-visualizar planos

## Diretórios afetados
- `Content/Cinematics/Intro/`, `Content/UI/Menus/`, `Source/JogoResgate/` (flag no save), `docs/gameplay/CAMERA_SHOTS.md`

## Verificações
- Duração total <= 60 s e pulável
- Controle devolvido sem salto de câmera
- Objetivo inicial coerente com a primeira tarefa

## Erros comuns
- Jogador surgindo no mapa sem explicação
- Cutscene que não pode ser pulada
- Objetivo da HUD diferente da tarefa real

## Critério de sucesso
Do clique em Jogar até o primeiro controle, a sequência roda inteira, é pulável e entrega o jogador no estado certo.

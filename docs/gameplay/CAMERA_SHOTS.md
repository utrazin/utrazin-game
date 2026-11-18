# Planos de câmera e cenas

## Abertura da fase 1 (A-074)

Dirigida em C++ por `AJRIntroDirector` (`Source/JogoResgate/Cinematics/`), sem Level Sequence. O ator fica no mapa
L01 no ponto onde o herói aparece (ao lado da nave caída, do lado do acampamento) e é posto por
`tools/unreal/setup_intro.py`. O desenho por cima (menu, faixas, legendas, aviso de pular, preto e branco) é do
`AJRIntroHUD` (filho do `AJRHUD`). Storyboard: `assets/work/intro/previews/intro_storyboard.png`
(gerado por `tools/blender/preview_intro.py`, formas simples).

| Ato | Duração | Plano | Câmera | Som |
|---|---|---|---|---|
| 0 Tela de start | até escolher | geral alto, girando 3 graus/s sobre o vale | órbita de raio 9x o tamanho da nave, lente 70 | música do menu |
| (transição) | 0,8 s | escurece | mesma órbita | música some |
| 1 Cabine | 7 s | plano médio na frente-direita do nariz, nave nivelada a ~90 m | presa na nave, tremor leve crescente | motor, vento, bipe de alarme; luz vermelha pulsando |
| 2 Perda de controle | 10 s | 6,5 s do acampamento (teleobjetiva seguindo a nave) + 3,5 s de perseguição atrás da nave | chão: lente 28 a 50; perseguição: 70 a 88, tremor forte | explosão no motor, faíscas, motor engasgando, música de tensão |
| 3 Impacto | 3 s | corte seco para plano aberto da queda | clarão branco 0,35 s, tremor forte que some | estrondo, ~1 s de silêncio, depois o fogo |
| 4 Pós-queda | 4,5 s + 4,5 s | geral girando 28 graus em volta da nave em chamas; corte para o herói de frente, nave atrás | no herói: ele dá os primeiros passos e a câmera dá a volta até atrás dele | fogo |
| 5 Entrega | 1 s | blend para a câmera do jogo | `SetViewTargetWithBlend` EaseInOut | música do jogo |

Total do clique em Jogar até o controle: ~31 s (limite 60 s). Todos os tempos são propriedades do ator.

Regras:
- Pular: segurar Espaço, Enter, A ou Start por 1 s (barra no canto). Tela preta, tudo no estado final, mesma entrega.
- IntroSeen no save (v2): depois da primeira vez "Jogar" já pula; "Ver abertura" mostra de novo. Console `JRAbertura`
  apaga a flag e recomeça a fase.
- A entrega dispara o gatilho `Historia_Z0_Queda` (fala + tarefa "Pegue o graveto"), igual a entrar nele.
- Zumbis ficam parados (CustomTimeDilation 0) e o herói não toma dano durante o menu e a abertura.
- Renascer depois de morrer nunca mostra a abertura. Jogo aberto com checkpoint no meio da fase: só a tela de start
  (Continuar / Sair).

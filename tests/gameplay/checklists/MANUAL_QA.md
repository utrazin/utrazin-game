# QA manual obrigatório (20 passos)

Build: ______ Commit: ______ Data: ______ Testador: ______

| # | Passo | Esperado | Resultado (ok/falha/não executado) | Evidência |
|---|---|---|---|---|
| 1 | Carregar a fase | Mapa carrega sem erros no log; jogador no carro | | |
| 2 | Dirigir e frear | Acelera, freia e faz curva com resposta previsível | | |
| 3 | Subir e descer terreno | Sobe rampas íngremes sem travar; suspensão absorve | | |
| 4 | Danificar pneu | Pneu furado muda dirigibilidade e aparece no HUD | | |
| 5 | Chegar ao checkpoint | Toast de checkpoint; save gravado | | |
| 6 | Sair animadamente do carro | Animação de saída; carro para; 1 personagem apenas | | |
| 7 | Controlar personagem | Andar, correr, pular, câmera | | |
| 8 | Mirar, disparar e recarregar | Munição desconta; recarga respeita reserva | | |
| 9 | Receber dano e morrer | Barra cai; morte dispara tela/fluxo de falha | | |
| 10 | Carregar checkpoint | Volta ao último checkpoint com estado correto | | |
| 11 | Acionar inimigos por distância | Inimigos fora do raio ficam em idle/patrulha | | |
| 12 | Concluir a horda | Ondas progridem; sem spawn visível | | |
| 13 | Libertar a vítima | Interação abre a cela só no estágio Rescue | | |
| 14 | Executar abraço | Animação sincronizada de ambos | | |
| 15 | Concluir fase | Tela de conclusão; fase seguinte desbloqueada | | |
| 16 | Salvar e reabrir progresso | Fechar o jogo e reabrir mantém progresso | | |
| 17 | Trocar personagem e skin | Troca no menu sem perder progresso | | |
| 18 | Conferir HUD e minimapa | Vida, carro, munição, objetivo, minimapa corretos | | |
| 19 | Verificar performance | `stat unit` dentro do budget (RENDERING.md) | | |
| 20 | Executar build standalone | Build Win64 abre e completa a fase | | |

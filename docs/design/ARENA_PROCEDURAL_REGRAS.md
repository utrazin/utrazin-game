# Arena procedural: regras de posicionamento por item (A-089)

Código: `Source/JogoResgate/Remap/JRArenaLayout.*` (planta, lógica pura) e `JRArenaGenerator.*` (troca as células por peças).
Teste: `Automation RunTests JR.Remap.ArenaLayout`. Simulação da lógica em Python: `tools/sim/layout_sim.py` (roda em ~2 min).

## 1. De onde vêm as regras

- Gerador bom de arena não espalha peça solta: usa **regras de designer** ("isto perto daquilo", "isto nunca no meio")
  e deixa o resto variar (linha de "Fast Procedural Level Population With Playability Constraints", Horswill e Foged).
- Peças grandes primeiro, depois as menores (quanto mais coisa no mapa, menos lugar sobra).
- Grupos prontos de peças (**assemblies**, como no Electric Dreams da Epic) dão lógica aos cenários: posto, pátio de
  contêineres, ferro-velho.
- Arena de horda precisa de **espaço aberto** (a IA e o jogador desviando) e de corredores largos: a horda funciona como
  parede móvel. Corredor estreito e beco viram ponto de "acampar".

## 2. Construções

Nada que pareça ter interior e não tenha. Saíram as cabanas/casas fechadas. Ficam: posto (dá para passar por baixo da
cobertura, a loja é de costas para o muro), contêineres, carcaças de carro e ônibus, barricadas, rochas.

## 3. Grade e zonas

Grade de 8 m. Planta = molde (círculo, cruz, U, dois pátios, rua com becos) com muralha em volta.

| Zona | Onde | O que pode |
|---|---|---|
| Central | raio 2 células (16 m) em volta do início | nada; pilar natural só se não houver outro jeito de quebrar a visão |
| Borda | 1 a 2 células do muro | conjuntos temáticos, cobertura alta comum, baús, surgimento de zumbis |
| Meio | o resto | cobertura baixa em grupos, pilares naturais, ninhos |

## 4. Conjuntos temáticos

Molde de cada um (linha 0 colada no muro; S alta, L baixa, Y livre, C vaga do baú):

```
Posto        Pátio        Ferro-velho   Acampamento
SS  (loja)   SSS          SYS           LL
YY  (cober-  SCY          YCL           CY
YY   tura)
```

Regras: linha de trás encostada no muro; frente (a linha logo depois) livre e reservada como caminho; folga de 1
célula entre conjuntos; pelo menos 70 graus entre eles (vistos do centro); centro do conjunto a 45% do raio ou mais;
fora da zona central; nada pode fechar uma área (flood fill). Quantidade: 2 até 96 m, 3 até 128 m, 4 acima. O posto
entra primeiro em 75% das arenas.

## 5. Regras por item

| Item | Regra |
|---|---|
| Cobertura alta comum (carro, contêiner) | só até 2 células do muro; grupos nunca encostam em outra cobertura (corredor de 8 m) |
| Cobertura baixa (barricada, cerca, tronco, barris) | qualquer lugar fora da zona central |
| Pilar (quebra de visão no meio) | rocha/penhasco, giro livre; nunca prédio ou carro |
| Baú | vaga de um conjunto (protegida, 2 acessos); senão colado no muro, a 40% do raio, 2 acessos, 4 células de outro baú, 2 de ninho |
| Ninho | de preferência a 2+ células do muro e sem cobertura nas 8 células em volta; colisão em cápsula não andável |
| Surgimento de zumbi | longe do centro, de preferência colado no muro |
| Nave (extração) | uma por quadrante, longe do centro, com espaço em volta |

## 6. Conferência (recusa e tenta outra semente)

Tudo alcançável a partir do início; nenhuma linha reta de visão maior que 64 m; 3+ saídas do centro; zona central
sem cobertura (exceto pilar); baú com 2 acessos; conjunto encostado no muro; 60% de área livre ou mais; pontos
especiais sem sobreposição. Depois de 12 tentativas: plano B (círculo só com as quebras de visão).

## 7. Kit (Groups de cada peça)

Contêiner: Geral, Pátio. Carros batidos: Geral, Ferro-velho. Ônibus: Ferro-velho. Pedra3 e Penhasco: Natureza (pilares).
Barricada e Cerca: Geral, Acampamento. Tronco: Geral, Natureza. Barril: Geral, Ferro-velho, Acampamento.
Gerador: Acampamento. Pedra2: Geral, Natureza.

## 8. Próximos passos

- Temas novos de conjunto (laboratório alien, ninho grande, torre de rádio) quando houver modelos.
- Rampa ou NavLink nas peças escaláveis para o zumbi seguir por cima (hoje ele pula: A-088).
- Densidade de decoração por zona (mais entulho perto dos conjuntos, chão limpo no centro).

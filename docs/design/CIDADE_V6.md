# Villa Star v6: cidade com ruas, bairros e Árvore-Mãe (A-098)

Prévia: `assets/work/city_v6/city_preview.png`. Gerador: `tools/city/gen_city_v6.py`. Montagem: `tools/unreal/dress_city_v6.py`.

## Planta
- Muralha 200 x 200 m, portão do Kaar no norte (arena lá fora).
- Grade de ruas nas linhas -84, -42, 0, 42 e 84 m. Avenidas em x=0 e y=0 (8 m + calçada de 2 m), demais ruas com 6 m + 1,5 m. Praça redonda de 16 m no centro, com a nave de monumento.
- 16 quarteirões de ~32 x 32 m, cada um com 4 lotes. Toda casa fica de frente para uma rua (avenida primeiro), com recuo, jardim na porta e quintal no fundo.

## Bairros (nível de arena que abre)
| Bairro | Arena | O que tem |
|---|---|---|
| Praça Central | 1 | Armeiro (Krug), Bar, Bancada (Ix-Vel), Casa do herói, Garagem, Jardim da Árvore-Mãe, Rádio, Quartel, portão |
| Mercado Leste | 2 | 8 barracas em fileira no calçadão, Prefeitura |
| Vila Sul | 3 | residencial, Casa saqueada |
| Armazém | 3 | contêineres em fileiras, alguns empilhados |
| Oficinas Oeste | 4 | 2 oficinas com carro em conserto, geradores e barris |
| Ruínas do Ataque | 4 | entulho, ossos, cristais e carros batidos onde eram casas |
| Laboratório | 5 | laboratório e o cristal no pátio |
| Ferro-velho | 5 | fileiras de carros batidos, alguns empilhados |

## Como destrava
- O bairro abre quando a arena do nível dele abre no portão do Kaar (nível novo a cada 6 ondas de recorde).
- Bairro fechado: muro de contêineres de 3,3 m (o herói escala até 2,65 m) na metade da rua do lado fechado, entrando na muralha. Nada de parede invisível.
- Posto com placa e luz no cruzamento mais perto da praça. E no posto diz quantas ondas faltam.
- Na primeira visita depois de liberar, as barricadas tremem e afundam, aparece "BAIRRO LIBERADO" e a câmera treme.

## Árvore-Mãe
- No jardim noroeste da praça. E abre a árvore de melhorias permanentes, paga com cristais da arena.
- Galhos: Fúria (dano, cadência, cura por abate), Casca (vida, menos dano, munição), Raízes (créditos, cristais, cartas no começo) e Vento (velocidade, energia).
- Cristais por corrida: (ondas + 2 x objetivos) x (1 + 0,15 x (setor - 1)). Morrendo, fica 25%.

## Testar (console)
- `JRRecorde 12`: libera a arena 3 e abre na hora os postos liberados.
- `JRCristais 50`: dá cristais para a árvore.

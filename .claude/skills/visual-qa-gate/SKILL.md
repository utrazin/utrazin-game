---
name: visual-qa-gate
description: Use antes de dar qualquer entrega visível como pronta (mapa, prop, interior, câmera, luz). Portão de qualidade com os defeitos recorrentes do jogo: sem colisão, flutuando, sem textura, sobreposto, brilho estourado, câmera no chão.
---

# /visual-qa-gate

Checklist objetiva de aceite visual e de jogabilidade. Falhou em qualquer item bloqueante: não está pronto.

## Pré-requisitos
- Build ou relatórios de `tools/unreal/*.py` disponíveis (`reports/*.json`) e prints ou renders do resultado
- Se o usuário é quem roda a Unreal: peça os prints/relatórios em vez de afirmar

## Passos
1. **Colisão (bloqueante)**: tudo sólido bloqueia o jogador; objetos pequenos têm física ou colisão simples; nada atravessa o herói; terreno bloqueia o canal da câmera.
2. **Posição (bloqueante)**: nenhum item flutuando (exceto o que o roteiro justifica); pickups no chão ou sobre superfície; nada enterrado.
3. **Material (bloqueante)**: nenhuma malha com material de reserva (branco/cinza padrão); toda malha tem textura; sem estouro de brilho (ver `/material-lighting-audit`).
4. **Sobreposição (bloqueante)**: nenhuma árvore, rocha ou prop atravessando outro (`tools/pipeline/placement_registry.py`).
5. **Motivo (alto)**: cada objeto tem razão de estar ali (rota, ruína, acampamento). Restos de versões antigas removidos.
6. **Espaços fechados (bloqueante)**: tem interior real, porta transitável (>= 120 cm), props, luz e câmera ajustada (`/enterable-interior`).
7. **Câmera (bloqueante)**: nunca vê abaixo do terreno nem dentro de malhas; ações com troca de câmera têm animação e ângulo definidos (`/camera-shots-and-cutscenes`).
8. **Personagem (alto)**: mãos no encaixe da arma em idle, andar, correr e mirar (`/character-pose-validation`); sem tremedeira em terreno irregular.
9. **Áudio (médio)**: som combina com a ação; música com loop sem emenda; volumes balanceados.
10. **UI (médio)**: objetivo atual coerente com a tarefa da zona; marcador de interação visível.
11. **Registre** em `docs/qa/reports/` data, build, itens aprovados/reprovados e evidências.

## Ferramentas necessárias
- Relatórios em `reports/`, prints, `python tools/pipeline/validate_pipeline.py`

## Diretórios afetados
- `docs/qa/reports/`

## Verificações
- Todos os itens bloqueantes marcados com evidência (arquivo ou print)
- Itens não testáveis aqui marcados "pendente de validação manual", nunca "ok"

## Erros comuns
- Aprovar pela leitura do script em vez do resultado no jogo
- Esquecer o ponto de vista do jogador (olho a 170 cm), só vendo a cena de cima

## Critério de sucesso
Relatório em `docs/qa/reports/` com todos os bloqueantes aprovados, ou lista de reprovações com dono e correção.

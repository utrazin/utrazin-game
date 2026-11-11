# Roadmap

O MVP de lançamento contém **3 fases**. A primeira meta executável é o **vertical slice da Fase 1**. Mapas finais das fases 2 e 3 só depois de M2 validado.

## M0 Fundação (atual)

**Entregas**: estrutura do repositório, documentação base, Art/Audio Bible provisórias, manifesto + schema, scripts de pipeline com testes, agentes/skills/rules/hooks, CI, esqueleto C++ (não compilado).

**Aceite**
- [x] Estrutura criada conforme prompt mestre (raiz = `utrazin-game`, A-027)
- [x] Documentação inicial sem TODO genérico
- [x] Scripts Python testados (`pytest` verde no ambiente de criação; CI roda no primeiro push)
- [x] Regras, agentes, skills e hooks configurados; `settings.json` válido
- [x] Política de licenças definida
- [ ] Ambiente local inspecionado (`check_environment.py` no PC do usuário)
- [ ] Unreal 5.8.4 + VS instalados e projeto compilado uma vez (log em `docs/qa/`)
- [ ] Usuário revisou ASSUMPTIONS e respondeu decisões que bloqueiam M1

## M1 Greybox

**Aceite**
- Carro controlável (acelera, freia, curva) em terreno irregular com subidas e descidas
- Suspensão responde a irregularidades; dano simplificado (integridade global + 1 pneu)
- Checkpoint principal com transição carro para personagem (animação placeholder)
- Personagem controlável (andar, correr, pular, câmera)
- Save do checkpoint e recarga após morte
- Mapa `L01_Zombies` em greybox: direção, obstáculos, transição, trecho a pé, arena, local de resgate

## M2 Vertical slice Fase 1

**Aceite**
- Percurso completo jogável do início à conclusão
- 3 tipos de inimigo (corpo a corpo, arqueiro, atirador) com estados e aggro por distância
- Horda final via diretor de ondas
- Resgate: abrir cela + animação de abraço (placeholder aceitável)
- Save/load de progresso; tela de conclusão
- HUD funcional (vida, carro, munição, objetivo, minimapa)

## M3 Sistemas e arte

**Aceite**
- 2 personagens originais com 2 skins cada, aprovados por humano
- SUV original, pistola alienígena original, inimigos finais
- UI final, fonte, áudio e animações integradas
- Manifesto com todos os assets `approved` e licenças auditadas

## M4 Fases 2 e 3

**Aceite**
- Novos mapas criados só com Data Assets e conteúdo, **sem refatoração estrutural**
- Mesmos sistemas do M2 reutilizados; regressão da Fase 1 verde

## M5 Otimização e release

**Aceite**
- Build standalone Win64 Shipping
- QA manual completo (20 passos) nas 3 fases
- Regressões resolvidas; licenças aprovadas; créditos gerados
- Orçamento de performance (A-023) medido e atingido ou desvio aprovado

# Catálogo de agentes

Gerado por `python tools/pipeline/gen_catalog.py`. Não edite à mão.

| Agente | Ferramentas | Escopo |
|---|---|---|
| `animation-specialist` | Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch | Use para animações, retargeting (IK Retargeter), Blend Spaces, Animation Montages, root motion e transições (sair do carro, abraço, hit reactions). |
| `art-director` | Read, Glob, Grep, Write, Edit, WebSearch, WebFetch | Use para Art Bible, briefs de assets, prompts de conceito, paletas e revisão de consistência visual. Não aprova arte final sozinho. |
| `asset-license-auditor` | Read, Glob, Grep, Write, Edit, Bash, WebFetch, WebSearch | Use antes de integrar qualquer conteúdo de terceiros (modelos, texturas, animações, áudio, fontes, plugins, pesos de IA) e antes de releases, para verificar procedênci... |
| `blender-specialist` | Read, Glob, Grep, Write, Edit, Bash | Use para modelagem, retopologia, UVs, materiais, rigs e exportação no Blender via scripts do repositório. Delegue quando houver um .blend a criar/alterar ou um export. |
| `cinematics-director` | Read, Glob, Grep, Write, Edit, Bash | Use para câmeras de gameplay e interação, ângulos, troca de câmera, cutscenes no Sequencer e a abertura do jogo (start, nave, queda). Define planos e valida o enquadra... |
| `enemy-ai-engineer` | Read, Glob, Grep, Write, Edit, Bash | Use para IA de inimigos (StateTree), percepção e aggro por distância, ataques corpo a corpo/arco/pistola, mira com antecipação, orçamento de agentes e diretor de hordas. |
| `gameplay-engineer` | Read, Glob, Grep, Write, Edit, Bash | Use para personagem a pé, câmera, combate, armas, saúde, interações, possession carro/personagem, checkpoints, save e fluxo de fase. |
| `level-designer` | Read, Glob, Grep, Write, Edit, Bash | Use para projetar espaços jogáveis: interiores entráveis, fluxo e ritmo de zonas, objetivos por zona, posicionamento de interações e recompensas. Projeta; a construção... |
| `performance-engineer` | Read, Glob, Grep, Write, Edit, Bash | Use para benchmarks, profiling (stat, Insights), budgets de frame/memória, LOD, culling, streaming e avaliação A/B de Nanite/Lumen/World Partition. |
| `qa-engineer` | Read, Glob, Grep, Write, Edit, Bash | Use para criar testes (pytest, Automation Tests), executar regressão, preencher checklists e produzir relatórios de bugs. Nunca aprova testes que não executou. |
| `sound-designer` | Read, Glob, Grep, Write, Edit, Bash, WebFetch | Use para música, ambiente sonoro, efeitos, mixagem e música adaptativa por zona. Opera a produção musical opcional com ACE-Step. Feedback de HUD e menus continua com o... |
| `studio-producer` | Read, Glob, Grep, Write, Edit, TodoWrite | Use como coordenador de tarefas multidisciplinares: quebra o pedido em entregas, atribui agentes e donos de arquivo, controla dependências e integra os retornos. Não i... |
| `technical-architect` | Read, Glob, Grep, Write, Edit, Bash | Use para decisões de arquitetura, contratos entre módulos C++, ADRs, revisão de interfaces e dependências. Delegue antes de criar um sistema novo ou mudar fronteiras e... |
| `technical-artist` | Read, Glob, Grep, Write, Edit, Bash | Use para materiais, iluminação, shaders, exposição, brilho exagerado, materiais sem textura e ponte entre arte e motor (Blender para Unreal). Audita e corrige, não cri... |
| `ui-audio-engineer` | Read, Glob, Grep, Write, Edit, Bash | Use para HUD (vida, carro, munição, objetivo, minimapa), menus, String Tables pt-BR, áudio de feedback, Sound Classes e integração de VFX (Niagara). |
| `vehicle-engineer` | Read, Glob, Grep, Write, Edit, Bash | Use para física do SUV (Chaos Vehicles), tuning de suspensão/torque/direção, dano por zonas, pneu furado, motor danificado e testes de direção. |
| `world-builder` | Read, Glob, Grep, Write, Edit, Bash | Use para terreno (Landscape), greybox de fases, obstáculos, streaming, checkpoints posicionados, iluminação e preenchimento de cenário. |

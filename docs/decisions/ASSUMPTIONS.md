# Suposições provisórias

> **Nenhum item desta tabela foi aprovado pelo usuário.** São padrões razoáveis para destravar o trabalho (prompt mestre, Etapa 19). Para aprovar ou mudar: edite `Status`, atualize o GDD (seção 15) e feche o item correspondente em `OPEN_DECISIONS.md`.

Legenda: **Rev.** = reversível (Alta: troca barata; Média: exige retrabalho localizado; Baixa: afeta arquitetura ou muita arte).

| ID | Tema | Valor sugerido | Por quê | Rev. | Consequências | Status | GDD |
|---|---|---|---|---|---|---|---|
| A-001 | Plataforma | Windows 64 bits | Máquina do dev é Windows; Unreal mais madura nele | Alta | Linux/Mac ficam para depois; nada específico de Windows no gameplay | pendente | 3, Q2 |
| A-002 | Engine | Unreal Engine 5.8.4 | Última hotfix da 5.8 na criação do repo | Média | Upgrade de minor exige teste de regressão completo | pendente | 3, Q1 |
| A-003 | Linguagens | C++ (sistemas) + Blueprint (composição) + Python (pipeline) | Performance e testabilidade em C++, iteração rápida em BP | Baixa | Exige Visual Studio; build mais lento que só BP | pendente | Q1 |
| A-004 | Estilo visual | Semi-realista estilizado | Coerente com física crível, mas viável para equipe pequena | Baixa | Define Art Bible, texel density e orçamento de polígonos | pendente | Q4 |
| A-005 | Personagens | Mesmos atributos iniciais | Evita balanceamento duplo no MVP | Alta | Diferença é visual/narrativa até decisão | pendente | 5, Q7 |
| A-006 | Skins | Apenas cosméticas, todas liberadas | Simples, sem economia | Alta | Desbloqueio por progressão pode ser adicionado via Data Asset | pendente | 5 |
| A-007 | Dificuldade | Um nível: Normal | Escopo | Alta | Parâmetros de dificuldade já ficam em Data Assets | pendente | Q12 |
| A-008 | Veículo | SUV 4x4 original (provisório) | Terreno acidentado pede tração 4x4 e suspensão longa | Média | Afeta física, rig de rodas e animação de saída | pendente | 6, Q13 |
| A-009 | Tiro dentro do carro | Não no MVP | Reduz escopo de câmera/animação | Média | Inimigos são evitados ou atropelados no trecho de carro | pendente | 6.3, Q14 |
| A-010 | Atropelamento | Permitido, causa dano ao carro proporcional ao impacto | Física plausível e risco/recompensa | Alta | Precisa de dano por zona frontal | pendente | 6.3 |
| A-011 | Armas | Apenas pistola alienígena original; munição limitada com recarga | Escopo | Alta | Sistema de armas é extensível via `UJRWeaponDefinition` | pendente | 7, Q16 |
| A-012 | Progressão | Linear, sem loot/moeda | Escopo | Alta | Sem economia para balancear | pendente | Q17 |
| A-013 | Checkpoint | Principal na transição carro/pé + início da fase; morte volta ao último | GDD já prevê o principal | Alta | Pode ganhar checkpoints extras por Data Asset | pendente | 4, Q18 |
| A-014 | Destruição do carro | Reinicia no último checkpoint | Simples e justo | Alta | | pendente | 6.2 |
| A-015 | Carro após checkpoint | Fica estacionado e inativo (sem física simulada) | Evita custo e bugs | Alta | | pendente | 6.4 |
| A-016 | SaveGame | `USaveGame` versionado (campo `SaveVersion` + migração) | Nativo, sem dependências | Média | | pendente | 3.1 |
| A-017 | Idioma | pt-BR, textos via String Tables para futura localização | Público inicial | Alta | | pendente | 10 |
| A-018 | Duração | 15 a 20 min por fase | Sugestão do próprio GDD | Alta | Guia o tamanho do greybox | pendente | Q11 |
| A-019 | Gore | Moderado (sangue escuro, sem desmembramento) | Classificação mais ampla, menos arte | Média | | pendente | 11, Q5 |
| A-020 | Dublagem | Sem falas obrigatórias no MVP | Escopo e custo | Alta | | pendente | Q9 |
| A-021 | Combustível/economia | Não no MVP | Escopo | Alta | | pendente | 6, Q15 |
| A-022 | Comercialização | Tratada como possível (auditoria de licença comercial) | Evita retrabalho de licenças depois | Alta | Bloqueia assets NC | pendente | Q20 |
| A-023 | Performance | 60 FPS a 1080p em GPU de classe RTX 3060 / RX 6600 | Meta provisória comum para PC | Média | Guia budgets de LOD, IA e luz | pendente | 3 |
| A-024 | Fases 2 e 3 | Temas temporários `L02_Future` e `L03_Future`, sem canonizar | Não inventar escopo | Alta | | pendente | 4.2, Q10 |
| A-025 | Input | Teclado/mouse e controle (Enhanced Input) | Custo baixo com Enhanced Input | Alta | | pendente | Q3 |
| A-026 | Vida do personagem | Sem regeneração; itens de cura simples no trecho a pé | Tensão de sobrevivência | Alta | | pendente | 7 |
| A-027 | Raiz do repositório | Conteúdo do "jogo-resgate/" do prompt fica na raiz de `utrazin-game` | Repositório já existe com esse nome | Alta | Caminhos dos docs são relativos à raiz | pendente | n/a |
| A-028 | Nome do projeto Unreal | `JogoResgate`, prefixo C++ `JR` | Título provisório | Média | Renomear módulo depois exige redirects | pendente | Q21 |
| A-029 | Orçamento de IA | 12 agentes completos, até 30 visíveis na horda | Valor do prompt mestre, sujeito a profiling | Alta | | pendente | 8.2 |
| A-030 | IA | StateTree (ver ADR-002) | Nativa e madura na 5.8 | Média | | pendente | 8.2 |
| A-031 | GAS | Não usar no MVP (ver ADR-001) | Componentes simples bastam | Média | Interfaces preservam migração | pendente | 7 |

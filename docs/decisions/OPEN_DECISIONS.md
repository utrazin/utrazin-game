# Decisões em aberto

Itens que **dependem do usuário**. A coluna "Proposta" aponta para a suposição usada enquanto não houver resposta. "Bloqueia" indica o marco que fica impedido sem a decisão.

| ID | Pergunta (GDD seção 14) | Proposta | Impacto | Bloqueia |
|---|---|---|---|---|
| OD-001 | Versão da Unreal e C++/Blueprint | A-002, A-003 | Toda a base de código | M1 |
| OD-002 | Plataforma e hardware mínimo | A-001, A-023 | Budgets de performance | M5 |
| ~~OD-003~~ | Teclado/mouse, controle ou ambos | **Resolvido: ambos** (A-025) | Input e UI | - |
| ~~OD-004~~ | Estilo visual | **Resolvido: cartunesco** (A-004) | Toda a arte | - |
| OD-005 | Tom e classificação (gore) | A-019 | VFX, inimigos | M3 |
| OD-006 | Referências de jogo (visual/jogabilidade) | nenhuma | Art Bible | M3 |
| OD-007 | Quem são os 2 personagens; diferenças de jogabilidade | A-005 | Concepts, rigs, balanceamento | M3 |
| OD-008 | Quem é a pessoa resgatada em cada fase; narrativa e cinemáticas | nenhuma | Fluxo de fase, cena de abraço | M2 |
| OD-009 | Dublagem e diálogos | A-020 | Áudio, legendas | M3 |
| OD-010 | Tema/objetivo das fases 2 e 3 | A-024 | Mapas futuros | M4 |
| ~~OD-011~~ | Duração da fase | **Resolvido: Fase 1 até 10 min** (A-018); fases 2 e 3 em aberto | Tamanho do mapa | - |
| OD-012 | Níveis de dificuldade | A-007 | Balanceamento | M5 |
| OD-013 | Modelo do carro; um ou vários | A-008 | Física e arte | M3 |
| OD-014 | Tiro de dentro do carro; armas no carro; atropelar | A-009, A-010 | Câmera, animação, dano | M2 |
| OD-015 | Dano por zonas, reparo, combustível | A-021 + zonas propostas em docs/gameplay/VEHICLE.md | Física e HUD | M1 |
| OD-016 | Mais armas no MVP; munição limitada | A-011 | Combate, UI | M2 |
| OD-017 | Itens, upgrades, loot, moeda | A-012 | Economia | M2 |
| ~~OD-018~~ | Morte e quantidade de checkpoints | **Resolvido: volta ao último checkpoint** (A-013, A-014) | Save, level design | - |
| OD-019 | Equipe (só você ou mais pessoas) | só o usuário | Locks LFS, processo de revisão | M0 |
| OD-020 | Prazo e distribuição/venda | A-022 | Licenças | M5 |
| OD-021 | Nome do jogo e licença do repositório | A-028; LICENSE "todos os direitos reservados" | Branding, módulo C++ | M5 |
| OD-022 | Fonte própria: uma para o jogo ou uma por fase | uma para o jogo (OFL) | UI | M3 |
| OD-023 | Fontes de áudio (livre, licenciado, criado) | bibliotecas CC0 + gravação própria | Áudio | M3 |
| OD-024 | Ferramentas de textura (Blender, GIMP, Krita) | Krita + GIMP + Blender | Pipeline | M3 |
| OD-025 | Uso de IA gerativa para conceitos (qual ferramenta, licença dos pesos) | nenhuma escolhida | Concepts | M3 |
| OD-026 | Recordes/estatísticas no save | não no MVP | Save | M2 |

## Impedimentos técnicos atuais

| ID | Impedimento | Efeito | Como resolver |
|---|---|---|---|
| IMP-001 | ~~Unreal Engine, Visual Studio e Blender não instalados~~ resolvido em 2026-11-11 (falta só Blender no PATH) | Código C++ e `.uproject` nunca compilados/abertos; sem `.uasset`/`.umap` | Seguir `docs/setup/INSTALL_UNREAL.md` e `INSTALL_BLENDER.md` |
| IMP-002 | Repositório criado em ambiente remoto (sem acesso ao shell do PC) | Inspeção do ambiente local não executada; Git LFS não verificado | Rodar `python tools/setup/check_environment.py` no PC |

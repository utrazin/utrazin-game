# Audio Bible (v0.1 provisória)

## Estética

- **Trecho de carro**: motor e terreno dominam; música rítmica de baixa frequência, crescendo com velocidade e perigo.
- **Trecho a pé**: ambiente denso (vento, insetos, estruturas rangendo), música esparsa, ataques sonoros quando inimigos entram em aggro.
- **Horda final**: camada percussiva intensa que sobe por onda.
- **Resgate**: corte da tensão, tema emocional curto e melódico.

## Categorias (Sound Classes / Submixes)

| Classe | Exemplos | Prioridade |
|---|---|---|
| `SC_Music` | trilha por fase, stingers | média |
| `SC_SFX_Player` | tiros, recarga, passos, dano | alta |
| `SC_SFX_Vehicle` | motor (loop por RPM), pneus, impactos, pneu estourando, motor danificado | alta |
| `SC_SFX_Enemy` | vocalizações zumbi, flechas, tiros inimigos | média |
| `SC_Ambience` | camadas ambiente por zona | baixa |
| `SC_UI` | navegação, confirmação, alertas de HUD | alta |
| `SC_Voice` | (sem dublagem no MVP, A-020) | n/a |

## Especificações técnicas

- Formato fonte: WAV 48 kHz, 24 bits; export final: WAV 48 kHz 16 bits (Unreal comprime).
- SFX mono, exceto ambiente e música (estéreo).
- Loudness alvo: música -16 LUFS integrado; SFX normalizados para pico -1 dBTP.
- Loops sem clique (verificar zero-crossing).
- Nome: `SFX_<Categoria>_<Descricao>_<Var>` (ex.: `SFX_Vehicle_TireBurst_01`), `MUS_<Fase>_<Estado>`, `AMB_<Zona>_<Var>`.
- Atenuação: perfis compartilhados em `Content/Audio/Attenuation/`.
- Concorrência: limite de vozes por inimigo (máx. 6 vocalizações simultâneas).

## Fontes permitidas

CC0 (preferido), CC BY 4.0 com atribuição, gravações próprias. Ver [`ASSET_LICENSES.md`](../../ASSET_LICENSES.md). Ferramenta de edição sugerida: Audacity (GPL, gratuita).

## Feedback obrigatório (legibilidade)

| Evento | Som | Também visual |
|---|---|---|
| Pneu furado | estouro + chiado contínuo | ícone no HUD |
| Motor danificado | tosse do motor, perda de RPM | fumaça |
| Inimigo entra em aggro | grito curto direcional | indicador |
| Munição baixa | clique de aviso | núcleo da pistola pisca |
| Checkpoint | stinger curto | toast no HUD |

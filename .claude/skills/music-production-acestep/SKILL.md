---
name: music-production-acestep
description: OPCIONAL. Use para gerar, avaliar, selecionar e organizar música do jogo (menu, exploração, combate, ambiente por zona) com o ACE-Step 1.5 local via API REST. A pipeline funciona sem ele.
---

# /music-production-acestep

Fluxo de produção musical assistida. Ferramenta externa e opcional: se não estiver instalada, use bibliotecas CC0 conforme `design/audio-bible/AUDIO_BIBLE.md`.

## Pré-requisitos
- ACE-Step instalado à parte (`docs/pipeline/EXTERNAL_TOOLS.md`), servidor em `http://localhost:8001` (`uv run acestep-api`)
- GPU/VRAM conforme a faixa de hardware documentada; `python tools/setup/check_optional_ai_tools.py` informa o que há
- Registro de licença da saída antes de usar no jogo (`/audit-licenses`)

## Passos
1. **Brief por cue** (`audio/music/briefs/<id>.md`): uso (menu, zona, combate, calmaria), emoção, tempo (BPM), tom, instrumentos, duração, se precisa fazer loop, se tem voz. Mantenha o mesmo BPM e tom nos cues que serão misturados.
2. **Gerar** com `python tools/audio/acestep_client.py generate --prompt "..." --duration 90 --bpm 100 --batch 4 --out audio/music/candidates/<id>`. A API devolve áudio por tarefa; guarde prompt, seed, modelo e versão no `.json` ao lado.
3. **Música sem voz**: a API documentada não traz campo `instrumental`; use o prompt ("instrumental, no vocals") e confirme a convenção de letra na documentação do repositório do ACE-Step antes de depender dela.
4. **Avaliar** (ouvir e anotar em `audio/music/review/<id>.md`): encaixe com a cena, ausência de vozes ou artefatos, final limpo, repetição enjoativa, mix (não esmagar efeitos). Reprove sem dó.
5. **Loop**: ajuste os pontos de loop e faça crossfade de 1 a 2 s; confirme emenda inaudível. Música adaptativa: gere versões Calma, Tensão e Combate no mesmo BPM e tom e misture por camadas na engine.
6. **Normalizar** para -16 a -18 LUFS de música (efeitos mais altos); formato `wav` 48 kHz para a fonte, importado como `SFX_/MUS_` conforme `.claude/rules/unreal-content.md`.
7. **Organizar**: `audio/music/final/MUS_<Fase>_<Zona>_<Uso>_v01.wav`; registre no manifesto com `creation_method: ai_generated`, modelo, versão, seed, prompt e licença (pesos MIT conforme o model card; confirme a versão baixada).
8. **Integrar** com `ui-audio-engineer` e `sound-designer` (MetaSounds, Sound Classes, ducking). Aprovação humana final por escuta.

## Ferramentas necessárias
- ACE-Step (opcional), `tools/audio/acestep_client.py`, ffmpeg ou Audacity para loop e normalização

## Diretórios afetados
- `audio/music/`, `assets/manifest/assets.json`, `design/audio-bible/`

## Verificações
- Cada arquivo final tem seed, prompt, modelo e licença registrados
- Loop sem estalo; loudness dentro da faixa
- O jogo roda com a pasta de música vazia (ferramenta opcional)

## Erros comuns
- Baixar todos os modelos sem checar VRAM e disco
- Misturar cues de BPM e tom diferentes
- Usar a saída sem registrar origem e licença

## Critério de sucesso
Cada cue necessário tem uma faixa aprovada por escuta, em loop limpo, registrada no manifesto, ou o cue usa o plano alternativo CC0.

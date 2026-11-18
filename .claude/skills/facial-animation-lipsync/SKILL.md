---
name: facial-animation-lipsync
description: OPCIONAL. Use para animação facial e lip sync de personagens falantes (NPCs, cutscenes): requisitos de rig com blend shapes, fluxo áudio para curvas faciais com Audio2Face-3D ou alternativa, importação na Unreal e validação.
---

# /facial-animation-lipsync

Fluxo de áudio até boca, olhos e sobrancelhas. Opcional: sem ele o diálogo roda com legendas e animação de fala simples.

## Pré-requisitos
- Diálogo em WAV mono (confirme taxa e formato aceitos pela ferramenta usada)
- Rosto do personagem com blend shapes (ver passo 1); os heróis atuais vêm de modelos do Tripo e podem não ter
- Compatibilidade verificada: o plugin Audio2Face-3D para Unreal documenta suporte até UE 5.6; **não instale na 5.8.4 sem teste real**, e nunca rebaixe a engine

## Passos
1. **Rig facial mínimo**: shape keys com nomes ARKit. Conjunto completo de 52 ou o mínimo para fala: `jawOpen`, `mouthClose`, `mouthFunnel`, `mouthPucker`, `mouthSmileLeft/Right`, `mouthStretchLeft/Right`, `mouthLowerDownLeft/Right`, `mouthUpperUpLeft/Right`, `eyeBlinkLeft/Right`, `browInnerUp`. Valide com `python tools/blender/validate_face_blendshapes.py` (no Blender) ou `--names arquivo.txt`.
2. **Escolha o caminho** (registre a decisão em `docs/decisions/`):
   - A) Audio2Face-3D fora da engine (SDK, MACE ou NIM), exportando curvas por quadro (JSON, CSV ou FBX) e importando na Unreal como curvas/Animation Sequence. Licenças: código MIT, mas modelos sob "NVIDIA Open Model" e Audio2Emotion sob licença própria; confirme uso comercial antes de entregar.
   - B) Plugin Audio2Face-3D da NVIDIA dentro da Unreal: só se a documentação passar a listar a versão da engine do projeto e um teste real passar. Hoje: INVESTIGAR.
   - C) Alternativa livre de visemas a partir do áudio (por exemplo Rhubarb Lip Sync, confirmar licença) mapeada para os shape keys: menor qualidade, sem dependência de GPU NVIDIA.
3. **Gerar** as curvas por fala; nomeie `ANM_Face_<Personagem>_<Linha>`; guarde a origem (ferramenta, versão, modelo) no manifesto.
4. **Importar** na Unreal: curvas aplicadas por `Modify Curve` no ABP do rosto (ou morph targets na Animation Sequence); camada de rosto separada do corpo.
5. **Validar sincronia**: amostre a boca contra a fala (abertura de mandíbula acompanha a energia do áudio, fechamentos em consoantes labiais M/B/P). Desvio de tempo <= 2 quadros a 30 fps; sem tremedeira; olhos piscam. Grave um clipe de 10 s por personagem.
6. **Integrar** ao diálogo (`dialogue-systems`, `intro-sequence`, `camera-shots-and-cutscenes`): close só quando o rosto passou na validação.

## Ferramentas necessárias
- Blender; Audio2Face-3D (opcional) ou alternativa de visemas

## Diretórios afetados
- `assets/work/characters/`, `unreal/JogoResgate/Content/Characters/`, `docs/decisions/`, `tools/blender/`

## Verificações
- Validador de blend shapes sem faltas críticas
- Clipe de teste com sincronia aprovada por vista
- Nenhum plugin instalado em versão de engine sem suporte comprovado

## Erros comuns
- Presumir compatibilidade de plugin com outra versão da engine
- Esquecer que os modelos têm licença própria
- Animar o rosto sem shape keys

## Critério de sucesso
Cada personagem falante tem rosto validado e pelo menos uma fala com lip sync aprovada, ou o fluxo está documentado e marcado como pendente.

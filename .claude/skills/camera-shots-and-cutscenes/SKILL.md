---
name: camera-shots-and-cutscenes
description: Use para definir ângulos de câmera, câmera de interação (pegar item, abrir baú, curar), câmera em espaço fechado, trocas de câmera com animação e cutscenes no Sequencer. Evita cortes sem motivo e ângulos ruins.
---

# /camera-shots-and-cutscenes

Toda troca de câmera tem motivo, animação e ângulo definidos antes de ser implementada.

## Pré-requisitos
- Lista de interações e eventos do roteiro
- `camera-systems` (disciplina) e a classe de câmera atual do `JRCharacter`

## Passos
1. **Catálogo de planos** (em `docs/gameplay/CAMERA_SHOTS.md`): para cada evento (pegar item, abrir baú, curar, entrar no carro, entrar em prédio, ver a nave) escreva: plano (aberto, médio, close), altura, distância, lado, FOV, duração, animação sincronizada, retorno.
2. **Regra de ouro**: só troque de câmera se agrega informação. Pegar um graveto: manter a câmera do jogador, com leve aproximação (0,3 a 0,5 s) e animação de abaixar e pegar. Sem animação pronta, não corta a câmera.
3. **Ângulo**: altura entre o peito e o olho; 3/4 frontal ou de ombro; nunca abaixo do joelho nem atrás de objetos. Evite mostrar a nuca em close.
4. **Colisão**: probe da câmera bloqueada por terreno e malhas (canal Camera), tamanho de sonda >= 12 cm; checar por baixo do terreno em encostas.
5. **Espaços fechados**: volume de câmera encurta o braço e limita inclinação (ver `/enterable-interior`); blend de entrada e saída de 0,4 a 0,8 s.
6. **Transições**: `SetViewTargetWithBlend`, curva EaseInOut; devolve o controle sem salto; input bloqueado só durante a ação.
7. **Cutscenes**: Level Sequence com Camera Cuts; sempre pulável (segurar tecla), estado salvo para pular; duração <= 60 s por cena; áudio por trilha.
8. **Validação**: grave 5 s de cada plano, confira o enquadramento do personagem e a ausência de clipping. Anexe ao relatório.
9. Rode `/visual-qa-gate`.

## Ferramentas necessárias
- Unreal (Sequencer, Camera Actors), `blender-camera-cinematography` para pré-visualização

## Diretórios afetados
- `unreal/JogoResgate/Content/Cinematics/`, `Source/JogoResgate/Characters/`, `docs/gameplay/CAMERA_SHOTS.md`

## Verificações
- Nenhum evento muda de câmera sem animação correspondente
- Câmera nunca fica abaixo do terreno em teste de 360 graus em encosta
- Cutscene pulável sem quebrar estado

## Erros comuns
- Trocar câmera "só porque sim"
- Ângulo escolhido sem olhar o resultado
- Esquecer de devolver a câmera ao jogador

## Critério de sucesso
Cada interação do roteiro tem plano documentado, implementado e gravado, aprovado pelo usuário.

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * [A-073] Opções de sensação de jogo (acessibilidade), lidas por quem dispara tremor, congelada e clarão.
 * Variáveis de console (salvas pelo jogador no futuro via menu; hoje: console ou DefaultEngine.ini [ConsoleVariables]):
 *   jr.Feel.ShakeScale   0..1  intensidade do tremor de câmera (0 = sem tremor). Padrão 1.
 *   jr.Feel.MotionScale  0..1  movimentos extras da câmera: FOV de velocidade, "afundada" ao aterrissar, pulso. Padrão 1.
 *   jr.Feel.ReduceFlash  0/1   1 = clarões do corpo atingido mais fracos e curtos. Padrão 0.
 *   jr.Feel.HitStop      0/1   0 = desliga a "congelada" dos golpes. Padrão 1.
 * Tiers (skill game-feel): pequeno = trauma 0,10-0,20 sem congelar; médio = 0,30-0,50 e 0,04-0,06 s;
 * grande = 0,70-1,00 e 0,10-0,15 s (usado com moderação: em terceira pessoa o grande fica em 0,45-0,6).
 */
namespace JRFeel
{
	JOGORESGATE_API float ShakeScale();
	JOGORESGATE_API float MotionScale();
	JOGORESGATE_API bool ReduceFlash();
	JOGORESGATE_API bool HitStopEnabled();
}

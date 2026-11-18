// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "JRZombieCarTypes.generated.h"

/** Eventos zumbi x carro (ganchos para som/VFX da Etapa 10). Value: ver cada item. */
UENUM(BlueprintType)
enum class EJRZombieCarEvent : uint8
{
	/** Soco na lataria. Value = dano aplicado. */
	ZombieHitCar,
	/** Zumbi agarrou no capô/lateral. Value = número do ponto (0 capô, 1 esquerda, 2 direita). */
	ZombieGrabbed,
	/** Zumbi agarrado foi sacudido/arremessado. Value = velocidade do carro (km/h). */
	ZombieThrownOff,
	/** Atropelamento com arremesso. Value = velocidade do impacto (km/h). */
	RunOver,
	/** Atropelamento devagar: empurrou e cambaleou. Value = velocidade do carro (km/h). */
	ZombiePushed,
	/** Furou uma barricada. Value = velocidade do carro (km/h). */
	BarricadeBroken,
	/** O carro explodiu. Value = raio da explosão (cm). */
	Explosion
};

/** Estado visual de dano do carro (fumaça, fogo, destruído). */
UENUM(BlueprintType)
enum class EJRVehicleDamageFXState : uint8
{
	Intact,
	Smoking,
	Burning,
	Wrecked
};

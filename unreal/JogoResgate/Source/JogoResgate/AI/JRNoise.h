// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Subsystems/WorldSubsystem.h"
#include "JRNoise.generated.h"

class UJRWeaponComponent;

/**
 * Audição dos zumbis (A-048). Qualquer sistema chama:
 *   UJRNoise::ReportNoise(this, Local, RaioEmCm);
 * Zumbis calmos dentro do raio (x HearingScale do arquétipo) vão ver o que foi (Investigate)
 * e só atacam se enxergarem o jogador. Barato: só percorre os zumbis quando há barulho.
 * Referência de raio: tiro 3000, impacto de bala 700, buzina 4000, explosão 6000, motor 2500 a 7000.
 */
UCLASS()
class JOGORESGATE_API UJRNoise : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Loudness = raio em cm em que os zumbis ouvem. */
	UFUNCTION(BlueprintCallable, Category = "JR|Noise", meta = (WorldContext = "WorldContext"))
	static void ReportNoise(UObject* WorldContext, FVector Location, float Loudness);
};

/**
 * Barulhos automáticos do jogador sem mexer em outros arquivos: tiros da arma do herói
 * (OnWeaponFired) e o motor do carro andando (a cada EngineNoiseInterval).
 */
UCLASS()
class JOGORESGATE_API UJRNoiseSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;

	/** Raio do barulho de um tiro do jogador (cm). */
	UPROPERTY(EditAnywhere, Category = "JR|Noise")
	float GunshotLoudness = 3000.f;

	/** Raio do barulho onde a bala bate (distrai zumbis perto do impacto). */
	UPROPERTY(EditAnywhere, Category = "JR|Noise")
	float BulletImpactLoudness = 700.f;

	/** Motor: raio base + raio por cm/s de velocidade, com teto. */
	UPROPERTY(EditAnywhere, Category = "JR|Noise")
	float EngineBaseLoudness = 2500.f;

	UPROPERTY(EditAnywhere, Category = "JR|Noise")
	float EngineLoudnessPerSpeed = 2.f;

	UPROPERTY(EditAnywhere, Category = "JR|Noise")
	float EngineMaxLoudness = 7000.f;

	/** Abaixo desta velocidade (cm/s) o motor parado não chama ninguém. */
	UPROPERTY(EditAnywhere, Category = "JR|Noise")
	float EngineMinSpeed = 150.f;

	/** false se a arma já chamar UJRNoise::ReportNoise por conta própria (evita barulho em dobro). */
	UPROPERTY(EditAnywhere, Category = "JR|Noise")
	bool bAutoBindPlayerWeapon = true;

private:
	void TickNoise();

	UFUNCTION()
	void HandlePlayerWeaponFired(const FVector& Start, const FVector& End);

	FTimerHandle NoiseTimer;
	TWeakObjectPtr<UJRWeaponComponent> BoundWeapon;
	float EngineNoiseInterval = 1.f;
};

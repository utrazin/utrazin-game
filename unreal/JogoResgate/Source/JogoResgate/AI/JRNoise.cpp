// Copyright utrazin. All Rights Reserved.

#include "AI/JRNoise.h"
#include "AI/JREnemyCharacter.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRWeaponComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "JogoResgate.h"
#include "TimerManager.h"
#include "Vehicles/JRVehiclePawn.h"

void UJRNoise::ReportNoise(UObject* WorldContext, FVector Location, float Loudness)
{
	if (!WorldContext || Loudness <= 0.f || !GEngine)
	{
		return;
	}
	UWorld* GameWorld = GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull);
	if (!GameWorld)
	{
		return;
	}
	int32 Listeners = 0;
	for (TActorIterator<AJREnemyCharacter> It(GameWorld); It; ++It)
	{
		AJREnemyCharacter* Enemy = *It;
		if (Enemy && !Enemy->IsDead())
		{
			// O próprio zumbi filtra pela distância (x HearingScale) e pelo estado.
			Listeners += Enemy->HearNoise(Location, Loudness) ? 1 : 0;
		}
	}
	UE_LOG(LogJR, Verbose, TEXT("Barulho em %s (raio %.0f): %d zumbi(s) foram ver"), *Location.ToCompactString(), Loudness, Listeners);
}

bool UJRNoiseSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UJRNoiseSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	InWorld.GetTimerManager().SetTimer(NoiseTimer, this, &UJRNoiseSubsystem::TickNoise, EngineNoiseInterval, true, 0.5f);
}

void UJRNoiseSubsystem::Deinitialize()
{
	if (UWorld* GameWorld = GetWorld())
	{
		GameWorld->GetTimerManager().ClearTimer(NoiseTimer);
	}
	if (UJRWeaponComponent* Weapon = BoundWeapon.Get())
	{
		Weapon->OnWeaponFired.RemoveDynamic(this, &UJRNoiseSubsystem::HandlePlayerWeaponFired);
	}
	BoundWeapon.Reset();
	Super::Deinitialize();
}

void UJRNoiseSubsystem::TickNoise()
{
	APawn* PlayerPawn = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!PlayerPawn)
	{
		return;
	}
	// Tiros: liga na arma do herói atual (troca de herói, respawn e sair do carro criam outra).
	if (bAutoBindPlayerWeapon)
	{
		if (const AJRCharacter* Hero = Cast<AJRCharacter>(PlayerPawn))
		{
			UJRWeaponComponent* Weapon = Hero->GetWeaponComponent();
			if (Weapon && Weapon != BoundWeapon.Get())
			{
				if (UJRWeaponComponent* Old = BoundWeapon.Get())
				{
					Old->OnWeaponFired.RemoveDynamic(this, &UJRNoiseSubsystem::HandlePlayerWeaponFired);
				}
				Weapon->OnWeaponFired.AddUniqueDynamic(this, &UJRNoiseSubsystem::HandlePlayerWeaponFired);
				BoundWeapon = Weapon;
			}
		}
	}
	// Motor: carro do jogador andando chama zumbis de longe (perto, a perseguição do carro já cuida).
	if (const AJRVehiclePawn* Car = Cast<AJRVehiclePawn>(PlayerPawn))
	{
		const float CarSpeed = static_cast<float>(Car->GetVelocity().Size());
		if (!Car->IsWrecked() && CarSpeed >= EngineMinSpeed)
		{
			const float Radius = FMath::Min(EngineBaseLoudness + CarSpeed * EngineLoudnessPerSpeed, EngineMaxLoudness);
			UJRNoise::ReportNoise(this, Car->GetActorLocation(), Radius);
		}
	}
}

void UJRNoiseSubsystem::HandlePlayerWeaponFired(const FVector& Start, const FVector& End)
{
	UJRNoise::ReportNoise(this, Start, GunshotLoudness);
	if (BulletImpactLoudness > 0.f)
	{
		UJRNoise::ReportNoise(this, End, BulletImpactLoudness);
	}
}

// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRBlockingGate.h"
#include "AI/JRAIDirector.h"
#include "Characters/JRCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/JRPlayerController.h"
#include "FX/JRInteractionCameraComponent.h"
#include "Engine/World.h"
#include "GameFramework/DamageType.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"

AJRBlockingGate::AJRBlockingGate()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	BlockerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BlockerMesh"));
	BlockerMesh->SetupAttachment(Root);
	BlockerMesh->SetCollisionProfileName(TEXT("BlockAll"));
	BlockVolume = CreateDefaultSubobject<UBoxComponent>(TEXT("BlockVolume"));
	BlockVolume->SetupAttachment(Root);
	BlockVolume->SetBoxExtent(FVector(180.f, 750.f, 350.f));
	BlockVolume->SetRelativeLocation(FVector(0.f, 0.f, 300.f));
	BlockVolume->SetCollisionProfileName(TEXT("BlockAll"));
	BlockVolume->SetHiddenInGame(true);
	FlashLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("FlashLight"));
	FlashLight->SetupAttachment(Root);
	FlashLight->SetRelativeLocation(FVector(0.f, 0.f, 300.f));
	FlashLight->SetIntensity(0.f);
	FlashLight->SetAttenuationRadius(3000.f);
	FlashLight->SetLightColor(FLinearColor(1.f, 0.55f, 0.2f));
	FlashLight->SetCastShadows(false);
}

bool AJRBlockingGate::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return !bOpen && !bArmed && Cast<AJRCharacter>(InstigatorActor) != nullptr;
}

FText AJRBlockingGate::GetInteractionText_Implementation() const
{
	return RequiredItem.IsNone() ? NSLOCTEXT("JogoResgate", "GateOpen", "Abrir passagem")
		: NSLOCTEXT("JogoResgate", "GateArm", "Armar explosivo");
}

void AJRBlockingGate::Interact_Implementation(AActor* InstigatorActor)
{
	if (!Execute_CanInteract(this, InstigatorActor))
	{
		return;
	}
	// [Animações/A-057] o herói anima a ação: aperta/abre (InteractAnim) ou ajoelha e arma (PlantAnim).
	AJRCharacter* ActingHero = Cast<AJRCharacter>(InstigatorActor);
	if (RequiredItem.IsNone())
	{
		if (ActingHero)
		{
			ActingHero->PlayFullBodyAction(ActingHero->GetInteractAnim(), 1.f, 2.f);
		}
		OpenGate();
		return;
	}
	const APawn* Hero = Cast<APawn>(InstigatorActor);
	AJRPlayerController* PC = Hero ? Cast<AJRPlayerController>(Hero->GetController()) : nullptr;
	if (!PC || !PC->HasKeyItem(RequiredItem))
	{
		AJRHUD::Toast(this, HintWithoutItem, FLinearColor(1.f, 0.6f, 0.2f));
		return;
	}
	PC->ConsumeKeyItem(RequiredItem);
	bArmed = true;
	if (ActingHero)
	{
		const FVector ToGate = (GetActorLocation() - ActingHero->GetActorLocation()).GetSafeNormal2D();
		if (!ToGate.IsNearlyZero())
		{
			ActingHero->SetActorRotation(ToGate.Rotation());
		}
		const float PlantTime = ActingHero->PlayFullBodyAction(ActingHero->GetPlantAnim(), 1.f, 3.f);
		// [A-058] por trás e de cima enquanto arma o explosivo.
		if (PlantTime > 0.f && ActingHero->GetInteractionCamera())
		{
			ActingHero->GetInteractionCamera()->PlayShot(EJRInteractionShot::GatePlant, this, PlantTime);
		}
	}
	AJRHUD::Toast(this, FString::Printf(TEXT("Explosivo armado! Afaste-se (%.0f s)."), FuseTime), FLinearColor(1.f, 0.35f, 0.1f));
	GetWorldTimerManager().SetTimer(FuseTimer, this, &AJRBlockingGate::Detonate, FMath::Max(FuseTime, 0.1f), false);
}

void AJRBlockingGate::Detonate()
{
	const FVector Origin = BlockVolume->GetComponentLocation();
	OpenGate(); // antes do dano: a caixa não pode "proteger" quem está do outro lado
	UGameplayStatics::ApplyRadialDamage(this, ExplosionDamage, Origin, ExplosionRadius, UDamageType::StaticClass(),
		TArray<AActor*>(), this, nullptr, true);
	if (ExplosionSystem)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ExplosionSystem, Origin);
	}
	if (ExplosionSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, ExplosionSound, Origin);
	}
	FlashLight->SetIntensity(200000.f);
	GetWorldTimerManager().SetTimer(FlashTimer, this, &AJRBlockingGate::EndFlash, 0.35f, false);
	if (bTriggerHorde)
	{
		if (AJRAIDirector* Director = AJRAIDirector::Find(this))
		{
			Director->TriggerHordeAt(TEXT("Portao"), Origin, HordeDuration, HordeSize);
		}
		AJRHUD::Toast(this, TEXT("BUM! Caminho livre... e a horda ouviu! Corra para o buggy!"), FLinearColor(1.f, 0.3f, 0.2f));
	}
}

void AJRBlockingGate::EndFlash()
{
	FlashLight->SetIntensity(0.f);
}

void AJRBlockingGate::OpenGate()
{
	if (bOpen)
	{
		return;
	}
	bOpen = true;
	bArmed = false;
	BlockerMesh->SetVisibility(false, true);
	BlockerMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	BlockVolume->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	UE_LOG(LogJR, Log, TEXT("%s aberto"), *GetName());
	OnGateOpened.Broadcast(this);
	BP_OnGateOpened();
}

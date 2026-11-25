// Copyright utrazin. All Rights Reserved.

#include "Interactions/JRInteriorPortal.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "JogoResgate.h"
#include "GameFramework/WorldSettings.h"
#include "TimerManager.h"

AJRInteriorPortal::AJRInteriorPortal()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetupAttachment(Root);
	Box->SetBoxExtent(FVector(70.f, 90.f, 110.f));
	Box->SetRelativeLocation(FVector(0.f, 0.f, 110.f));
	// Só consulta: a busca de interação por proximidade acha WorldDynamic; ninguém tropeça nela.
	Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Box->SetCollisionObjectType(ECC_WorldDynamic);
	Box->SetCollisionResponseToAllChannels(ECR_Overlap);
	Box->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	Box->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	Box->SetCanEverAffectNavigation(false);
}

AJRInteriorPortal* AJRInteriorPortal::FindTarget() const
{
	if (TargetId.IsNone() || !GetWorld())
	{
		return nullptr;
	}
	for (TActorIterator<AJRInteriorPortal> It(GetWorld()); It; ++It)
	{
		if (*It != this && It->PortalId == TargetId)
		{
			return *It;
		}
	}
	return nullptr;
}

bool AJRInteriorPortal::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return !bBusy && Cast<APawn>(InstigatorActor) != nullptr && FindTarget() != nullptr;
}

FText AJRInteriorPortal::GetInteractionText_Implementation() const
{
	return Prompt.IsEmpty() ? NSLOCTEXT("JogoResgate", "PortalEnter", "Entrar") : Prompt;
}

FTransform AJRInteriorPortal::GetArrivalTransform(float CapsuleHalfHeight) const
{
	const FRotator Yaw(0.f, GetActorRotation().Yaw, 0.f);
	const FVector Loc = GetActorLocation() + Yaw.Vector() * ArrivalDistance + FVector(0.f, 0.f, CapsuleHalfHeight + 4.f);
	return FTransform(Yaw, Loc);
}

void AJRInteriorPortal::Interact_Implementation(AActor* InstigatorActor)
{
	APawn* Pawn = Cast<APawn>(InstigatorActor);
	AJRInteriorPortal* Target = FindTarget();
	if (!Pawn || !Target || bBusy)
	{
		if (!Target)
		{
			UE_LOG(LogJR, Warning, TEXT("%s: porta sem destino (TargetId=%s)."), *GetName(), *TargetId.ToString());
		}
		return;
	}
	bBusy = true;
	Traveler = Pawn;
	Destination = Target;
	if (APlayerController* PC = Cast<APlayerController>(Pawn->GetController()))
	{
		if (PC->PlayerCameraManager)
		{
			PC->PlayerCameraManager->StartCameraFade(0.f, 1.f, FadeSeconds, FLinearColor::Black, false, true);
		}
		PC->SetIgnoreMoveInput(true);
	}
	GetWorldTimerManager().SetTimer(TravelTimer, this, &AJRInteriorPortal::FinishTravel, FadeSeconds + 0.05f, false);
}

void AJRInteriorPortal::FinishTravel()
{
	bBusy = false;
	APawn* Pawn = Traveler.Get();
	AJRInteriorPortal* Target = Destination.Get();
	Traveler.Reset();
	Destination.Reset();
	if (!Pawn)
	{
		return;
	}
	APlayerController* PC = Cast<APlayerController>(Pawn->GetController());
	if (Target)
	{
		float HalfHeight = 90.f;
		if (const ACharacter* Char = Cast<ACharacter>(Pawn))
		{
			HalfHeight = Char->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			if (UCharacterMovementComponent* Move = Char->GetCharacterMovement())
			{
				Move->StopMovementImmediately();
			}
		}
		const FTransform Arrival = Target->GetArrivalTransform(HalfHeight);
		FVector Loc = Arrival.GetLocation();
		// [A-098] Apoia no piso de verdade (trace para baixo) em vez de confiar na altura calculada.
		FHitResult Floor;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(JRPortalFloor), false, Pawn);
		if (GetWorld()->LineTraceSingleByChannel(Floor, Loc + FVector(0.f, 0.f, 60.f), Loc - FVector(0.f, 0.f, 400.f), ECC_Visibility, Q))
		{
			Loc.Z = Floor.ImpactPoint.Z + HalfHeight + 2.f;
		}
		Pawn->SetActorLocationAndRotation(Loc, Arrival.Rotator(), false, nullptr, ETeleportType::TeleportPhysics);
		if (ACharacter* Char = Cast<ACharacter>(Pawn))
		{
			if (UCharacterMovementComponent* Move = Char->GetCharacterMovement())
			{
				Move->SetMovementMode(MOVE_Walking);
			}
		}
		UE_LOG(LogJR, Log, TEXT("[interiores] %s -> %s em %s (KillZ %.0f)"), *PortalId.ToString(), *Target->GetPortalId().ToString(),
			*Loc.ToCompactString(), GetWorld()->GetWorldSettings() ? GetWorld()->GetWorldSettings()->KillZ : 0.f);
		if (PC)
		{
			PC->SetControlRotation(FRotator(-10.f, Arrival.Rotator().Yaw, 0.f));
		}
	}
	if (PC)
	{
		PC->ResetIgnoreMoveInput(); // [A-098] zera o contador mesmo se o E foi apertado duas vezes
		if (PC->PlayerCameraManager)
		{
			PC->PlayerCameraManager->StartCameraFade(1.f, 0.f, FadeSeconds, FLinearColor::Black, false, false);
		}
	}
}

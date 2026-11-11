// Copyright utrazin. All Rights Reserved.

#include "Interactions/JRRescueTarget.h"
#include "Animation/AnimInstance.h"
#include "Characters/JRCharacter.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "TimerManager.h"

AJRRescueTarget::AJRRescueTarget()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	CageMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CageMesh"));
	CageMesh->SetupAttachment(Root);
	VictimMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("VictimMesh"));
	VictimMesh->SetupAttachment(Root);
	PlayerAlignPoint = CreateDefaultSubobject<USceneComponent>(TEXT("PlayerAlignPoint"));
	PlayerAlignPoint->SetupAttachment(Root);
	PlayerAlignPoint->SetRelativeLocation(FVector(80.f, 0.f, 0.f));
	PlayerAlignPoint->SetRelativeRotation(FRotator(0.f, 180.f, 0.f));
	InteractionText = NSLOCTEXT("JogoResgate", "RescueInteract", "Libertar");
}

bool AJRRescueTarget::CanInteract_Implementation(AActor* InstigatorActor) const
{
	const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>();
	return !bRescued && Objective && Objective->GetStage() == EJRLevelStage::Rescue && InstigatorActor && InstigatorActor->IsA<AJRCharacter>();
}

FText AJRRescueTarget::GetInteractionText_Implementation() const
{
	return InteractionText;
}

void AJRRescueTarget::Interact_Implementation(AActor* InstigatorActor)
{
	if (!Execute_CanInteract(this, InstigatorActor))
	{
		return;
	}
	bRescued = true;
	OnCageOpened();

	AJRCharacter* Character = Cast<AJRCharacter>(InstigatorActor);
	Character->SetActorLocationAndRotation(PlayerAlignPoint->GetComponentLocation(), PlayerAlignPoint->GetComponentRotation(),
		false, nullptr, ETeleportType::TeleportPhysics);
	if (AController* C = Character->GetController())
	{
		C->SetIgnoreMoveInput(true);
	}
	const float PlayerDuration = Character->PlayRescueHug();
	float VictimDuration = 0.f;
	if (VictimHugMontage && VictimMesh->GetAnimInstance())
	{
		VictimDuration = VictimMesh->GetAnimInstance()->Montage_Play(VictimHugMontage);
	}
	const float Duration = FMath::Max3(PlayerDuration, VictimDuration, 0.f);
	GetWorldTimerManager().SetTimer(FinishTimer, this, &AJRRescueTarget::FinishRescue, Duration > 0.f ? Duration : FallbackHugDuration, false);
}

void AJRRescueTarget::FinishRescue()
{
	OnRescueCompleted();
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->CompleteLevel();
	}
}

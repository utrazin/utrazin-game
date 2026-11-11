// Copyright utrazin. All Rights Reserved.

#include "Levels/JRCheckpoint.h"
#include "Components/ArrowComponent.h"
#include "Components/BoxComponent.h"
#include "Core/JRPlayerController.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Vehicles/JRVehiclePawn.h"

AJRCheckpoint::AJRCheckpoint()
{
	PrimaryActorTick.bCanEverTick = false;

	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetBoxExtent(FVector(400.f, 600.f, 300.f));
	Trigger->SetCollisionProfileName(TEXT("Trigger"));
	RootComponent = Trigger;

	RespawnPoint = CreateDefaultSubobject<UArrowComponent>(TEXT("RespawnPoint"));
	RespawnPoint->SetupAttachment(Trigger);
}

void AJRCheckpoint::BeginPlay()
{
	Super::BeginPlay();
	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AJRCheckpoint::HandleOverlap);
}

FTransform AJRCheckpoint::GetRespawnTransform() const
{
	return RespawnPoint->GetComponentTransform();
}

void AJRCheckpoint::HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	const APawn* Pawn = Cast<APawn>(OtherActor);
	if (bReached || !Pawn || !Pawn->IsPlayerControlled())
	{
		return;
	}
	bReached = true;

	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->ReachCheckpoint(this);
	}
	if (bIsVehicleTransition && Pawn->IsA<AJRVehiclePawn>())
	{
		if (AJRPlayerController* PC = Cast<AJRPlayerController>(Pawn->GetController()))
		{
			PC->RequestExitVehicle(GetRespawnTransform());
		}
	}
}

// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRStoryTrigger.h"
#include "Audio/JRAudio.h" // [Áudio/A-061]
#include "Characters/JRCharacter.h"
#include "EngineUtils.h"
#include "Interactions/JRRescueTarget.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "UI/JRHUD.h"

AJRStoryTrigger::AJRStoryTrigger()
{
	PrimaryActorTick.bCanEverTick = false;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetBoxExtent(FVector(800.f, 800.f, 400.f));
	Box->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	RootComponent = Box;
}

void AJRStoryTrigger::BeginPlay()
{
	Super::BeginPlay();
	Box->OnComponentBeginOverlap.AddDynamic(this, &AJRStoryTrigger::HandleOverlap);
}

void AJRStoryTrigger::HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	const APawn* Pawn = Cast<APawn>(OtherActor);
	if (bDone || !Pawn || !Pawn->IsPlayerControlled() || (bOnFootOnly && !Pawn->IsA<AJRCharacter>()))
	{
		return;
	}
	if (bCompletesLevel)
	{
		for (TActorIterator<AJRRescueTarget> It(GetWorld()); It; ++It)
		{
			if (!It->IsRescued())
			{
				AJRHUD::Toast(this, TEXT("Falta a sobrevivente! Volte à vila."), FLinearColor(1.f, 0.5f, 0.3f));
				return; // dispara de novo quando ela estiver livre
			}
		}
	}
	bDone = true;
	if (!Message.IsEmpty())
	{
		UJRAudio::Play2D(this, TEXT("UI.Radio")); // [Áudio/A-061] estática de rádio na mensagem da história
	}
	if (bCompletesLevel)
	{
		if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
		{
			Objective->CompleteLevel();
		}
	}
	const APlayerController* PC = Cast<APlayerController>(Pawn->GetController());
	if (AJRHUD* Hud = PC ? Cast<AJRHUD>(PC->GetHUD()) : nullptr)
	{
		if (!Message.IsEmpty())
		{
			Hud->ShowToast(Message, FLinearColor(1.f, 0.95f, 0.7f));
		}
		if (!ObjectiveHint.IsEmpty())
		{
			Hud->SetCurrentTask(ObjectiveHint, TaskTarget.Get(), TaskReachRadius); // [A-064]
		}
	}
}

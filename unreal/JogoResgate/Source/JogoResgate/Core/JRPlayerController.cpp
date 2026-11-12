// Copyright utrazin. All Rights Reserved.

#include "Core/JRPlayerController.h"
#include "Characters/JRCharacter.h"
#include "Core/JRGameMode.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "InputMappingContext.h"
#include "JogoResgate.h"
#include "Vehicles/JRVehiclePawn.h"

void AJRPlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	ApplyMappingContextFor(InPawn);
	if (AJRCharacter* OnFootChar = Cast<AJRCharacter>(InPawn))
	{
		OnFootCharacter = OnFootChar;
	}
	OnControlledPawnChanged.Broadcast(InPawn);
}

void AJRPlayerController::ApplyMappingContextFor(const APawn* InPawn)
{
	UEnhancedInputLocalPlayerSubsystem* Subsystem = GetLocalPlayer()
		? GetLocalPlayer()->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>() : nullptr;
	if (!Subsystem)
	{
		return;
	}
	Subsystem->ClearAllMappings();
	for (UInputMappingContext* Context : GlobalMappingContexts)
	{
		if (Context)
		{
			Subsystem->AddMappingContext(Context, 10);
		}
	}
	const bool bInVehicle = InPawn && InPawn->IsA<AJRVehiclePawn>();
	for (UInputMappingContext* Context : bInVehicle ? VehicleMappingContexts : OnFootMappingContexts)
	{
		if (Context)
		{
			Subsystem->AddMappingContext(Context, 0);
		}
	}
}

bool AJRPlayerController::RequestExitVehicle(const FTransform& FallbackTransform)
{
	AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(GetPawn());
	if (!Vehicle || bExitInProgress)
	{
		return false;
	}
	bExitInProgress = true;

	AJRGameMode* GameMode = GetWorld()->GetAuthGameMode<AJRGameMode>();
	const FTransform SpawnTransform = Vehicle->GetExitTransform();

	// Reutiliza o personagem se já existir: a transição nunca duplica personagens.
	AJRCharacter* OnFootChar = OnFootCharacter;
	if (OnFootChar)
	{
		OnFootChar->SetActorTransform(SpawnTransform, false, nullptr, ETeleportType::TeleportPhysics);
	}
	else
	{
		const TSubclassOf<AJRCharacter> CharacterClass = GameMode ? GameMode->ResolveCharacterClass() : nullptr;
		if (!CharacterClass)
		{
			UE_LOG(LogJR, Error, TEXT("RequestExitVehicle: classe de personagem não definida."));
			bExitInProgress = false;
			return false;
		}
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
		OnFootChar = GetWorld()->SpawnActor<AJRCharacter>(CharacterClass, SpawnTransform, Params);
		if (!OnFootChar)
		{
			OnFootChar = GetWorld()->SpawnActor<AJRCharacter>(CharacterClass, FallbackTransform, Params);
		}
		if (!OnFootChar)
		{
			UE_LOG(LogJR, Error, TEXT("RequestExitVehicle: falha ao spawnar personagem."));
			bExitInProgress = false;
			return false;
		}
	}

	Vehicle->ParkAndDisable();
	ParkedVehicle = Vehicle;
	Possess(OnFootChar); // UnPossessed do veículo zera os inputs
	if (GameMode)
	{
		GameMode->ApplySelectedSkin(OnFootChar);
	}
	OnFootChar->PlayExitVehicleSequence();
	bExitInProgress = false;
	return true;
}

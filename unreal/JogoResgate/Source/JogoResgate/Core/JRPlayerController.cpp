// Copyright utrazin. All Rights Reserved.

#include "Core/JRPlayerController.h"
#include "AI/JRAIDirector.h"
#include "Characters/JRCharacter.h"
#include "Core/JRGameInstance.h"
#include "Core/JRGameMode.h"
#include "EnhancedInputComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "UI/JRHUD.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "InputMappingContext.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "Progression/JRProgressionSubsystem.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehiclePawn.h"

void AJRPlayerController::JRHeroi(const FString& CharacterId)
{
	UJRProgressionSubsystem* Progression = GetGameInstance() ? GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>() : nullptr;
	if (!Progression)
	{
		UE_LOG(LogJR, Warning, TEXT("JRHeroi: sem ProgressionSubsystem."));
		return;
	}
	Progression->SelectCharacter(FName(*CharacterId), NAME_None);
	UE_LOG(LogJR, Log, TEXT("JRHeroi: personagem selecionado %s. Reiniciando a fase."), *CharacterId);
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}

void AJRPlayerController::JRDirector(const FString& Command)
{
	JRDiretor(Command);
}

void AJRPlayerController::JRDiretor(const FString& Command)
{
	AJRAIDirector* Director = AJRAIDirector::Find(this);
	TArray<FString> Words;
	Command.TrimStartAndEnd().ToLower().ParseIntoArrayWS(Words);
	const FString Cmd = Words.Num() > 0 ? Words[0] : FString();
	if (Cmd.IsEmpty() || Cmd == TEXT("debug"))
	{
		const bool bNew = !AJRAIDirector::IsDebugEnabled();
		AJRAIDirector::SetDebugEnabled(bNew);
		UE_LOG(LogJR, Log, TEXT("JRDiretor: debug %s%s"), bNew ? TEXT("ligado") : TEXT("desligado"),
			Director ? TEXT("") : TEXT(" (nenhum AJRAIDirector neste mapa!)"));
		return;
	}
	if (!Director)
	{
		UE_LOG(LogJR, Warning, TEXT("JRDiretor: nenhum AJRAIDirector neste mapa (rode tools/unreal/setup_ai_director.py)."));
		return;
	}
	if (Cmd == TEXT("horda") || Cmd == TEXT("horde"))
	{
		const int32 Size = Words.Num() > 1 ? FCString::Atoi(*Words[1]) : 0;
		Director->TriggerHorde(TEXT("Console"), 60.f, Size);
	}
	else if (Cmd == TEXT("calma") || Cmd == TEXT("calmaria"))
	{
		Director->ForcePhase(EJRDirectorPhase::Relax);
	}
	else if (Cmd == TEXT("subida"))
	{
		Director->ForcePhase(EJRDirectorPhase::BuildUp);
	}
	else if (Cmd == TEXT("status"))
	{
		UE_LOG(LogJR, Log, TEXT("%s"), *Director->GetStatusLine());
	}
	else if (Cmd == TEXT("off") || Cmd == TEXT("on"))
	{
		Director->SetDirectorEnabled(Cmd == TEXT("on"));
		UE_LOG(LogJR, Log, TEXT("JRDiretor: diretor %s"), Director->IsDirectorEnabled() ? TEXT("ligado") : TEXT("desligado"));
	}
	else
	{
		UE_LOG(LogJR, Warning, TEXT("JRDiretor: comandos: (vazio) | horda [tamanho] | calma | subida | status | off | on"));
	}
}

void AJRPlayerController::JRCarDamage(float Amount)
{
	AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(GetPawn());
	if (!Vehicle || !Vehicle->GetDamageComponent())
	{
		UE_LOG(LogJR, Warning, TEXT("JRCarDamage: você não está num carro."));
		return;
	}
	const float Value = Amount > 0.f ? Amount : 25.f;
	UJRVehicleDamageComponent* Damage = Vehicle->GetDamageComponent();
	Damage->ApplyZoneDamage(EJRVehicleZone::Front, Value);
	Damage->ApplyZoneDamage(EJRVehicleZone::Engine, Value);
	UE_LOG(LogJR, Log, TEXT("JRCarDamage: integridade agora %.0f%%"), Damage->GetIntegrity() * 100.f);
}

void AJRPlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	ApplyMappingContextFor(InPawn);
	if (AJRCharacter* OnFootChar = Cast<AJRCharacter>(InPawn))
	{
		OnFootCharacter = OnFootChar;
	}
	// Troca de pawn (sair/entrar no carro, respawn) é um corte de câmera: aplica a visão escolhida na hora.
	ApplyViewPreference(InPawn, true);
	OnControlledPawnChanged.Broadcast(InPawn);
}

void AJRPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	if (UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(InputComponent))
	{
		if (ToggleMapAction)
		{
			Input->BindAction(ToggleMapAction, ETriggerEvent::Started, this, &AJRPlayerController::HandleToggleMap);
		}
		if (ToggleViewAction)
		{
			Input->BindAction(ToggleViewAction, ETriggerEvent::Started, this, &AJRPlayerController::HandleToggleView);
		}
	}
}

void AJRPlayerController::HandleToggleMap(const FInputActionValue& Value)
{
	if (AJRHUD* JRHud = Cast<AJRHUD>(GetHUD()))
	{
		JRHud->ToggleBigMap();
	}
}

void AJRPlayerController::HandleToggleView(const FInputActionValue& Value)
{
	JRVisao();
}

bool AJRPlayerController::PrefersFirstPersonView() const
{
	if (const UJRGameInstance* JRInstance = GetGameInstance<UJRGameInstance>())
	{
		return JRInstance->bPreferFirstPersonView;
	}
	return bPreferFirstPersonLocal;
}

void AJRPlayerController::JRVisao()
{
	const bool bNewFirstPerson = !PrefersFirstPersonView();
	bPreferFirstPersonLocal = bNewFirstPerson;
	if (UJRGameInstance* JRInstance = GetGameInstance<UJRGameInstance>())
	{
		JRInstance->bPreferFirstPersonView = bNewFirstPerson;
	}
	ApplyViewPreference(GetPawn(), false);
	AJRHUD::Toast(this, bNewFirstPerson ? FString(TEXT("Primeira pessoa [V]")) : FString(TEXT("Terceira pessoa [V]")),
		FLinearColor(0.6f, 0.9f, 1.f));
}

void AJRPlayerController::ApplyViewPreference(APawn* InPawn, bool bInstant)
{
	const bool bFirstPerson = PrefersFirstPersonView();
	if (AJRCharacter* Hero = Cast<AJRCharacter>(InPawn))
	{
		Hero->SetFirstPersonView(bFirstPerson, bInstant);
	}
	else if (AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(InPawn))
	{
		Vehicle->SetFirstPersonView(bFirstPerson, bInstant);
	}
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
	bool bNewCharacter = false;
	if (OnFootChar)
	{
		// Estava escondido dentro do carro (RequestEnterVehicle): volta a aparecer, colidir e andar.
		OnFootChar->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
		OnFootChar->SetActorHiddenInGame(false);
		OnFootChar->SetActorEnableCollision(true);
		if (UCharacterMovementComponent* Move = OnFootChar->GetCharacterMovement())
		{
			Move->SetMovementMode(MOVE_Walking);
		}
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
		bNewCharacter = true;
	}

	Vehicle->ParkAndDisable();
	ParkedVehicle = Vehicle;
	Possess(OnFootChar); // UnPossessed do veículo zera os inputs
	if (GameMode)
	{
		GameMode->ApplySelectedSkin(OnFootChar);
		if (bNewCharacter)
		{
			// Renasceu no carro: o herói novo recebe as armas do checkpoint (o mapa recarregou).
			GameMode->ApplyRespawnLoadout(OnFootChar);
		}
	}
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		if (Objective->GetStage() == EJRLevelStage::Driving)
		{
			Objective->SetStage(EJRLevelStage::OnFoot);
		}
	}
	OnFootChar->PlayExitFromVehicle(Vehicle, Vehicle->GetSeatTransform());
	bExitInProgress = false;
	return true;
}

bool AJRPlayerController::RequestEnterVehicle(AJRVehiclePawn* Vehicle)
{
	AJRCharacter* Hero = Cast<AJRCharacter>(GetPawn());
	if (!Vehicle || !Hero || bExitInProgress || Vehicle->IsWrecked() || Vehicle->IsPlayerControlled())
	{
		return false;
	}
	const FName CarKey = Vehicle->GetRequiredKeyItem();
	if (!CarKey.IsNone() && !HasKeyItem(CarKey))
	{
		AJRHUD::Toast(this, TEXT("Trancado. Você precisa da chave do buggy."), FLinearColor(1.f, 0.6f, 0.2f));
		return false;
	}
	const FName Pending = Vehicle->GetPendingRequiredItem();
	if (!Pending.IsNone())
	{
		if (!HasKeyItem(Pending))
		{
			AJRHUD::Toast(this, FString::Printf(TEXT("O carro não anda: falta %s."), *Vehicle->GetPendingRequiredItemLabel()),
				FLinearColor(1.f, 0.6f, 0.2f));
			return false;
		}
		ConsumeKeyItem(Pending);
		Vehicle->ClearPendingRequiredItem();
		AJRHUD::Toast(this, TEXT("Tanque abastecido!"), FLinearColor(0.4f, 1.f, 0.5f));
	}

	// O herói "entra": some, para de colidir e vai junto com o carro (volta em RequestExitVehicle).
	OnFootCharacter = Hero;
	if (UCharacterMovementComponent* Move = Hero->GetCharacterMovement())
	{
		Move->StopMovementImmediately();
		Move->DisableMovement();
	}
	Hero->SetActorEnableCollision(false);
	Hero->SetActorHiddenInGame(true);
	Hero->AttachToActor(Vehicle, FAttachmentTransformRules::KeepWorldTransform);

	Vehicle->EnableDriving();
	Possess(Vehicle); // PossessedBy do carro mostra o motorista
	// [A-058] Entrar no carro: mistura suave da câmera do herói para a do carro (antes era corte seco).
	SetViewTarget(Hero);
	SetViewTargetWithBlend(Vehicle, 0.6f, VTBlend_EaseInOut, 2.f, false);
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		if (Objective->GetStage() == EJRLevelStage::OnFoot)
		{
			Objective->SetStage(EJRLevelStage::Driving);
		}
	}
	UE_LOG(LogJR, Log, TEXT("RequestEnterVehicle: %s entrou em %s"), *GetNameSafe(Hero), *GetNameSafe(Vehicle));
	return true;
}

void AJRPlayerController::GiveKeyItem(FName Item)
{
	if (!Item.IsNone())
	{
		KeyItems.Add(Item);
	}
}

bool AJRPlayerController::ConsumeKeyItem(FName Item)
{
	return KeyItems.Remove(Item) > 0;
}

void AJRPlayerController::JRItens()
{
	GiveKeyItem(TEXT("CarKey"));
	GiveKeyItem(TEXT("Fuel"));
	GiveKeyItem(TEXT("Explosive"));
	AJRHUD::Toast(this, TEXT("Teste: chave do buggy, galão e explosivos."), FLinearColor(0.6f, 0.9f, 1.f));
}

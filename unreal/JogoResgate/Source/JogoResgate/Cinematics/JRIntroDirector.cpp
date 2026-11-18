// Copyright utrazin. All Rights Reserved.

#include "Cinematics/JRIntroDirector.h"
#include "AI/JREnemyCharacter.h"
#include "Audio/JRAudio.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/LightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/JRGameMode.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FX/JRFXSubsystem.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Gameplay/JRStoryTrigger.h"
#include "InputCoreTypes.h"
#include "JogoResgate.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Levels/JRCheckpoint.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Progression/JRProgressionSubsystem.h"
#include "Save/JRSaveGame.h"
#include "UI/JRIntroHUD.h"
#include "UObject/UnrealType.h"

// ======================================================================
// Abertura (A-074). Os tempos de cada ato vêm das propriedades; as câmeras são calculadas a partir da nave caída,
// do ponto do herói (este ator) e do checkpoint do início. Nada aqui depende de Level Sequence.
// ======================================================================

namespace
{
	const FLinearColor FireOrange(1.f, 0.48f, 0.12f);
	constexpr float SubtitleFade = 0.25f;
	constexpr float SkipFadeOut = 0.35f;
	constexpr float SkipFadeIn = 0.6f;

	/** 0..1 dentro da janela [T0, T1] com entrada e saída suaves (legendas). */
	float Window(float T, float T0, float T1)
	{
		return FMath::Clamp(FMath::Min((T - T0) / SubtitleFade, (T1 - T) / SubtitleFade), 0.f, 1.f);
	}

	FVector Bezier(const FVector& P0, const FVector& P1, const FVector& P2, const FVector& P3, float Alpha)
	{
		const float Inv = 1.f - Alpha;
		return P0 * (Inv * Inv * Inv) + P1 * (3.f * Inv * Inv * Alpha) + P2 * (3.f * Inv * Alpha * Alpha) + P3 * (Alpha * Alpha * Alpha);
	}

	bool AnyKeyDown(const APlayerController* PC, std::initializer_list<FKey> Keys)
	{
		for (const FKey& Key : Keys)
		{
			if (PC->IsInputKeyDown(Key))
			{
				return true;
			}
		}
		return false;
	}

	bool AnyKeyPressed(const APlayerController* PC, std::initializer_list<FKey> Keys)
	{
		for (const FKey& Key : Keys)
		{
			if (PC->WasInputKeyJustPressed(Key))
			{
				return true;
			}
		}
		return false;
	}

	void SetActorLightsVisible(AActor* Actor, bool bVisible)
	{
		if (!Actor)
		{
			return;
		}
		Actor->SetActorHiddenInGame(!bVisible);
		TArray<ULightComponent*> Lights;
		Actor->GetComponents(Lights);
		for (ULightComponent* Light : Lights)
		{
			Light->SetVisibility(bVisible);
		}
	}
}

AJRIntroDirector::AJRIntroDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	PrimaryActorTick.TickGroup = TG_PostPhysics;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	CineCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("CineCamera"));
	CineCamera->SetupAttachment(Root);
	CineCamera->bConstrainAspectRatio = false;
	CineCamera->SetFieldOfView(60.f);

	AlarmLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("AlarmLight"));
	AlarmLight->SetupAttachment(Root);
	AlarmLight->SetMobility(EComponentMobility::Movable);
	AlarmLight->IntensityUnits = ELightUnits::Candelas;
	AlarmLight->Intensity = 0.f;
	AlarmLight->LightColor = FColor(255, 24, 12);
	AlarmLight->AttenuationRadius = 2500.f;
	AlarmLight->CastShadows = false;
	AlarmLight->SetVisibility(false);

	SetCanBeDamaged(false);
}

// ====================================================================== estáticos

AJRIntroDirector* AJRIntroDirector::FindInWorld(UWorld* World)
{
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AJRIntroDirector> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

bool AJRIntroDirector::CanPlayIntro() const
{
	const UWorld* World = GetWorld();
	return bEnabled && World && (!World->IsPlayInEditor() || bPlayInEditor);
}

bool AJRIntroDirector::IsIntroSeen(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
	const UJRProgressionSubsystem* Progression = GI ? GI->GetSubsystem<UJRProgressionSubsystem>() : nullptr;
	return Progression && Progression->GetSave() && Progression->GetSave()->bIntroSeen;
}

void AJRIntroDirector::SetIntroSeen(const UObject* WorldContext, bool bSeen)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
	UJRProgressionSubsystem* Progression = GI ? GI->GetSubsystem<UJRProgressionSubsystem>() : nullptr;
	if (Progression && Progression->GetSave() && Progression->GetSave()->bIntroSeen != bSeen)
	{
		Progression->GetSave()->bIntroSeen = bSeen;
		Progression->SaveNow();
	}
}

// ====================================================================== início

void AJRIntroDirector::BeginPlay()
{
	Super::BeginPlay();
	UWorld* World = GetWorld();
	if (!World || FindInWorld(World) != this)
	{
		return; // só um diretor por mapa
	}
	const AJRGameMode* GameModeJR = World->GetAuthGameMode<AJRGameMode>();
	const UGameInstance* GI = World->GetGameInstance();
	const UJRProgressionSubsystem* Progression = GI ? GI->GetSubsystem<UJRProgressionSubsystem>() : nullptr;
	const bool bRestarting = Progression && Progression->bRestartingFromCheckpoint;

	if (GameModeJR && GameModeJR->ShouldPlayIntro())
	{
		Mode = EMode::Full;
	}
	else if (bEnabled && bStartScreenOnContinue && !bRestarting && !World->IsPlayInEditor())
	{
		Mode = EMode::MenuOnly; // jogo aberto com um checkpoint salvo no meio da fase
	}
	else
	{
		Mode = EMode::None;
		return;
	}

	if (Mode == EMode::Full)
	{
		ResolveScene();
		BuildPath();
		HideCrashSite();
		Overlay.Black = 1.f; // nada do jogo aparece antes da câmera da abertura assumir
	}
	SetPhase(EJRIntroPhase::Menu);
	Overlay.bVisible = true;
	Overlay.bHideGameHud = true;
	SetActorTickEnabled(true);
	UE_LOG(LogJR, Log, TEXT("Abertura: modo %s (visto antes: %s)"), Mode == EMode::Full ? TEXT("completo") : TEXT("só tela de start"),
		IsIntroSeen(this) ? TEXT("sim") : TEXT("não"));
}

void AJRIntroDirector::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	FreezeEnemies(false);
	DestroyFlightShip();
	Super::EndPlay(EndPlayReason);
}

bool AJRIntroDirector::AcquirePlayer()
{
	APlayerController* PC = PlayerPC.Get();
	if (!PC)
	{
		PC = GetWorld()->GetFirstPlayerController();
		PlayerPC = PC;
	}
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn)
	{
		return false;
	}
	if (PlayerPawn.Get() != Pawn)
	{
		if (bPlayerLocked)
		{
			UnlockPlayer(); // trocou de pawn no meio (não deveria): solta o antigo
		}
		PlayerPawn = Pawn;
		LockPlayer();
	}
	return true;
}

void AJRIntroDirector::LockPlayer()
{
	APlayerController* PC = PlayerPC.Get();
	APawn* Pawn = PlayerPawn.Get();
	if (!PC || !Pawn || bPlayerLocked)
	{
		return;
	}
	bPlayerLocked = true;
	Pawn->DisableInput(PC);
	PC->SetIgnoreMoveInput(true);
	PC->SetIgnoreLookInput(true);
	bPawnWasDamageable = Pawn->CanBeDamaged();
	Pawn->SetCanBeDamaged(false);
	if (Mode == EMode::Full && !bHeroShown)
	{
		Pawn->SetActorHiddenInGame(true);
		PC->SetViewTarget(this);
	}
	FInputModeGameAndUI InputMode;
	InputMode.SetHideCursorDuringCapture(false);
	InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	PC->SetInputMode(InputMode);
	PC->bShowMouseCursor = true;
}

void AJRIntroDirector::UnlockPlayer()
{
	APlayerController* PC = PlayerPC.Get();
	APawn* Pawn = PlayerPawn.Get();
	if (!bPlayerLocked)
	{
		return;
	}
	bPlayerLocked = false;
	if (PC)
	{
		PC->SetIgnoreMoveInput(false);
		PC->SetIgnoreLookInput(false);
		PC->bShowMouseCursor = false;
		PC->SetInputMode(FInputModeGameOnly());
	}
	if (Pawn)
	{
		if (PC)
		{
			Pawn->EnableInput(PC);
		}
		Pawn->SetCanBeDamaged(bPawnWasDamageable);
		Pawn->SetActorHiddenInGame(false);
	}
}

void AJRIntroDirector::FreezeEnemies(bool bFreeze)
{
	if (!bFreeze)
	{
		for (const TPair<TWeakObjectPtr<AActor>, float>& Pair : FrozenEnemies)
		{
			if (AActor* Enemy = Pair.Key.Get())
			{
				Enemy->CustomTimeDilation = Pair.Value;
			}
		}
		FrozenEnemies.Reset();
		return;
	}
	if (!GetWorld())
	{
		return;
	}
	// Zumbis param durante a tela de start e a abertura (inclusive os que o spawner cria nesse tempo).
	for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
	{
		AJREnemyCharacter* Enemy = *It;
		if (!FrozenEnemies.Contains(Enemy))
		{
			FrozenEnemies.Add(Enemy, Enemy->CustomTimeDilation);
			Enemy->CustomTimeDilation = 0.f;
		}
	}
}

void AJRIntroDirector::SetPhase(EJRIntroPhase NewPhase)
{
	Phase = NewPhase;
	PhaseTime = 0.f;
	NextAlarm = 0.f;
	NextSpark = 0.f;
	Overlay.Subtitle.Reset();
	Overlay.SubtitleAlpha = 0.f;
}

// ====================================================================== cena

void AJRIntroDirector::ResolveScene()
{
	UWorld* World = GetWorld();
	HeroMark = GetActorLocation();
	HeroFacing = GetActorForwardVector().GetSafeNormal2D();
	if (HeroFacing.IsNearlyZero())
	{
		HeroFacing = FVector::ForwardVector;
	}

	if (!CrashedShip)
	{
		float BestDist = TNumericLimits<float>::Max();
		for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
		{
			const UStaticMeshComponent* Comp = It->GetStaticMeshComponent();
			const UStaticMesh* Mesh = Comp ? Comp->GetStaticMesh() : nullptr;
			if (Mesh && !ShipMeshHint.IsEmpty() && Mesh->GetName().Contains(ShipMeshHint))
			{
				const float Dist = FVector::Dist(It->GetActorLocation(), HeroMark);
				if (Dist < BestDist)
				{
					BestDist = Dist;
					CrashedShip = *It;
				}
			}
		}
	}
	if (CrashedShip)
	{
		FVector Origin;
		FVector Extent;
		CrashedShip->GetActorBounds(true, Origin, Extent);
		CrashPoint = Origin;
		ShipRadius = FMath::Clamp(static_cast<float>(FMath::Max(Extent.X, Extent.Y)), 300.f, 4000.f);
		CrashedShipQuat = CrashedShip->GetActorQuat();
		CrashedShipScale = CrashedShip->GetActorScale3D();
	}
	else
	{
		CrashPoint = HeroMark - HeroFacing * 2500.f + FVector(0.f, 0.f, 200.f);
		UE_LOG(LogJR, Warning, TEXT("Abertura: nave caída não encontrada (procure %s). Rode tools/unreal/setup_intro.py."), *ShipMeshHint);
	}

	if (FireLights.Num() == 0)
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			const ULightComponent* Light = It->FindComponentByClass<ULightComponent>();
			if (Light && *It != this && FVector::Dist(It->GetActorLocation(), CrashPoint) < 3000.f)
			{
				const FLinearColor C = Light->GetLightColor();
				if (C.R > 0.8f && C.B < 0.4f && C.G < 0.7f)
				{
					FireLights.Add(*It);
				}
			}
		}
	}

	// Direção de chegada: a nave deslizou para a frente (nariz da malha) até parar.
	const FQuat ModelOffset = FRotator(0.f, ShipModelYawOffset, 0.f).Quaternion();
	const FVector NoseLocal = ModelOffset.Inverse().RotateVector(FVector::ForwardVector);
	FVector Nose = CrashedShipQuat.RotateVector(NoseLocal).GetSafeNormal2D();
	if (Nose.IsNearlyZero())
	{
		Nose = (CrashPoint - HeroMark).GetSafeNormal2D();
	}
	ApproachDir = FRotator(0.f, ApproachYawExtra, 0.f).RotateVector(Nose).GetSafeNormal2D();
	if (ApproachDir.IsNearlyZero())
	{
		ApproachDir = FVector::ForwardVector;
	}

	CampPoint = HeroMark + HeroFacing * 6000.f;
	for (TActorIterator<AJRCheckpoint> It(World); It; ++It)
	{
		if (It->IsLevelStart())
		{
			CampPoint = It->GetActorLocation();
			break;
		}
	}
	ImpactCamDir = (HeroMark - CrashPoint).GetSafeNormal2D();
	if (ImpactCamDir.IsNearlyZero())
	{
		ImpactCamDir = FVector::CrossProduct(FVector::UpVector, ApproachDir);
	}
	MenuOrbitCenter = CrashPoint;
}

void AJRIntroDirector::BuildPath()
{
	PathAltitude = CruiseAltitude;
	const FVector Up = FVector::UpVector;
	for (int32 Pass = 0; Pass < 5; ++Pass)
	{
		PathB = CrashPoint - ApproachDir * DiveDistance + Up * PathAltitude;
		PathA = PathB - ApproachDir * CruiseDistance;
		PathC1 = PathB + ApproachDir * (DiveDistance * 0.4f);
		PathC2 = CrashPoint - ApproachDir * (DiveDistance * 0.18f) + Up * (PathAltitude * 0.22f);
		// Um morro no caminho? Sobe o voo até passar 20 m acima do chão (até 70% da descida).
		float Need = 1.f;
		const float TotalT = CabinSeconds + LoseControlSeconds * 0.7f;
		for (int32 Sample = 0; Sample <= 24; ++Sample)
		{
			const float SampleT = TotalT * static_cast<float>(Sample) / 24.f;
			const FVector Pos = PathPosition(SampleT);
			const float Ground = GroundZAt(Pos, -1.0e7f);
			const float Above = static_cast<float>(Pos.Z - CrashPoint.Z);
			if (Ground > Pos.Z - 2000.f && Above > 100.f)
			{
				Need = FMath::Max(Need, static_cast<float>((Ground + 2000.f - CrashPoint.Z) / Above));
			}
		}
		if (Need <= 1.01f)
		{
			break;
		}
		PathAltitude *= FMath::Min(Need * 1.05f, 4.f);
	}
	if (PathAltitude > CruiseAltitude + 1.f)
	{
		UE_LOG(LogJR, Log, TEXT("Abertura: voo subiu para %.0f m por causa do relevo."), PathAltitude / 100.f);
	}
}

FVector AJRIntroDirector::PathPosition(float T) const
{
	if (T <= CabinSeconds)
	{
		const float Alpha = FMath::Clamp(T / CabinSeconds, 0.f, 1.f);
		FVector Pos = FMath::Lerp(PathA, PathB, Alpha);
		Pos.Z += FMath::Sin(T * 1.7f) * 60.f;
		return Pos;
	}
	const float U = FMath::Clamp((T - CabinSeconds) / LoseControlSeconds, 0.f, 1.f);
	const float Accel = (U + 0.35f * U * U) / 1.35f; // começa na velocidade do voo e acelera
	return Bezier(PathB, PathC1, PathC2, CrashPoint, Accel);
}

FVector AJRIntroDirector::ShipForward(float T) const
{
	const float End = CabinSeconds + LoseControlSeconds;
	const float T0 = FMath::Min(T, End - 0.05f);
	const FVector Dir = (PathPosition(T0 + 0.05f) - PathPosition(T0)).GetSafeNormal();
	return Dir.IsNearlyZero() ? ApproachDir : Dir;
}

FQuat AJRIntroDirector::ShipRotation(float T) const
{
	FRotator Travel = ShipForward(T).Rotation();
	if (T <= CabinSeconds)
	{
		Travel.Roll = FMath::Sin(T * 1.3f) * 4.f;
	}
	else
	{
		const float U = FMath::Clamp((T - CabinSeconds) / LoseControlSeconds, 0.f, 1.f);
		Travel.Roll = FMath::Sin(T * 5.f) * 35.f * U + 180.f * U * U * U;
		Travel.Yaw += FMath::Sin(T * 2.3f) * 12.f * U;
		Travel.Pitch += FMath::Sin(T * 3.1f) * 6.f * U;
	}
	return Travel.Quaternion() * FRotator(0.f, ShipModelYawOffset, 0.f).Quaternion();
}

float AJRIntroDirector::GroundZAt(const FVector& Where, float Fallback) const
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return Fallback;
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRIntroGround), false);
	Query.AddIgnoredActor(this);
	if (CrashedShip)
	{
		Query.AddIgnoredActor(CrashedShip);
	}
	if (FlightShip)
	{
		Query.AddIgnoredActor(FlightShip);
	}
	if (const APawn* Pawn = PlayerPawn.Get())
	{
		Query.AddIgnoredActor(Pawn);
	}
	FHitResult Hit;
	const FVector From(Where.X, Where.Y, Where.Z + 30000.f);
	const FVector To(Where.X, Where.Y, Where.Z - 30000.f);
	if (World->LineTraceSingleByChannel(Hit, From, To, ECC_Visibility, Query))
	{
		return Hit.ImpactPoint.Z;
	}
	return Fallback;
}

FVector AJRIntroDirector::HeroPivot() const
{
	const APawn* Pawn = PlayerPawn.Get();
	return (Pawn ? Pawn->GetActorLocation() : HeroMark) + FVector(0.f, 0.f, 45.f);
}

void AJRIntroDirector::SetCamera(const FVector& Location, const FVector& LookAt, float Fov, float ShakeDeg, float ShakeCm)
{
	const FVector Dir = (LookAt - Location).GetSafeNormal();
	const FQuat Rot = Dir.IsNearlyZero() ? CineCamera->GetComponentQuat() : Dir.Rotation().Quaternion();
	SetCameraRot(Location, Rot, Fov, ShakeDeg, ShakeCm);
}

void AJRIntroDirector::SetCameraRot(const FVector& Location, const FQuat& Rotation, float Fov, float ShakeDeg, float ShakeCm)
{
	// Tremor de câmera feito à mão (ruído suave), sem asset de Camera Shake.
	const float N1 = FMath::PerlinNoise1D(RealTime * 7.3f);
	const float N2 = FMath::PerlinNoise1D(RealTime * 6.1f + 31.7f);
	const float N3 = FMath::PerlinNoise1D(RealTime * 8.7f + 77.1f);
	FRotator Rot = Rotation.Rotator();
	Rot.Pitch += N1 * ShakeDeg;
	Rot.Yaw += N2 * ShakeDeg;
	Rot.Roll += N3 * ShakeDeg * 0.6f;
	const FVector Loc = Location + FVector(N2, N3, N1) * ShakeCm;
	CineCamera->SetWorldLocationAndRotation(Loc, Rot);
	CineCamera->SetFieldOfView(Fov);
}

void AJRIntroDirector::SpawnFlightShip()
{
	if (FlightShip)
	{
		return;
	}
	UStaticMeshComponent* SourceComp = CrashedShip ? CrashedShip->FindComponentByClass<UStaticMeshComponent>() : nullptr;
	UStaticMesh* Mesh = FlightShipMesh.LoadSynchronous();
	if (!Mesh && SourceComp)
	{
		Mesh = SourceComp->GetStaticMesh();
	}
	if (!Mesh)
	{
		UE_LOG(LogJR, Warning, TEXT("Abertura: sem malha para a nave em voo (FlightShipMesh vazio e nave caída não achada)."));
		return;
	}
	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	SpawnParams.ObjectFlags |= RF_Transient;
	FlightShip = GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),
		FTransform(ShipRotation(0.f), PathPosition(0.f)), SpawnParams);
	if (!FlightShip)
	{
		return;
	}
	FlightShip->SetMobility(EComponentMobility::Movable);
	UStaticMeshComponent* Comp = FlightShip->GetStaticMeshComponent();
	Comp->SetStaticMesh(Mesh);
	Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Comp->SetCastShadow(true);
	if (SourceComp && SourceComp->GetStaticMesh() == Mesh)
	{
		for (int32 Index = 0; Index < SourceComp->GetNumMaterials(); ++Index)
		{
			Comp->SetMaterial(Index, SourceComp->GetMaterial(Index));
		}
	}
	FlightShip->SetActorScale3D(FlightShipScale > 0.f ? FVector(FlightShipScale) : CrashedShipScale);
	if (SmokeSystem)
	{
		SmokeFX = UNiagaraFunctionLibrary::SpawnSystemAttached(SmokeSystem, Comp, NAME_None, FVector::ZeroVector, FRotator::ZeroRotator,
			EAttachLocation::KeepRelativeOffset, true);
		if (SmokeFX)
		{
			SmokeFX->Deactivate(); // liga na explosão do motor
		}
	}
	AlarmLight->SetVisibility(true);
}

void AJRIntroDirector::DestroyFlightShip()
{
	if (FlightShip)
	{
		FlightShip->Destroy();
		FlightShip = nullptr;
	}
	SmokeFX = nullptr;
	if (AlarmLight)
	{
		AlarmLight->SetVisibility(false);
	}
}

void AJRIntroDirector::HideCrashSite()
{
	if (CrashedShip)
	{
		CrashedShip->SetActorHiddenInGame(true);
	}
	for (AActor* Light : FireLights)
	{
		SetActorLightsVisible(Light, false);
	}
	bCrashShown = false;
}

void AJRIntroDirector::ShowCrashSite(bool bWithEffects)
{
	if (CrashedShip)
	{
		CrashedShip->SetActorHiddenInGame(false);
	}
	for (AActor* Light : FireLights)
	{
		SetActorLightsVisible(Light, true);
	}
	bCrashShown = true;
	if (FireSystem)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, FireSystem, CrashPoint, FRotator::ZeroRotator, FVector::OneVector, false);
	}
	if (!bWithEffects)
	{
		return;
	}
	if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
	{
		FX->SpawnFlash(CrashPoint + FVector(0.f, 0.f, ShipRadius * 0.2f), FireOrange, 30.f, ShipRadius * 0.2f, ShipRadius * 1.4f, 0.9f,
			60000.f, ShipRadius * 6.f);
		// Faíscas e marcas de queimado em volta (a "poeira" do impacto sem Niagara).
		for (int32 Index = 0; Index < 6; ++Index)
		{
			const float Ang = 2.f * PI * static_cast<float>(Index) / 6.f + 0.4f;
			FVector At = CrashPoint + FVector(FMath::Cos(Ang), FMath::Sin(Ang), 0.f) * ShipRadius * FMath::FRandRange(0.6f, 1.2f);
			At.Z = GroundZAt(At, CrashPoint.Z);
			FX->SpawnPlasmaImpact(At, FVector::UpVector, FireOrange, 3.f, FMath::FRandRange(3.f, 5.f), true);
		}
	}
}

void AJRIntroDirector::StartFireLoop()
{
	if (bFireLoopStarted)
	{
		return;
	}
	bFireLoopStarted = true;
	USceneComponent* At = CrashedShip ? CrashedShip->GetRootComponent() : nullptr;
	if (At && !FireLoopId.IsNone())
	{
		FireLoop = UJRAudio::PlayAttached(this, FireLoopId, At, NAME_None, 0.8f);
	}
}

void AJRIntroDirector::ShowHero()
{
	APawn* Pawn = PlayerPawn.Get();
	if (!Pawn || bHeroShown)
	{
		return;
	}
	bHeroShown = true;
	FVector Loc = HeroMark;
	if (const ACharacter* Hero = Cast<ACharacter>(Pawn))
	{
		const float HalfHeight = Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		Loc.Z = GroundZAt(HeroMark, HeroMark.Z - HalfHeight) + HalfHeight + 2.f;
	}
	const FRotator Facing = HeroFacing.Rotation();
	Pawn->SetActorLocationAndRotation(Loc, Facing, false, nullptr, ETeleportType::TeleportPhysics);
	if (APlayerController* PC = PlayerPC.Get())
	{
		PC->SetControlRotation(Facing);
	}
	Pawn->SetActorHiddenInGame(false);
}

AActor* AJRIntroDirector::FindStoryTrigger() const
{
	if (FirstStoryTrigger)
	{
		return FirstStoryTrigger;
	}
	AActor* Best = nullptr;
	float BestDist = TNumericLimits<float>::Max();
	for (TActorIterator<AJRStoryTrigger> It(GetWorld()); It; ++It)
	{
		const float Dist = FVector::Dist(It->GetActorLocation(), CampPoint);
		if (Dist < BestDist)
		{
			BestDist = Dist;
			Best = *It;
		}
	}
	return BestDist < 15000.f ? Best : nullptr;
}

void AJRIntroDirector::FireStoryTrigger()
{
	// O primeiro gatilho (Historia_Z0_Queda) dispara na entrega do controle, com o mesmo código dele
	// (fala + rádio + tarefa "Pegue o graveto"), chamando o HandleOverlap pela reflexão. Ele marca bDone e não repete.
	if (bTriggerFired)
	{
		return;
	}
	bTriggerFired = true;
	AActor* Trigger = FindStoryTrigger();
	APawn* Pawn = PlayerPawn.Get();
	UFunction* Func = Trigger ? Trigger->FindFunction(TEXT("HandleOverlap")) : nullptr;
	if (!Func || !Pawn)
	{
		UE_LOG(LogJR, Warning, TEXT("Abertura: gatilho da primeira tarefa não encontrado (%s)."), *GetNameSafe(Trigger));
		return;
	}
	uint8* Params = static_cast<uint8*>(FMemory_Alloca_Aligned(Func->ParmsSize, Func->GetMinAlignment()));
	FMemory::Memzero(Params, Func->ParmsSize);
	for (TFieldIterator<FProperty> It(Func); It && It->HasAnyPropertyFlags(CPF_Parm); ++It)
	{
		It->InitializeValue_InContainer(Params);
		if (FObjectPropertyBase* ObjProp = CastField<FObjectPropertyBase>(*It))
		{
			const FName ParamName = ObjProp->GetFName();
			UObject* Value = nullptr;
			if (ParamName == TEXT("OverlappedComponent"))
			{
				Value = Trigger->GetRootComponent();
			}
			else if (ParamName == TEXT("OtherActor"))
			{
				Value = Pawn;
			}
			else if (ParamName == TEXT("OtherComp"))
			{
				Value = Pawn->GetRootComponent();
			}
			ObjProp->SetObjectPropertyValue_InContainer(Params, Value);
		}
	}
	Trigger->ProcessEvent(Func, Params);
	for (TFieldIterator<FProperty> It(Func); It && It->HasAnyPropertyFlags(CPF_Parm); ++It)
	{
		It->DestroyValue_InContainer(Params);
	}
}

// ====================================================================== som

void AJRIntroDirector::Play2D(FName Id, float Volume, float Pitch) const
{
	if (!Id.IsNone())
	{
		UJRAudio::Play2D(this, Id, Volume, Pitch);
	}
}

void AJRIntroDirector::PlayAt(FName Id, const FVector& Where, float Volume) const
{
	if (!Id.IsNone())
	{
		UJRAudio::PlayAt(this, Id, Where, Volume);
	}
}

void AJRIntroDirector::StopLoop(TObjectPtr<UAudioComponent>& Slot, float FadeOut)
{
	if (Slot)
	{
		Slot->FadeOut(FadeOut, 0.f);
		Slot = nullptr;
	}
}

// ====================================================================== quadro

void AJRIntroDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	RealTime += DeltaSeconds;
	PhaseTime += DeltaSeconds;
	if (!AcquirePlayer())
	{
		return; // o herói ainda não nasceu: a tela continua preta
	}
	if (!bMenuOpened)
	{
		bMenuOpened = true;
		OpenMenu();
	}
	if (RealTime >= NextFreezeScan && IsRunning())
	{
		FreezeEnemies(true);
		NextFreezeScan = RealTime + 0.5f;
	}

	Overlay.bVisible = IsRunning();
	switch (Phase)
	{
	case EJRIntroPhase::Menu:
		if (Mode == EMode::Full)
		{
			TickMenuCamera(RealTime);
			Overlay.Black = FMath::Max(0.f, 1.f - PhaseTime / 1.2f);
		}
		TickMenu(DeltaSeconds);
		break;
	case EJRIntroPhase::FadeToIntro:
		TickMenuCamera(RealTime);
		Overlay.Black = FMath::Clamp(PhaseTime / FadeSeconds, 0.f, 1.f);
		Overlay.Letterbox = Overlay.Black;
		UpdateSkip(DeltaSeconds);
		if (Phase == EJRIntroPhase::FadeToIntro && PhaseTime >= FadeSeconds)
		{
			SpawnFlightShip();
			if (FlightShip)
			{
				EngineLoop = UJRAudio::PlayAttached(this, EngineLoopId, FlightShip->GetRootComponent(), NAME_None, 0.8f);
			}
			WindLoop = UJRAudio::PlayAttached(this, WindLoopId, CineCamera, NAME_None, 0.6f);
			UJRAudio::PlayMusic(this, TensionMusicId, 1.5f);
			SetPhase(EJRIntroPhase::Cabin);
			TickCabin(0.f);
		}
		break;
	case EJRIntroPhase::Cabin:
		TickCabin(PhaseTime);
		UpdateSkip(DeltaSeconds);
		break;
	case EJRIntroPhase::LoseControl:
		TickLoseControl(PhaseTime);
		UpdateSkip(DeltaSeconds);
		break;
	case EJRIntroPhase::Impact:
		TickImpact(PhaseTime);
		UpdateSkip(DeltaSeconds);
		break;
	case EJRIntroPhase::Aftermath:
		TickAftermath(PhaseTime);
		UpdateSkip(DeltaSeconds);
		break;
	case EJRIntroPhase::Handoff:
		Overlay.Letterbox = 1.f - FMath::Clamp(PhaseTime / HandoffBlendSeconds, 0.f, 1.f);
		Overlay.bSkipHint = false;
		if (PhaseTime >= HandoffBlendSeconds)
		{
			Finish();
		}
		break;
	case EJRIntroPhase::SkipFade:
		if (!bSkipApplied)
		{
			const float Alpha = FMath::Clamp(PhaseTime / SkipFadeOut, 0.f, 1.f);
			Overlay.Black = FMath::Lerp(SkipBlackStart, 1.f, Alpha);
			if (Alpha >= 1.f)
			{
				// Tudo no estado final, escondido pela tela preta.
				bSkipApplied = true;
				DestroyFlightShip();
				StopLoop(EngineLoop, 0.1f);
				StopLoop(WindLoop, 0.2f);
				if (!bCrashShown)
				{
					ShowCrashSite(false);
				}
				StartFireLoop();
				ShowHero();
				if (APlayerController* PC = PlayerPC.Get())
				{
					PC->SetViewTarget(PlayerPawn.Get());
				}
				UJRAudio::PlayMusic(this, GameMusicId, 2.f);
				Overlay.Letterbox = 0.f;
				PhaseTime = 0.f;
			}
		}
		else
		{
			Overlay.Black = 1.f - FMath::Clamp(PhaseTime / SkipFadeIn, 0.f, 1.f);
			if (PhaseTime >= SkipFadeIn)
			{
				Finish();
			}
		}
		break;
	default:
		break;
	}
}

// ====================================================================== Ato 0: tela de start

void AJRIntroDirector::OpenMenu()
{
	MenuActions.Reset();
	Overlay.MenuItems.Reset();
	if (Mode == EMode::Full)
	{
		MenuActions.Add(EMenuAction::Play);
		Overlay.MenuItems.Add(TEXT("Jogar"));
		if (IsIntroSeen(this))
		{
			MenuActions.Add(EMenuAction::PlayFull);
			Overlay.MenuItems.Add(TEXT("Ver abertura"));
		}
	}
	else
	{
		MenuActions.Add(EMenuAction::Continue);
		Overlay.MenuItems.Add(TEXT("Continuar"));
	}
	MenuActions.Add(EMenuAction::Quit);
	Overlay.MenuItems.Add(TEXT("Sair"));
	MenuIndex = 0;
	Overlay.MenuIndex = 0;
	bMenuNeedsRelease = true;
	Overlay.bMenu = true;
	if (Mode == EMode::Full)
	{
		UJRAudio::PlayMusic(this, MenuMusicId, 1.5f);
	}
	// Sem o HUD da abertura (setup_intro.py não rodou / GameMode com outro HUD) o menu não aparece: começa direto.
	const APlayerController* PC = PlayerPC.Get();
	if (!PC || !Cast<AJRIntroHUD>(PC->GetHUD()))
	{
		UE_LOG(LogJR, Warning, TEXT("Abertura: o HUD não é AJRIntroHUD, sem tela de start (rode tools/unreal/setup_intro.py)."));
		RunMenuAction(MenuActions[0]);
	}
}

void AJRIntroDirector::TickMenuCamera(float T)
{
	// Câmera girando devagar bem alto sobre o vale (a nave ainda não caiu: está escondida).
	const float Radius = FMath::Max(ShipRadius * 9.f, 9000.f);
	const float Ang = FMath::DegreesToRadians(T * 3.f) + FMath::Atan2(ApproachDir.Y, ApproachDir.X);
	const FVector Around(FMath::Cos(Ang), FMath::Sin(Ang), 0.f);
	const FVector Tangent(-FMath::Sin(Ang), FMath::Cos(Ang), 0.f);
	const FVector Loc = MenuOrbitCenter + Around * Radius + FVector(0.f, 0.f, Radius * 0.3f);
	const FVector Look = Loc + Tangent * 10000.f + Around * 3000.f - FVector(0.f, 0.f, 1800.f);
	SetCamera(Loc, Look, 70.f, 0.f, 0.f);
}

void AJRIntroDirector::TickMenu(float DeltaSeconds)
{
	APlayerController* PC = PlayerPC.Get();
	if (!PC || MenuActions.Num() == 0)
	{
		return;
	}
	Overlay.bMenu = true;
	const std::initializer_list<FKey> ConfirmKeys = { EKeys::Enter, EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom, EKeys::LeftMouseButton };
	if (bMenuNeedsRelease)
	{
		// ignora a tecla que ainda estava apertada (ex.: o Enter da tela anterior)
		if (AnyKeyDown(PC, ConfirmKeys))
		{
			return;
		}
		bMenuNeedsRelease = false;
	}
	const int32 Count = MenuActions.Num();
	int32 Move = 0;
	if (AnyKeyPressed(PC, { EKeys::Up, EKeys::W, EKeys::Gamepad_DPad_Up, EKeys::Gamepad_LeftStick_Up }))
	{
		Move = -1;
	}
	else if (AnyKeyPressed(PC, { EKeys::Down, EKeys::S, EKeys::Gamepad_DPad_Down, EKeys::Gamepad_LeftStick_Down }))
	{
		Move = 1;
	}
	if (Move != 0)
	{
		MenuIndex = (MenuIndex + Move + Count) % Count;
		Play2D(MenuMoveSoundId, 0.6f);
	}

	// Mouse: passar por cima escolhe, clicar confirma.
	if (const AJRIntroHUD* Hud = Cast<AJRIntroHUD>(PC->GetHUD()))
	{
		float MouseX = 0.f;
		float MouseY = 0.f;
		if (PC->GetMousePosition(MouseX, MouseY))
		{
			const FVector2D Mouse(MouseX, MouseY);
			const int32 Hit = Hud->HitTestMenu(Mouse);
			const bool bMoved = !Mouse.Equals(LastMouse, 0.5f);
			LastMouse = Mouse;
			if (Hit != INDEX_NONE && Hit < Count)
			{
				if (bMoved && Hit != MenuIndex)
				{
					MenuIndex = Hit;
					Play2D(MenuMoveSoundId, 0.6f);
				}
				if (PC->WasInputKeyJustPressed(EKeys::LeftMouseButton))
				{
					MenuIndex = Hit;
					Overlay.MenuIndex = MenuIndex;
					RunMenuAction(MenuActions[Hit]);
					return;
				}
			}
		}
	}
	Overlay.MenuIndex = MenuIndex;
	if (AnyKeyPressed(PC, { EKeys::Enter, EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom }))
	{
		RunMenuAction(MenuActions[MenuIndex]);
	}
}

void AJRIntroDirector::RunMenuAction(EMenuAction Action)
{
	Play2D(MenuSelectSoundId, 0.8f);
	Overlay.bMenu = false;
	switch (Action)
	{
	case EMenuAction::Play:
		if (IsIntroSeen(this))
		{
			StartSkip(); // já viu: "Jogar" vai direto ao fim da abertura
		}
		else
		{
			StartCinematic();
		}
		break;
	case EMenuAction::PlayFull:
		StartCinematic();
		break;
	case EMenuAction::Continue:
		Finish();
		break;
	case EMenuAction::Quit:
		UKismetSystemLibrary::QuitGame(this, PlayerPC.Get(), EQuitPreference::Quit, false);
		break;
	}
}

void AJRIntroDirector::StartCinematic()
{
	if (APlayerController* PC = PlayerPC.Get())
	{
		PC->bShowMouseCursor = false;
	}
	UJRAudio::PlayMusic(this, NAME_None, FadeSeconds);
	bSkipArmed = false;
	SkipHold = 0.f;
	SetPhase(EJRIntroPhase::FadeToIntro);
}

void AJRIntroDirector::StartSkip()
{
	if (Phase == EJRIntroPhase::SkipFade || Phase == EJRIntroPhase::Done)
	{
		return;
	}
	SkipBlackStart = Overlay.Black;
	SkipLetterboxStart = Overlay.Letterbox;
	Overlay.bSkipHint = false;
	Overlay.SkipProgress = 0.f;
	Overlay.bMenu = false;
	bSkipApplied = false;
	if (APlayerController* PC = PlayerPC.Get())
	{
		PC->bShowMouseCursor = false;
	}
	SetPhase(EJRIntroPhase::SkipFade);
}

void AJRIntroDirector::UpdateSkip(float DeltaSeconds)
{
	const APlayerController* PC = PlayerPC.Get();
	if (!PC)
	{
		return;
	}
	const bool bHeld = AnyKeyDown(PC, { EKeys::SpaceBar, EKeys::Enter, EKeys::Gamepad_FaceButton_Bottom, EKeys::Gamepad_Special_Right });
	if (!bSkipArmed)
	{
		bSkipArmed = !bHeld; // precisa soltar a tecla do "Jogar" antes de valer para pular
		SkipHold = 0.f;
	}
	else if (bHeld)
	{
		SkipHold += DeltaSeconds;
	}
	else
	{
		SkipHold = FMath::Max(0.f, SkipHold - DeltaSeconds * 2.f);
	}
	Overlay.bSkipHint = true;
	Overlay.SkipProgress = FMath::Clamp(SkipHold / SkipHoldSeconds, 0.f, 1.f);
	if (SkipHold >= SkipHoldSeconds)
	{
		StartSkip();
	}
}

// ====================================================================== Ato 1: cabine

void AJRIntroDirector::TickCabin(float T)
{
	const FVector Up = FVector::UpVector;
	const FVector ShipPos = PathPosition(T);
	const FVector Fwd = ShipForward(T);
	const FVector Right = FVector::CrossProduct(Up, Fwd).GetSafeNormal();
	if (FlightShip)
	{
		FlightShip->SetActorLocationAndRotation(ShipPos, ShipRotation(T));
	}
	// Alarme: luz vermelha pulsando e bipe.
	const float Pulse = 0.5f + 0.5f * FMath::Sin(RealTime * 9.f);
	AlarmLight->SetWorldLocation(ShipPos + Fwd * ShipRadius * 0.5f + Up * ShipRadius * 0.35f);
	AlarmLight->SetIntensity(AlarmLightCandelas * Pulse);
	if (T >= NextAlarm)
	{
		Play2D(AlarmSoundId, 0.7f, 0.85f);
		NextAlarm = T + 0.9f;
	}
	if (EngineLoop)
	{
		EngineLoop->SetPitchMultiplier(1.1f);
	}
	// Plano médio perto da cabine (frente-direita da nave), olhando para o nariz.
	const FVector CamLoc = ShipPos + Fwd * ShipRadius * 1.25f + Right * (ShipRadius * 0.55f + T * 25.f) + Up * ShipRadius * 0.3f;
	const FVector Look = ShipPos + Fwd * ShipRadius * 0.35f + Up * ShipRadius * 0.15f;
	SetCamera(CamLoc, Look, 55.f, 0.6f + T * 0.08f, 4.f);

	Overlay.Black = 1.f - FMath::Clamp(T / FadeSeconds, 0.f, 1.f);
	Overlay.Letterbox = 1.f;
	const float A1 = Window(T, 0.8f, 3.8f);
	const float A2 = Window(T, 4.0f, CabinSeconds - 0.2f);
	Overlay.Subtitle = A1 > 0.f ? TEXT("ALERTA: falha no motor principal!") : (A2 > 0.f ? TEXT("Perdendo altitude... segurem firme!") : TEXT(""));
	Overlay.SubtitleAlpha = FMath::Max(A1, A2);
	if (T >= CabinSeconds)
	{
		SetPhase(EJRIntroPhase::LoseControl);
	}
}

// ====================================================================== Ato 2: perda de controle

void AJRIntroDirector::TickLoseControl(float T)
{
	const FVector Up = FVector::UpVector;
	const float PathT = CabinSeconds + T;
	const float U = FMath::Clamp(T / LoseControlSeconds, 0.f, 1.f);
	const FVector ShipPos = PathPosition(PathT);
	const FVector Fwd = ShipForward(PathT);
	const FVector Right = FVector::CrossProduct(Up, Fwd).GetSafeNormal();
	const FVector Rear = ShipPos - Fwd * ShipRadius * 0.8f;
	if (FlightShip)
	{
		FlightShip->SetActorLocationAndRotation(ShipPos, ShipRotation(PathT));
	}
	UJRFXSubsystem* FX = UJRFXSubsystem::Get(this);
	if (!bEngineBang)
	{
		bEngineBang = true;
		PlayAt(EngineBangId, Rear, 0.6f);
		if (FX)
		{
			FX->SpawnFlash(Rear, FireOrange, 25.f, ShipRadius * 0.1f, ShipRadius * 0.7f, 0.5f, 30000.f, ShipRadius * 4.f);
		}
		if (SmokeFX)
		{
			SmokeFX->Activate(true);
		}
	}
	if (FX && T >= NextSpark)
	{
		NextSpark = T + 0.12f;
		const FVector Jitter = FMath::VRand() * ShipRadius * 0.15f;
		FX->SpawnPlasmaImpact(Rear + Jitter, -Fwd, FireOrange, 2.f, 1.2f + 2.f * U, false);
	}
	const float Pulse = 0.5f + 0.5f * FMath::Sin(RealTime * 16.f);
	AlarmLight->SetWorldLocation(ShipPos + Fwd * ShipRadius * 0.5f + Up * ShipRadius * 0.35f);
	AlarmLight->SetIntensity(AlarmLightCandelas * Pulse);
	if (T >= NextAlarm)
	{
		Play2D(AlarmSoundId, 0.8f, 1.05f);
		NextAlarm = T + 0.45f;
	}
	if (EngineLoop)
	{
		// motor engasgando: tom caindo e volume falhando
		EngineLoop->SetPitchMultiplier(FMath::Lerp(1.1f, 0.55f, U));
		EngineLoop->SetVolumeMultiplier(0.8f * (0.55f + 0.45f * FMath::Abs(FMath::Sin(RealTime * 11.f))));
	}

	const float ChaseStart = LoseControlSeconds - FMath::Min(3.5f, LoseControlSeconds * 0.4f);
	if (T < ChaseStart)
	{
		// Plano do chão, no acampamento: teleobjetiva seguindo a nave que cai.
		FVector Cam = CampPoint;
		Cam.Z = GroundZAt(CampPoint, CampPoint.Z) + 220.f;
		SetCamera(Cam, ShipPos, FMath::Lerp(28.f, 50.f, T / ChaseStart), 0.25f, 1.f);
	}
	else
	{
		// Perseguição atrás da nave, tremendo forte até o chão.
		const float K2 = FMath::Clamp((T - ChaseStart) / (LoseControlSeconds - ChaseStart), 0.f, 1.f);
		FVector Cam = ShipPos - Fwd * ShipRadius * 2.6f + Up * ShipRadius * (0.9f - 0.4f * K2) + Right * ShipRadius * 0.4f;
		Cam.Z = FMath::Max<double>(Cam.Z, GroundZAt(Cam, Cam.Z - 1000.f) + 180.f);
		SetCamera(Cam, ShipPos + Fwd * ShipRadius * 1.5f, FMath::Lerp(70.f, 88.f, K2), 1.2f + 2.f * K2, 6.f + 14.f * K2);
	}
	Overlay.Letterbox = 1.f;
	Overlay.Black = 0.f;
	Overlay.SubtitleAlpha = Window(T, 0.3f, 2.6f);
	Overlay.Subtitle = Overlay.SubtitleAlpha > 0.f ? TEXT("PERDA DE CONTROLE") : TEXT("");
	if (T >= LoseControlSeconds)
	{
		SetPhase(EJRIntroPhase::Impact);
		TickImpact(0.f);
	}
}

// ====================================================================== Ato 3: impacto

void AJRIntroDirector::TickImpact(float T)
{
	const FVector Up = FVector::UpVector;
	if (!bImpactSoundsDone)
	{
		bImpactSoundsDone = true;
		DestroyFlightShip();
		ShowCrashSite(true);
		for (const FName& Id : ImpactSoundIds)
		{
			PlayAt(Id, CrashPoint, 1.f);
		}
		UJRAudio::PlayMusic(this, NAME_None, 0.1f);
		StopLoop(EngineLoop, 0.05f);
		StopLoop(WindLoop, 0.3f);
	}
	if (T >= 1.3f)
	{
		StartFireLoop(); // ~1 s de silêncio depois do estrondo
	}
	// Corte seco: plano aberto da queda, do lado do herói.
	const FVector Side = FVector::CrossProduct(Up, ImpactCamDir).GetSafeNormal();
	const float Dist = FMath::Max(ShipRadius * 3.2f, 2500.f);
	FVector Cam = CrashPoint + ImpactCamDir * Dist + Side * ShipRadius * 0.8f + Up * (ShipRadius * 0.5f + 250.f);
	Cam.Z = FMath::Max<double>(Cam.Z, GroundZAt(Cam, Cam.Z - 1000.f) + 200.f);
	const float Decay = FMath::Exp(-2.5f * T);
	SetCamera(Cam, CrashPoint + Up * ShipRadius * 0.15f, 62.f, 3.5f * Decay, 25.f * Decay);
	Overlay.White = 0.9f * (1.f - FMath::Clamp(T / 0.35f, 0.f, 1.f));
	Overlay.Black = 0.f;
	Overlay.Letterbox = 1.f;
	if (T >= ImpactSeconds)
	{
		Overlay.White = 0.f;
		SetPhase(EJRIntroPhase::Aftermath);
		TickAftermath(0.f);
	}
}

// ====================================================================== Ato 4: pós-queda e herói

void AJRIntroDirector::TickAftermath(float T)
{
	const FVector Up = FVector::UpVector;
	const float Split = AftermathSeconds * 0.5f;
	Overlay.Letterbox = 1.f;
	Overlay.White = 0.f;
	if (T < Split)
	{
		// Plano aberto girando devagar em volta da nave pegando fogo.
		const float Ang0 = FMath::Atan2(ImpactCamDir.Y, ImpactCamDir.X);
		const float Ang = Ang0 + FMath::DegreesToRadians(28.f) * FMath::SmoothStep(0.f, 1.f, T / Split);
		const float Dist = FMath::Max(ShipRadius * 3.f, 2600.f);
		FVector Cam = CrashPoint + FVector(FMath::Cos(Ang), FMath::Sin(Ang), 0.f) * Dist + Up * (ShipRadius * 0.35f + 180.f);
		Cam.Z = FMath::Max<double>(Cam.Z, GroundZAt(Cam, Cam.Z - 1000.f) + 200.f);
		SetCamera(Cam, CrashPoint + Up * ShipRadius * 0.2f, 55.f, 0.15f, 0.f);
		return;
	}
	// Corte para o herói em pé ao lado da nave.
	ShowHero();
	APawn* Pawn = PlayerPawn.Get();
	const float T2 = T - Split;
	const float Len2 = AftermathSeconds - Split;
	const float StepStart = Len2 * 0.33f;
	if (Pawn && T2 >= StepStart && T2 < StepStart + 1.1f)
	{
		Pawn->AddMovementInput(HeroFacing, 0.4f, true); // os primeiros passos (força mesmo com o controle travado)
	}
	const FVector Pivot = HeroPivot();
	const FVector Right = FVector::CrossProduct(Up, HeroFacing).GetSafeNormal();
	const FVector FrontLoc = Pivot + HeroFacing * 380.f + Right * 110.f + Up * 15.f;
	const FQuat FrontQuat = (Pivot + Up * 10.f - FrontLoc).Rotation().Quaternion();
	const float Swing = FMath::SmoothStep(Len2 * 0.55f, Len2, T2);
	if (Swing <= 0.f)
	{
		SetCameraRot(FrontLoc, FrontQuat, 50.f, 0.12f, 0.f);
	}
	else
	{
		// A câmera dá a volta até a posição da câmera do jogo (atrás do herói): o blend final fica curto.
		const UCameraComponent* HeroCam = Pawn ? Pawn->FindComponentByClass<UCameraComponent>() : nullptr;
		const FVector TargetLoc = HeroCam ? HeroCam->GetComponentLocation() : Pivot - HeroFacing * 350.f + Up * 80.f;
		const FQuat TargetQuat = HeroCam ? HeroCam->GetComponentQuat() : HeroFacing.Rotation().Quaternion();
		const float TargetFov = HeroCam ? HeroCam->FieldOfView : 75.f;
		const FVector VA = FrontLoc - Pivot;
		const FVector VB = TargetLoc - Pivot;
		const float YawA = FMath::Atan2(VA.Y, VA.X);
		const float YawB = FMath::Atan2(VB.Y, VB.X);
		const float Yaw = YawA + FMath::FindDeltaAngleRadians(YawA, YawB) * Swing;
		const float Dist = FMath::Lerp(VA.Size2D(), VB.Size2D(), Swing);
		const float Height = FMath::Lerp(VA.Z, VB.Z, Swing);
		const FVector Loc = Pivot + FVector(FMath::Cos(Yaw) * Dist, FMath::Sin(Yaw) * Dist, Height);
		const FQuat LookQuat = (Pivot + Up * 10.f - Loc).Rotation().Quaternion();
		const FQuat Rot = FQuat::Slerp(LookQuat, TargetQuat, Swing * Swing);
		SetCameraRot(Loc, Rot, FMath::Lerp(50.f, TargetFov, Swing), 0.f, 0.f);
	}
	if (T >= AftermathSeconds && !bHandoffStarted)
	{
		bHandoffStarted = true;
		SetPhase(EJRIntroPhase::Handoff);
		Overlay.bSkipHint = false;
		if (APlayerController* PC = PlayerPC.Get())
		{
			PC->SetViewTargetWithBlend(Pawn, HandoffBlendSeconds, VTBlend_EaseInOut, 2.f, false);
		}
		UJRAudio::PlayMusic(this, GameMusicId, 3.f);
	}
}

// ====================================================================== Ato 5: entrega do controle

void AJRIntroDirector::Finish()
{
	if (Phase == EJRIntroPhase::Done)
	{
		return;
	}
	const bool bWasFull = Mode == EMode::Full;
	if (bWasFull)
	{
		// O mesmo estado final, tenha a abertura rodado inteira ou não.
		DestroyFlightShip();
		if (!bCrashShown)
		{
			ShowCrashSite(false);
		}
		StartFireLoop();
		ShowHero();
		APlayerController* PC = PlayerPC.Get();
		if (PC && PC->GetViewTarget() == this)
		{
			PC->SetViewTarget(PlayerPawn.Get());
		}
	}
	StopLoop(EngineLoop, 0.2f);
	StopLoop(WindLoop, 0.5f);
	FreezeEnemies(false);
	UnlockPlayer();
	if (bWasFull)
	{
		FireStoryTrigger();
		SetIntroSeen(this, true);
		UJRAudio::PlayMusic(this, GameMusicId, 3.f);
	}
	Overlay = FJRIntroOverlay();
	SetPhase(EJRIntroPhase::Done);
	SetActorTickEnabled(false);
	UE_LOG(LogJR, Log, TEXT("Abertura: controle entregue ao jogador (%s)."), *GetNameSafe(PlayerPawn.Get()));
}

// Copyright utrazin. All Rights Reserved.

#include "AI/JRAIDirector.h"
#include "AI/JREnemyBudgetSubsystem.h"
#include "AI/JREnemyCharacter.h"
#include "Camera/PlayerCameraManager.h"
#include "Combat/JRHealthComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehiclePawn.h"

namespace
{
	TAutoConsoleVariable<int32> CVarJRDirectorDebug(
		TEXT("jr.Director.Debug"), 0,
		TEXT("Mostra na tela a fase, a intensidade e os vivos do diretor de IA (0 = desligado, 1 = ligado)."),
		ECVF_Default);

	constexpr uint64 DirectorDebugKey = 0x4A52444952ull; // "JRDIR"

	const TCHAR* PhaseName(EJRDirectorPhase InPhase)
	{
		switch (InPhase)
		{
		case EJRDirectorPhase::BuildUp: return TEXT("Subida");
		case EJRDirectorPhase::Peak: return TEXT("Pico");
		case EJRDirectorPhase::Relax: return TEXT("Calmaria");
		}
		return TEXT("?");
	}
}

// ============================================================ AJRDirectorZone

AJRDirectorZone::AJRDirectorZone()
{
	PrimaryActorTick.bCanEverTick = false;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	RootComponent = Box;
	Box->InitBoxExtent(FVector(2000.f, 2000.f, 1000.f));
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Box->SetGenerateOverlapEvents(false);
	Box->SetCanEverAffectNavigation(false);
	Box->SetHiddenInGame(true);
	Box->ShapeColor = FColor(80, 220, 120);
}

bool AJRDirectorZone::ContainsPoint(const FVector& Point) const
{
	if (!Box)
	{
		return false;
	}
	// Para o espaço local da caixa: a transformação inversa já desfaz rotação e escala.
	const FVector Local = Box->GetComponentTransform().InverseTransformPosition(Point);
	const FVector Extent = Box->GetUnscaledBoxExtent();
	return FMath::Abs(Local.X) <= Extent.X && FMath::Abs(Local.Y) <= Extent.Y && FMath::Abs(Local.Z) <= Extent.Z;
}

// ============================================================ AJRAIDirector

AJRAIDirector::AJRAIDirector()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

AJRAIDirector* AJRAIDirector::Find(const UObject* WorldContext)
{
	UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World)
	{
		return nullptr;
	}
	TActorIterator<AJRAIDirector> It(World);
	return It ? *It : nullptr;
}

bool AJRAIDirector::IsDebugEnabled()
{
	return CVarJRDirectorDebug.GetValueOnGameThread() != 0;
}

void AJRAIDirector::SetDebugEnabled(bool bDebug)
{
	CVarJRDirectorDebug->Set(bDebug ? 1 : 0);
}

void AJRAIDirector::BeginPlay()
{
	Super::BeginPlay();
	Random.GenerateNewSeed();
	const double Now = GetWorld()->GetTimeSeconds();
	LastUpdateTime = Now;
	LastRecycleTime = Now;
	PhaseStartTime = Now;
	NextSpawnTime = Now + Settings.FirstSpawnDelay;
	if (BuildUpTable.Num() == 0 && PeakTable.Num() == 0 && EnemyTable.Num() == 0)
	{
		UE_LOG(LogJR, Warning, TEXT("%s: tabelas de inimigos vazias; o diretor não vai criar zumbis (rode tools/unreal/setup_ai_director.py)."), *GetName());
	}
	GetWorldTimerManager().SetTimer(UpdateTimer, this, &AJRAIDirector::UpdateDirector, FMath::Max(UpdateInterval, 0.1f), true);
}

void AJRAIDirector::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(UpdateTimer);
	BindPlayerPawn(nullptr);
	Super::EndPlay(EndPlayReason);
}

bool AJRAIDirector::IsActiveNow() const
{
	if (!bEnabled || !GetWorld())
	{
		return false;
	}
	if (GetWorld()->GetTimeSeconds() < EventActiveUntil)
	{
		return true; // horda de evento: trabalha mesmo fora dos estágios
	}
	const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>();
	if (!Objective || Objective->GetStage() == EJRLevelStage::NotStarted)
	{
		return bActiveWithoutObjective;
	}
	return ActiveStages.Contains(Objective->GetStage());
}

void AJRAIDirector::AddIntensity(float Amount)
{
	Intensity = FMath::Clamp(Intensity + Amount, 0.f, 1.f);
}

void AJRAIDirector::NotifyEnemyKilled(AJREnemyCharacter* Enemy)
{
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (Enemy && Player && FVector::Dist(Enemy->GetActorLocation(), Player->GetActorLocation()) <= Settings.KillNearRadius)
	{
		AddIntensity(Settings.KillIntensity);
	}
}

void AJRAIDirector::TriggerHorde(FName Reason, float Duration, int32 Size)
{
	TriggerHordeAt(Reason, FVector::ZeroVector, Duration, Size);
}

void AJRAIDirector::TriggerHordeAt(FName Reason, FVector Location, float Duration, int32 Size)
{
	if (!bEnabled)
	{
		UE_LOG(LogJR, Log, TEXT("Diretor: horda '%s' ignorada (diretor desligado)"), *Reason.ToString());
		return;
	}
	if (const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0))
	{
		const AJRDirectorZone* Zone = FindZoneAt(Player->GetActorLocation());
		if (Zone && Zone->bNoSpawns && Zone->bBlockEventHordes)
		{
			UE_LOG(LogJR, Log, TEXT("Diretor: horda '%s' bloqueada pela zona segura %s"), *Reason.ToString(), *Zone->GetActorNameOrLabel());
			return;
		}
	}
	const float Length = Duration > 0.f ? Duration : Settings.PeakDuration;
	EventActiveUntil = GetWorld()->GetTimeSeconds() + Length;
	bWasActive = true; // não deixa a "entrada no estágio" trocar o Pico por Subida
	StartPeak(Reason.IsNone() ? FName(TEXT("Evento")) : Reason, Location, Length, Size);
}

void AJRAIDirector::ForcePhase(EJRDirectorPhase NewPhase)
{
	switch (NewPhase)
	{
	case EJRDirectorPhase::Peak:
		TriggerHorde(TEXT("Console"), Settings.PeakDuration, 0);
		break;
	case EJRDirectorPhase::Relax:
		SetPhase(EJRDirectorPhase::Relax, Random.FRandRange(Settings.RelaxMinTime, FMath::Max(Settings.RelaxMinTime, Settings.RelaxMaxTime)));
		break;
	case EJRDirectorPhase::BuildUp:
		SetPhase(EJRDirectorPhase::BuildUp);
		break;
	}
}

void AJRAIDirector::StartPeak(FName Reason, const FVector& Location, float Duration, int32 Size)
{
	SetPhase(EJRDirectorPhase::Peak, Duration);
	bHasHordeFocus = !Location.IsNearlyZero();
	HordeFocus = Location;
	HordeRemaining = Size > 0 ? Size : -1;
	HordeReason = Reason;
	if (bShowHordeToast)
	{
		AJRHUD::Toast(this, TEXT("Horda chegando!"), FLinearColor(1.f, 0.25f, 0.15f));
	}
	const FString SizeText = Size > 0 ? FString::Printf(TEXT("%d zumbis"), Size) : FString(TEXT("sem limite"));
	UE_LOG(LogJR, Log, TEXT("Diretor: horda '%s' (%.0f s, %s)"), *Reason.ToString(), Duration, *SizeText);
	OnHordeTriggered.Broadcast(Reason, Size);
}

void AJRAIDirector::SetPhase(EJRDirectorPhase NewPhase, float Duration)
{
	const double Now = GetWorld()->GetTimeSeconds();
	const EJRDirectorPhase OldPhase = Phase;
	Phase = NewPhase;
	PhaseStartTime = Now;
	PhaseEndTime = Now + FMath::Max(Duration, 0.f);
	bHasHordeFocus = false;
	HordeRemaining = -1;
	switch (NewPhase)
	{
	case EJRDirectorPhase::Peak:
		NextSpawnTime = Now; // a horda começa já
		break;
	case EJRDirectorPhase::Relax:
		HordeReason = NAME_None;
		break;
	case EJRDirectorPhase::BuildUp:
		HordeReason = NAME_None;
		NextSpawnTime = Now + Settings.FirstSpawnDelay;
		break;
	}
	UE_LOG(LogJR, Log, TEXT("Diretor: %s -> %s (intensidade %.2f, %.0f s)"), PhaseName(OldPhase), PhaseName(NewPhase), Intensity, Duration);
	if (OldPhase != NewPhase)
	{
		OnDirectorPhaseChanged.Broadcast(OldPhase, NewPhase);
		ReceivePhaseChanged(OldPhase, NewPhase);
	}
}

void AJRAIDirector::ScheduleNextSpawn()
{
	const float Scale = bPlayerDriving ? Settings.DrivingIntervalScale : 1.f;
	const float MinI = Settings.BuildUpMinInterval * Scale;
	const float MaxI = FMath::Max(MinI, Settings.BuildUpMaxInterval * Scale);
	NextSpawnTime = GetWorld()->GetTimeSeconds() + Random.FRandRange(MinI, MaxI);
}

void AJRAIDirector::UpdateDirector()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	const float Dt = static_cast<float>(FMath::Clamp(Now - LastUpdateTime, 0.0, 2.0));
	LastUpdateTime = Now;
	if (Find(this) != this)
	{
		// Dois diretores no mapa dobrariam os spawns: só o primeiro trabalha.
		UE_LOG(LogJR, Warning, TEXT("%s: já existe outro AJRAIDirector no mapa; este fica desligado."), *GetName());
		GetWorldTimerManager().ClearTimer(UpdateTimer);
		return;
	}

	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (Player != BoundPawn.Get())
	{
		BindPlayerPawn(Player);
	}
	Spawned.RemoveAll([](const TWeakObjectPtr<AJREnemyCharacter>& Weak) { return !Weak.IsValid() || Weak->IsDead(); });

	const bool bActive = Player != nullptr && IsActiveNow();
	if (bActive != bWasActive)
	{
		bWasActive = bActive;
		if (bActive)
		{
			// Entrou num estágio ativo: começa da Subida com um respiro antes do primeiro grupo.
			SetPhase(EJRDirectorPhase::BuildUp);
		}
	}
	if (!bActive)
	{
		DrawDebug();
		return;
	}

	bPlayerDriving = Player->IsA<AJRVehiclePawn>();
	const AJRDirectorZone* Zone = FindZoneAt(Player->GetActorLocation());
	CurrentZoneName = Zone ? Zone->GetActorNameOrLabel() : FString();
	UpdateIntensity(Player, Dt, Zone);

	switch (Phase)
	{
	case EJRDirectorPhase::BuildUp:
	{
		const double InPhase = Now - PhaseStartTime;
		if (Intensity >= Settings.RelaxTriggerIntensity)
		{
			// Jogador já sobrecarregado (ex.: grupo colocado à mão): respiro antes de mandar mais.
			SetPhase(EJRDirectorPhase::Relax, Random.FRandRange(Settings.RelaxMinTime, FMath::Max(Settings.RelaxMinTime, Settings.RelaxMaxTime)));
		}
		else if ((InPhase >= Settings.MinBuildUpTime && Intensity >= Settings.PeakTriggerIntensity) || InPhase >= Settings.MaxBuildUpTime)
		{
			StartPeak(TEXT("Ritmo"), FVector::ZeroVector, Settings.PeakDuration, 0);
		}
		else if (Now >= NextSpawnTime)
		{
			const int32 Count = Random.RandRange(Settings.BuildUpMinGroup, FMath::Max(Settings.BuildUpMinGroup, Settings.BuildUpMaxGroup));
			if (SpawnGroup(Player, Count, Zone) < 0)
			{
				NextSpawnTime = Now + Settings.RetryDelay;
			}
			else
			{
				ScheduleNextSpawn();
			}
		}
		break;
	}
	case EJRDirectorPhase::Peak:
	{
		const bool bHordeSpent = HordeRemaining == 0 && Spawned.Num() == 0;
		const bool bOverwhelmed = Now - PhaseStartTime >= Settings.PeakMinDuration && Intensity >= Settings.RelaxTriggerIntensity;
		if (Now >= PhaseEndTime || bHordeSpent || bOverwhelmed)
		{
			SetPhase(EJRDirectorPhase::Relax, Random.FRandRange(Settings.RelaxMinTime, FMath::Max(Settings.RelaxMinTime, Settings.RelaxMaxTime)));
		}
		else if (Now >= NextSpawnTime && HordeRemaining != 0)
		{
			const int32 Count = Random.RandRange(Settings.PeakMinGroup, FMath::Max(Settings.PeakMinGroup, Settings.PeakMaxGroup));
			if (SpawnGroup(Player, Count, Zone) < 0)
			{
				NextSpawnTime = Now + FMath::Min(Settings.RetryDelay, 1.5f);
			}
			else
			{
				NextSpawnTime = Now + Random.FRandRange(Settings.PeakMinInterval, FMath::Max(Settings.PeakMinInterval, Settings.PeakMaxInterval));
			}
		}
		break;
	}
	case EJRDirectorPhase::Relax:
		if (Now >= PhaseEndTime)
		{
			SetPhase(EJRDirectorPhase::BuildUp);
			ScheduleNextSpawn();
		}
		break;
	}

	if (Now - LastRecycleTime >= 2.0)
	{
		LastRecycleTime = Now;
		RecycleFarEnemies(Player);
	}
	DrawDebug();
}

void AJRAIDirector::UpdateIntensity(const APawn* Player, float DeltaSeconds, const AJRDirectorZone* Zone)
{
	const FVector PlayerLocation = Player->GetActorLocation();
	const double NearSq = FMath::Square(static_cast<double>(Settings.NearbyRadius));
	const double CombatSq = FMath::Square(static_cast<double>(Settings.CombatRadius));
	int32 Near = 0;
	bool bInCombat = false;
	for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
	{
		const AJREnemyCharacter* Enemy = *It;
		if (!Enemy || Enemy->IsDead())
		{
			continue;
		}
		const double DistSq = FVector::DistSquared(Enemy->GetActorLocation(), PlayerLocation);
		if (DistSq <= NearSq)
		{
			++Near;
		}
		if (!bInCombat && DistSq <= CombatSq)
		{
			const EJREnemyState State = Enemy->GetEnemyState();
			bInCombat = State == EJREnemyState::Chase || State == EJREnemyState::Attack || Enemy->IsGrabbingVehicle();
		}
	}
	NearbyCount = Near;

	float Delta = 0.f;
	if (Near > 0)
	{
		Delta += static_cast<float>(FMath::Min(Near, Settings.NearbyMaxCount)) * Settings.NearbyIntensityPerSecond * DeltaSeconds;
	}
	if (bInCombat)
	{
		CombatTime += DeltaSeconds;
		Delta += Settings.CombatIntensityPerSecond * DeltaSeconds;
	}
	else
	{
		CombatTime = 0.f;
	}
	if (!bInCombat && Near == 0)
	{
		const float Decay = Phase == EJRDirectorPhase::Relax ? Settings.RelaxDecayPerSecond : Settings.DecayPerSecond;
		Delta -= Decay * (Zone ? Zone->IntensityDecayMultiplier : 1.f) * DeltaSeconds;
	}
	AddIntensity(Delta);
}

const AJRDirectorZone* AJRAIDirector::FindZoneAt(const FVector& Point) const
{
	const AJRDirectorZone* Best = nullptr;
	for (TActorIterator<AJRDirectorZone> It(GetWorld()); It; ++It)
	{
		const AJRDirectorZone* Candidate = *It;
		if (Candidate && Candidate->ContainsPoint(Point) && (!Best || Candidate->Priority > Best->Priority))
		{
			Best = Candidate;
		}
	}
	return Best;
}

bool AJRAIDirector::IsInNoSpawnZone(const FVector& Point) const
{
	for (TActorIterator<AJRDirectorZone> It(GetWorld()); It; ++It)
	{
		if (It->bNoSpawns && It->ContainsPoint(Point))
		{
			return true;
		}
	}
	return false;
}

int32 AJRAIDirector::CountSpawnedOfClass(const UClass* Cls) const
{
	int32 Count = 0;
	for (const TWeakObjectPtr<AJREnemyCharacter>& Weak : Spawned)
	{
		Count += (Weak.IsValid() && Weak->GetClass() == Cls) ? 1 : 0;
	}
	return Count;
}

TSubclassOf<AJREnemyCharacter> AJRAIDirector::PickEnemyClass(const AJRDirectorZone* Zone)
{
	const TArray<FJRDirectorEnemyEntry>* PhaseTable = Phase == EJRDirectorPhase::Peak ? &PeakTable : &BuildUpTable;
	const TArray<FJRDirectorEnemyEntry>& Table = PhaseTable->Num() > 0 ? *PhaseTable : EnemyTable;
	const bool bFilterByZone = Zone && Zone->AllowedClasses.Num() > 0;

	// Só entra no sorteio quem tem classe, peso, é permitido pela zona e não passou do MaxAlive.
	TArray<const FJRDirectorEnemyEntry*, TInlineAllocator<8>> Valid;
	float Total = 0.f;
	for (const FJRDirectorEnemyEntry& Entry : Table)
	{
		if (!Entry.EnemyClass || Entry.Weight <= 0.f)
		{
			continue;
		}
		if (bFilterByZone && !Zone->AllowedClasses.Contains(Entry.EnemyClass))
		{
			continue;
		}
		if (Entry.MaxAlive > 0 && CountSpawnedOfClass(Entry.EnemyClass.Get()) >= Entry.MaxAlive)
		{
			continue;
		}
		Valid.Add(&Entry);
		Total += Entry.Weight;
	}
	if (Valid.Num() == 0 || Total <= 0.f)
	{
		return nullptr;
	}
	float Roll = Random.FRandRange(0.f, Total);
	for (const FJRDirectorEnemyEntry* Entry : Valid)
	{
		Roll -= Entry->Weight;
		if (Roll <= 0.f)
		{
			return Entry->EnemyClass;
		}
	}
	return Valid.Last()->EnemyClass;
}

int32 AJRAIDirector::SpawnGroup(const APawn* Player, int32 Count, const AJRDirectorZone* Zone)
{
	if (Zone && Zone->bNoSpawns)
	{
		return 0; // jogador na zona segura: nada de grupos
	}
	const float Density = Zone ? Zone->DensityMultiplier : 1.f;
	if (Density <= 0.f)
	{
		return 0;
	}
	const bool bPeak = Phase == EJRDirectorPhase::Peak;
	const int32 Cap = FMath::RoundToInt(static_cast<float>(bPeak ? Settings.MaxAlivePeak : Settings.MaxAliveBuildUp) * Density);
	const UJREnemyBudgetSubsystem* Budget = GetWorld()->GetSubsystem<UJREnemyBudgetSubsystem>();
	const int32 AliveInMap = Budget ? Budget->GetAliveEnemyCount() : Spawned.Num();
	int32 Want = FMath::Max(1, FMath::RoundToInt(static_cast<float>(Count) * Density));
	Want = FMath::Min(Want, Cap - AliveInMap);
	if (HordeRemaining >= 0)
	{
		Want = FMath::Min(Want, HordeRemaining);
	}
	if (Want <= 0)
	{
		return 0; // teto atingido
	}

	const FJRDirectorViewInfo View = GetViewInfo(Player);
	FVector Point;
	if (!FindSpawnPoint(Player, bPeak && bHasHordeFocus, View, Point))
	{
		UE_LOG(LogJR, Verbose, TEXT("Diretor: nenhum ponto de spawn válido agora"));
		return -1;
	}

	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	int32 Made = 0;
	for (int32 i = 0; i < Want; ++i)
	{
		const TSubclassOf<AJREnemyCharacter> Cls = PickEnemyClass(Zone);
		if (!Cls)
		{
			break; // nada permitido (zona/MaxAlive)
		}
		// Espalha o grupo um pouco, ainda em cima do navmesh.
		FVector Location = Point;
		if (i > 0)
		{
			const FVector Offset(Random.FRandRange(-300.f, 300.f), Random.FRandRange(-300.f, 300.f), 0.f);
			FNavLocation NavOffset;
			if (Nav && Nav->ProjectPointToNavigation(Point + Offset, NavOffset, FVector(200.f, 200.f, 400.f)))
			{
				Location = NavOffset.Location + FVector(0.f, 0.f, 100.f);
			}
		}
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
		const FRotator Face = (Player->GetActorLocation() - Location).Rotation();
		if (AJREnemyCharacter* Enemy = GetWorld()->SpawnActor<AJREnemyCharacter>(Cls, Location, FRotator(0.f, Face.Yaw, 0.f), Params))
		{
			Enemy->SetForceAggro(true); // já vem atrás do jogador
			Spawned.Add(Enemy);
			++Made;
		}
	}
	if (HordeRemaining > 0)
	{
		HordeRemaining = FMath::Max(0, HordeRemaining - Made);
	}
	TotalSpawned += Made;
	UE_LOG(LogJR, Log, TEXT("Diretor (%s): +%d zumbis a %.0f m (vivos: diretor %d, mapa %d)"), PhaseName(Phase), Made,
		FVector::Dist(Point, Player->GetActorLocation()) / 100.0, Spawned.Num(), AliveInMap + Made);
	return Made;
}

FJRDirectorViewInfo AJRAIDirector::GetViewInfo(const APawn* Player) const
{
	FJRDirectorViewInfo View;
	const APlayerController* PC = Player ? Cast<APlayerController>(Player->GetController()) : nullptr;
	if (!PC)
	{
		return View;
	}
	FRotator ViewRotation;
	PC->GetPlayerViewPoint(View.Location, ViewRotation);
	View.Dir = ViewRotation.Vector().GetSafeNormal2D();
	float HalfAngle = Settings.HiddenConeHalfAngle;
	if (PC->PlayerCameraManager)
	{
		HalfAngle = FMath::Max(HalfAngle, PC->PlayerCameraManager->GetFOVAngle() * 0.5f + 10.f);
	}
	View.CosHalfAngle = FMath::Cos(FMath::DegreesToRadians(FMath::Clamp(HalfAngle, 0.f, 180.f)));
	View.bValid = true;
	return View;
}

bool AJRAIDirector::IsHiddenFromView(const FJRDirectorViewInfo& View, const FVector& Point, const AActor* IgnoreA, const AActor* IgnoreB) const
{
	if (!View.bValid)
	{
		return false;
	}
	const FVector ToPoint = (Point - View.Location).GetSafeNormal2D();
	if (FVector::DotProduct(ToPoint, View.Dir) < View.CosHalfAngle)
	{
		return true; // fora do cone da câmera (atrás/dos lados)
	}
	// Na frente da câmera: só vale se algo tapa a visão (parede, morro).
	FHitResult Hit;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRDirectorView), false);
	if (IgnoreA)
	{
		Query.AddIgnoredActor(IgnoreA);
	}
	if (IgnoreB)
	{
		Query.AddIgnoredActor(IgnoreB);
	}
	return GetWorld()->LineTraceSingleByChannel(Hit, View.Location, Point, ECC_Visibility, Query);
}

bool AJRAIDirector::FindSpawnPoint(const APawn* Player, bool bUseHordeFocus, const FJRDirectorViewInfo& View, FVector& OutPoint)
{
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!Nav || !Player || !View.bValid)
	{
		return false;
	}
	const FVector PlayerLocation = Player->GetActorLocation();
	FVector Velocity = Player->GetVelocity();
	Velocity.Z = 0.0;
	const bool bAhead = bPlayerDriving && Velocity.Size() > Settings.DrivingMinSpeed; // carro andando: nasce à frente
	const FVector Forward = Velocity.GetSafeNormal();
	const FVector Side(-Forward.Y, Forward.X, 0.0);

	FNavLocation PlayerNav;
	const bool bPlayerOnNav = Nav->ProjectPointToNavigation(PlayerLocation, PlayerNav, FVector(600.f, 600.f, 600.f));
	const int32 Tries = 16;
	for (int32 Try = 0; Try < Tries; ++Try)
	{
		// Horda de evento: metade das tentativas perto do evento; depois volta para perto do jogador.
		const bool bFocusTry = bUseHordeFocus && Try < Tries / 2;
		FVector Candidate;
		float MinDistance = Settings.OnFootMinDistance;
		if (bFocusTry)
		{
			const float Angle = Random.FRandRange(0.f, 2.f * PI);
			Candidate = HordeFocus + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f)
				* Random.FRandRange(Settings.EventHordeMinDistance, Settings.EventHordeMaxDistance);
			MinDistance = Settings.EventHordeMinDistance * 0.5f;
		}
		else if (bAhead)
		{
			// À frente do carro e para um dos lados da linha: o grupo entra na estrada.
			const float Lateral = Random.FRandRange(Settings.DrivingLateralMin, FMath::Max(Settings.DrivingLateralMin, Settings.DrivingLateralMax));
			Candidate = PlayerLocation + Forward * Random.FRandRange(Settings.DrivingMinDistance, Settings.DrivingMaxDistance)
				+ Side * (Random.FRand() < 0.5f ? -Lateral : Lateral);
			MinDistance = Settings.DrivingMinDistance * 0.7f;
		}
		else
		{
			const float Angle = Random.FRandRange(0.f, 2.f * PI);
			Candidate = PlayerLocation + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f)
				* Random.FRandRange(Settings.OnFootMinDistance, Settings.OnFootMaxDistance);
		}
		FNavLocation NavPoint;
		if (!Nav->ProjectPointToNavigation(Candidate, NavPoint, FVector(800.f, 800.f, 3000.f)))
		{
			continue;
		}
		const FVector Ground = NavPoint.Location;
		if (FVector::Dist2D(Ground, PlayerLocation) < MinDistance)
		{
			continue; // a projeção puxou para perto demais
		}
		if (IsInNoSpawnZone(Ground))
		{
			continue;
		}
		// À frente do carro quase tudo está "na tela": depois de metade das tentativas aceita se estiver longe.
		const bool bAcceptVisible = bAhead && !bFocusTry && Try >= Tries / 2;
		if (!bAcceptVisible && !IsHiddenFromView(View, Ground + FVector(0.f, 0.f, 120.f), Player, nullptr))
		{
			continue;
		}
		// Precisa haver caminho até o jogador (não nascer atrás de um penhasco ou numa ilha de navmesh).
		if (bPlayerOnNav)
		{
			const UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(), Ground, PlayerNav.Location);
			if (!Path || !Path->IsValid() || Path->IsPartial())
			{
				continue;
			}
		}
		OutPoint = Ground + FVector(0.f, 0.f, 100.f);
		return true;
	}
	return false;
}

void AJRAIDirector::RecycleFarEnemies(const APawn* Player)
{
	const FJRDirectorViewInfo View = GetViewInfo(Player);
	if (!View.bValid)
	{
		return;
	}
	const FVector PlayerLocation = Player->GetActorLocation();
	const double DespawnSq = FMath::Square(static_cast<double>(Settings.DespawnDistance));
	FVector Travel = Player->GetVelocity();
	Travel.Z = 0.0;
	const FVector Behind = Travel.SizeSquared() > 10000.0 ? -Travel.GetSafeNormal() : -View.Dir;

	auto ShouldRecycle = [&](const AJREnemyCharacter* Enemy, bool bHandPlaced)
	{
		if (!Enemy || Enemy->IsDead() || Enemy->IsGrabbingVehicle())
		{
			return false;
		}
		const FVector Location = Enemy->GetActorLocation();
		if (FVector::DistSquared2D(Location, PlayerLocation) <= DespawnSq)
		{
			return false;
		}
		if (bHandPlaced && FVector::DotProduct((Location - PlayerLocation).GetSafeNormal2D(), Behind) < 0.3)
		{
			return false; // colocado à mão: só os que ficaram para trás
		}
		return IsHiddenFromView(View, Location + FVector(0.f, 0.f, 60.f), Player, Enemy);
	};

	TArray<AJREnemyCharacter*> ToRemove;
	for (const TWeakObjectPtr<AJREnemyCharacter>& Weak : Spawned)
	{
		if (ShouldRecycle(Weak.Get(), false))
		{
			ToRemove.Add(Weak.Get());
		}
	}
	if (Settings.bRecycleHandPlaced)
	{
		for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
		{
			AJREnemyCharacter* Enemy = *It;
			if (!Spawned.Contains(Enemy) && ShouldRecycle(Enemy, true))
			{
				ToRemove.Add(Enemy);
			}
		}
	}
	for (AJREnemyCharacter* Enemy : ToRemove)
	{
		Spawned.Remove(Enemy);
		Enemy->Destroy();
	}
	if (ToRemove.Num() > 0)
	{
		TotalRecycled += ToRemove.Num();
		UE_LOG(LogJR, Log, TEXT("Diretor: %d zumbi(s) longe e fora da visão reciclados"), ToRemove.Num());
	}
}

void AJRAIDirector::BindPlayerPawn(APawn* Player)
{
	if (UJRHealthComponent* OldHealth = BoundHealth.Get())
	{
		OldHealth->OnHealthChanged.RemoveDynamic(this, &AJRAIDirector::HandlePlayerHealthChanged);
	}
	if (UJRVehicleDamageComponent* OldDamage = BoundVehicleDamage.Get())
	{
		OldDamage->OnIntegrityChanged.RemoveDynamic(this, &AJRAIDirector::HandleVehicleIntegrityChanged);
	}
	BoundHealth.Reset();
	BoundVehicleDamage.Reset();
	BoundPawn = Player;
	if (!Player)
	{
		return;
	}
	if (AJRVehiclePawn* Car = Cast<AJRVehiclePawn>(Player))
	{
		if (UJRVehicleDamageComponent* Damage = Car->GetDamageComponent())
		{
			Damage->OnIntegrityChanged.AddUniqueDynamic(this, &AJRAIDirector::HandleVehicleIntegrityChanged);
			BoundVehicleDamage = Damage;
			LastIntegrity = Damage->GetIntegrity();
		}
	}
	else if (UJRHealthComponent* Health = Player->FindComponentByClass<UJRHealthComponent>())
	{
		Health->OnHealthChanged.AddUniqueDynamic(this, &AJRAIDirector::HandlePlayerHealthChanged);
		BoundHealth = Health;
	}
}

void AJRAIDirector::HandlePlayerHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta)
{
	if (Delta < 0.f)
	{
		AddIntensity(-Delta * Settings.DamageToIntensity);
	}
}

void AJRAIDirector::HandleVehicleIntegrityChanged(float Integrity)
{
	const float Drop = LastIntegrity - Integrity;
	LastIntegrity = Integrity;
	if (Drop > 0.f)
	{
		AddIntensity(Drop * Settings.VehicleDamageToIntensity);
	}
}

FString AJRAIDirector::GetStatusLine() const
{
	const UWorld* World = GetWorld();
	const double Now = World ? World->GetTimeSeconds() : 0.0;
	const double Left = Phase == EJRDirectorPhase::BuildUp ? NextSpawnTime - Now : PhaseEndTime - Now;
	const UJREnemyBudgetSubsystem* Budget = World ? World->GetSubsystem<UJREnemyBudgetSubsystem>() : nullptr;
	FString Horde;
	if (Phase == EJRDirectorPhase::Peak)
	{
		Horde = HordeRemaining >= 0 ? FString::Printf(TEXT(" | horda '%s' faltam %d"), *HordeReason.ToString(), HordeRemaining)
			: FString::Printf(TEXT(" | horda '%s'"), *HordeReason.ToString());
	}
	const FString ZoneText = CurrentZoneName.IsEmpty() ? FString() : FString::Printf(TEXT(" | zona %s"), *CurrentZoneName);
	return FString::Printf(
		TEXT("Diretor IA: %s %s | intensidade %.2f | %s %.0f s | vivos diretor %d / mapa %d | perto %d | combate %.0f s | criados %d, reciclados %d | %s%s%s"),
		PhaseName(Phase), IsActiveNow() ? TEXT("(ativo)") : TEXT("(parado neste estágio)"), Intensity,
		Phase == EJRDirectorPhase::BuildUp ? TEXT("próximo grupo em") : TEXT("fase acaba em"), FMath::Max(0.0, Left),
		Spawned.Num(), Budget ? Budget->GetAliveEnemyCount() : -1, NearbyCount, CombatTime, TotalSpawned, TotalRecycled,
		bPlayerDriving ? TEXT("dirigindo") : TEXT("a pé"),
		*ZoneText, *Horde);
}

void AJRAIDirector::DrawDebug() const
{
	if ((!bShowDebug && !IsDebugEnabled()) || !GEngine)
	{
		return;
	}
	const FColor Color = Phase == EJRDirectorPhase::Peak ? FColor::Red : (Phase == EJRDirectorPhase::Relax ? FColor::Cyan : FColor::Yellow);
	GEngine->AddOnScreenDebugMessage(DirectorDebugKey, UpdateInterval + 0.2f, Color, GetStatusLine());
}

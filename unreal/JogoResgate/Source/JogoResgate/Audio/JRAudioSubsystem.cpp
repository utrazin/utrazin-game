// Copyright utrazin. All Rights Reserved.

#include "Audio/JRAudioSubsystem.h"

#include "AI/JREnemyArchetype.h"
#include "AI/JREnemyCharacter.h"
#include "Audio/JRSoundBank.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRHealthComponent.h"
#include "Components/AudioComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Gameplay/JRBlockingGate.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehicleDamageModel.h"
#include "Vehicles/JRVehiclePawn.h"

namespace JRAudio
{
	static const TCHAR* BankPath = TEXT("/Game/Audio/DA_SoundBank.DA_SoundBank");
	static const FName MusicExplore(TEXT("Music.Explore"));
	static const FName MusicTension(TEXT("Music.Tension"));
	static const FName MusicHorde(TEXT("Music.Horde"));
	static const FName MusicVictory(TEXT("Music.Victory"));
	static const FName MusicDefeat(TEXT("Music.Defeat"));
	static const FName Fuel(TEXT("Fuel"));
	static constexpr float KmhPerCms = 0.036f;
	static constexpr float EnemyUpdateInterval = 0.1f;
	static constexpr float SlowUpdateInterval = 0.25f;
	static constexpr double ZombieVoiceWindow = 2.0;

	/** Peso de uma zona: 1 dentro do raio, cai até 0 em Radius x Fade. */
	static float ZoneWeight(float Dist, float Radius, float Fade)
	{
		if (Dist <= Radius)
		{
			return 1.f;
		}
		const float Outer = Radius * Fade;
		return Dist >= Outer ? 0.f : 1.f - (Dist - Radius) / FMath::Max(1.f, Outer - Radius);
	}

	static bool IsCalmState(EJREnemyState S)
	{
		return S == EJREnemyState::Idle || S == EJREnemyState::Patrol || S == EJREnemyState::Investigate;
	}

	/** Piso pelo material físico / nome do componente e da malha (palavras em inglês e português). */
	static FName SurfaceFromHit(const FHitResult& Hit)
	{
		const AActor* HitActor = Hit.GetActor();
		if (HitActor && HitActor->IsA<AJRVehiclePawn>())
		{
			return TEXT("Metal");
		}
		FString Key;
		if (const UPhysicalMaterial* PM = Hit.PhysMaterial.Get())
		{
			Key = PM->GetName();
		}
		if (const UPrimitiveComponent* Comp = Hit.GetComponent())
		{
			Key += TEXT(" ");
			Key += Comp->GetName();
			if (const UStaticMeshComponent* SMC = Cast<UStaticMeshComponent>(Comp))
			{
				Key += TEXT(" ");
				Key += GetNameSafe(SMC->GetStaticMesh());
			}
		}
		if (HitActor)
		{
			Key += TEXT(" ");
			Key += HitActor->GetName();
		}
		struct FRule { const TCHAR* Word; const TCHAR* Surface; };
		static const FRule Rules[] = {
			{ TEXT("Metal"), TEXT("Metal") }, { TEXT("Container"), TEXT("Metal") }, { TEXT("Carro"), TEXT("Metal") },
			{ TEXT("Wood"), TEXT("Wood") }, { TEXT("Plank"), TEXT("Wood") }, { TEXT("Madeira"), TEXT("Wood") },
			{ TEXT("Bridge"), TEXT("Wood") }, { TEXT("Ponte"), TEXT("Wood") },
			{ TEXT("Grass"), TEXT("Grass") }, { TEXT("Grama"), TEXT("Grass") },
			{ TEXT("Sand"), TEXT("Sand") }, { TEXT("Areia"), TEXT("Sand") },
			{ TEXT("Rock"), TEXT("Stone") }, { TEXT("Stone"), TEXT("Stone") }, { TEXT("Pedra"), TEXT("Stone") },
			{ TEXT("Concrete"), TEXT("Stone") }, { TEXT("Concreto"), TEXT("Stone") }, { TEXT("Floor"), TEXT("Stone") }
		};
		for (const FRule& R : Rules)
		{
			if (Key.Contains(R.Word))
			{
				return FName(R.Surface);
			}
		}
		return NAME_None;
	}
}

// ===================================================================== básico

UJRAudioSubsystem* UJRAudioSubsystem::Get(const UObject* WorldContext)
{
	const UWorld* W = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	return W ? W->GetSubsystem<UJRAudioSubsystem>() : nullptr;
}

bool UJRAudioSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UJRAudioSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UJRAudioSubsystem, STATGROUP_Tickables);
}

void UJRAudioSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	Rand.GenerateNewSeed();
	CurrentMapName = FName(*UWorld::RemovePIEPrefix(InWorld.GetMapName()));
	LoadBank();
	LastRealTime = InWorld.GetRealTimeSeconds();
	NextThunderTime = LastRealTime + 20.0;
	ActorSpawnedHandle = InWorld.AddOnActorSpawnedHandler(
		FOnActorSpawned::FDelegate::CreateUObject(this, &UJRAudioSubsystem::HandleActorSpawned));
	BindWorldActors();
	BindDirector();
	if (UJRObjectiveSubsystem* Objective = InWorld.GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->OnStageChanged.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleStageChanged);
		Objective->OnCheckpointReached.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleCheckpointReached);
	}
	SpawnEmitters();
	bStarted = true;
}

void UJRAudioSubsystem::Deinitialize()
{
	if (UWorld* W = GetWorld())
	{
		W->RemoveOnActorSpawnedHandler(ActorSpawnedHandle);
	}
	UnbindHero();
	auto StopComp = [](UAudioComponent* C)
	{
		if (IsValid(C))
		{
			C->Stop();
		}
	};
	StopComp(MusicA);
	StopComp(MusicB);
	StopComp(LowHealthLoop);
	for (const TPair<FName, TObjectPtr<UAudioComponent>>& Pair : AmbienceLoops)
	{
		StopComp(Pair.Value);
	}
	for (UAudioComponent* C : EmitterLoops)
	{
		StopComp(C);
	}
	AmbienceLoops.Reset();
	EmitterLoops.Reset();
	Vehicles.Reset();
	Enemies.Reset();
	LoadedAssets.Reset();
	SoundBank = nullptr;
	bStarted = false;
	Super::Deinitialize();
}

void UJRAudioSubsystem::LoadBank()
{
	SoundBank = LoadObject<UJRSoundBank>(nullptr, JRAudio::BankPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	SoundIndex.Reset();
	SoundCategoryScale.Reset();
	if (!SoundBank)
	{
		UE_LOG(LogJR, Warning, TEXT("[Audio] %s não existe: rode tools/unreal/setup_audio.py. Jogo segue sem som novo."), JRAudio::BankPath);
		bWarnedNoBank = true;
		return;
	}
	DefaultAttenuationAsset = SoundBank->DefaultAttenuation.LoadSynchronous();
	for (int32 i = 0; i < SoundBank->Sounds.Num(); ++i)
	{
		const FJRSoundEntry& E = SoundBank->Sounds[i];
		SoundIndex.Add(E.Id, i);
		const FString Name = E.Id.ToString();
		float Scale = SoundBank->SFXVolume;
		if (Name.StartsWith(TEXT("Music.")))
		{
			Scale = SoundBank->MusicVolume;
		}
		else if (Name.StartsWith(TEXT("Amb.")))
		{
			Scale = SoundBank->AmbienceVolume;
		}
		else if (Name.StartsWith(TEXT("UI.")))
		{
			Scale = SoundBank->UIVolume;
		}
		SoundCategoryScale.Add(Scale * SoundBank->MasterVolume);
		for (const TSoftObjectPtr<USoundBase>& V : E.Variations)
		{
			if (USoundBase* S = V.LoadSynchronous())
			{
				LoadedAssets.Add(S);
			}
		}
		if (USoundAttenuation* A = E.Attenuation.LoadSynchronous())
		{
			LoadedAssets.Add(A);
		}
	}
	UE_LOG(LogJR, Log, TEXT("[Audio] banco com %d sons, %d zonas, %d emissores (mapa %s)"), SoundBank->Sounds.Num(),
		SoundBank->AmbienceZones.Num(), SoundBank->Emitters.Num(), *CurrentMapName.ToString());
}

void UJRAudioSubsystem::BindWorldActors()
{
	UWorld* W = GetWorld();
	if (!W)
	{
		return;
	}
	for (TActorIterator<AActor> It(W); It; ++It)
	{
		HandleActorSpawned(*It);
	}
}

void UJRAudioSubsystem::HandleActorSpawned(AActor* Actor)
{
	if (AJREnemyCharacter* E = Cast<AJREnemyCharacter>(Actor))
	{
		BindEnemy(E);
	}
	else if (AJRVehiclePawn* V = Cast<AJRVehiclePawn>(Actor))
	{
		BindVehicle(V);
	}
	else if (AJRBlockingGate* G = Cast<AJRBlockingGate>(Actor))
	{
		BindGate(G);
	}
	else if (AJRAIDirector* D = Cast<AJRAIDirector>(Actor))
	{
		if (!Director.IsValid())
		{
			BindDirector();
		}
	}
}

void UJRAudioSubsystem::BindVehicle(AJRVehiclePawn* Vehicle)
{
	if (!Vehicle || FindVehicleAudio(Vehicle))
	{
		return;
	}
	FJRVehicleAudio& VA = Vehicles.AddDefaulted_GetRef();
	VA.Vehicle = Vehicle;
	VA.PrevPendingItem = Vehicle->GetPendingRequiredItem();
	Vehicle->OnZombieCarEvent.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleZombieCarEvent);
	Vehicle->OnActorHit.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleVehicleHit);
}

void UJRAudioSubsystem::BindEnemy(AJREnemyCharacter* Enemy)
{
	if (!Enemy)
	{
		return;
	}
	for (const FJREnemyAudio& EA : Enemies)
	{
		if (EA.Enemy.Get() == Enemy)
		{
			return;
		}
	}
	FJREnemyAudio& EA = Enemies.AddDefaulted_GetRef();
	EA.Enemy = Enemy;
	EA.PrevLocation = Enemy->GetActorLocation();
	EA.PrevState = Enemy->GetEnemyState();
	Enemy->OnEnemyDied.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleEnemyDied);
	if (UJRHealthComponent* HC = Enemy->FindComponentByClass<UJRHealthComponent>())
	{
		HC->OnHealthChanged.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleEnemyHealthChanged);
	}
}

void UJRAudioSubsystem::BindGate(AJRBlockingGate* Gate)
{
	if (Gate)
	{
		Gate->OnGateOpened.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleGateOpened);
	}
}

void UJRAudioSubsystem::BindDirector()
{
	AJRAIDirector* D = AJRAIDirector::Find(this);
	if (!D || Director.Get() == D)
	{
		return;
	}
	Director = D;
	D->OnDirectorPhaseChanged.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleDirectorPhaseChanged);
	D->OnHordeTriggered.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleHordeTriggered);
}

void UJRAudioSubsystem::BindHero(AJRCharacter* Hero)
{
	if (!Hero || BoundHero.Get() == Hero)
	{
		return;
	}
	UnbindHero();
	BoundHero = Hero;
	Hero->LandedDelegate.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleHeroLanded);
	Hero->MovementModeChangedDelegate.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleHeroMovementModeChanged);
	if (UJRHealthComponent* HC = Hero->GetHealthComponent())
	{
		HC->OnHealthChanged.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleHeroHealthChanged);
		HC->OnDeath.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleHeroDeath);
	}
	if (UJRInventoryComponent* Inv = Hero->GetInventoryComponent())
	{
		Inv->OnInventoryChanged.AddUniqueDynamic(this, &UJRAudioSubsystem::HandleInventoryChanged);
		InventoryCounts[0] = Inv->GetCount(EJRConsumable::Bandage);
		InventoryCounts[1] = Inv->GetCount(EJRConsumable::Medkit);
		InventoryCounts[2] = Inv->GetCount(EJRConsumable::Fury);
	}
}

void UJRAudioSubsystem::UnbindHero()
{
	AJRCharacter* Old = BoundHero.Get();
	BoundHero.Reset();
	if (!Old)
	{
		return;
	}
	Old->LandedDelegate.RemoveDynamic(this, &UJRAudioSubsystem::HandleHeroLanded);
	Old->MovementModeChangedDelegate.RemoveDynamic(this, &UJRAudioSubsystem::HandleHeroMovementModeChanged);
	if (UJRHealthComponent* HC = Old->GetHealthComponent())
	{
		HC->OnHealthChanged.RemoveDynamic(this, &UJRAudioSubsystem::HandleHeroHealthChanged);
		HC->OnDeath.RemoveDynamic(this, &UJRAudioSubsystem::HandleHeroDeath);
	}
	if (UJRInventoryComponent* Inv = Old->GetInventoryComponent())
	{
		Inv->OnInventoryChanged.RemoveDynamic(this, &UJRAudioSubsystem::HandleInventoryChanged);
	}
}

void UJRAudioSubsystem::SpawnEmitters()
{
	if (!SoundBank)
	{
		return;
	}
	for (const FJRAudioEmitter& Em : SoundBank->Emitters)
	{
		if (!Em.MapName.IsNone() && Em.MapName != CurrentMapName)
		{
			continue;
		}
		FJRSoundPick Pick;
		if (!Resolve(Em.LoopId, false, Pick))
		{
			continue;
		}
		// Atenuação própria do emissor (raio do lugar), criada em tempo de execução.
		USoundAttenuation* Att = NewObject<USoundAttenuation>(this);
		Att->Attenuation.bAttenuate = true;
		Att->Attenuation.bSpatialize = true;
		Att->Attenuation.AttenuationShapeExtents = FVector(Em.Radius * 0.25f, 0.f, 0.f);
		Att->Attenuation.FalloffDistance = FMath::Max(100.f, Em.Radius * 0.75f);
		EmitterAttenuations.Add(Att);
		UAudioComponent* C = UGameplayStatics::SpawnSoundAtLocation(this, Pick.Sound, Em.Location, FRotator::ZeroRotator,
			Pick.Volume * Em.Volume, 1.f, 0.f, Att, nullptr, false);
		if (C)
		{
			EmitterLoops.Add(C);
		}
	}
}

// ===================================================================== resolver e tocar

const FJRSoundEntry* UJRAudioSubsystem::FindEntry(FName Id, float* OutCategoryScale) const
{
	const int32* Idx = SoundBank ? SoundIndex.Find(Id) : nullptr;
	if (!Idx || !SoundBank->Sounds.IsValidIndex(*Idx))
	{
		return nullptr;
	}
	if (OutCategoryScale)
	{
		*OutCategoryScale = SoundCategoryScale.IsValidIndex(*Idx) ? SoundCategoryScale[*Idx] : 1.f;
	}
	return &SoundBank->Sounds[*Idx];
}

bool UJRAudioSubsystem::Resolve(FName Id, bool bCheckLimits, FJRSoundPick& Out)
{
	float Scale = 1.f;
	const FJRSoundEntry* E = FindEntry(Id, &Scale);
	const UWorld* W = GetWorld();
	if (!E || !W || E->Variations.Num() == 0)
	{
		if (SoundBank && !Id.IsNone() && !E)
		{
			UE_LOG(LogJR, Verbose, TEXT("[Audio] id sem som no banco: %s"), *Id.ToString());
		}
		return false;
	}
	const double Now = W->GetRealTimeSeconds();
	if (bCheckLimits)
	{
		if (E->MinInterval > 0.f)
		{
			if (const double* Last = LastPlayTime.Find(Id); Last && Now - *Last < E->MinInterval)
			{
				return false;
			}
		}
		if (E->bZombieVoice && SoundBank)
		{
			RecentZombieVoices.RemoveAll([Now](double T) { return Now - T > JRAudio::ZombieVoiceWindow; });
			if (RecentZombieVoices.Num() >= SoundBank->MaxZombieVoices)
			{
				return false;
			}
			RecentZombieVoices.Add(Now);
		}
		LastPlayTime.Add(Id, Now);
	}
	const int32 Num = E->Variations.Num();
	int32 Index = Num > 1 ? Rand.RandRange(0, Num - 1) : 0;
	if (Num > 1)
	{
		if (const int32* Prev = LastVariation.Find(Id); Prev && *Prev == Index)
		{
			Index = (Index + 1) % Num;
		}
	}
	LastVariation.Add(Id, Index);
	Out.Sound = E->Variations[Index].Get();
	if (!Out.Sound)
	{
		Out.Sound = E->Variations[Index].LoadSynchronous();
	}
	Out.Attenuation = E->Attenuation.Get() ? E->Attenuation.Get() : DefaultAttenuationAsset.Get();
	Out.Volume = E->Volume * Scale;
	Out.Pitch = E->PitchMax > E->PitchMin ? Rand.FRandRange(E->PitchMin, E->PitchMax) : E->PitchMin;
	return Out.Sound != nullptr;
}

bool UJRAudioSubsystem::Play2D(FName Id, float VolumeMultiplier, float PitchMultiplier)
{
	FJRSoundPick Pick;
	if (!Resolve(Id, true, Pick))
	{
		return false;
	}
	UGameplayStatics::PlaySound2D(this, Pick.Sound, Pick.Volume * VolumeMultiplier, Pick.Pitch * PitchMultiplier);
	Last2DSoundTime = GetWorld()->GetRealTimeSeconds();
	return true;
}

bool UJRAudioSubsystem::PlayAt(FName Id, const FVector& Location, float VolumeMultiplier, float PitchMultiplier)
{
	FJRSoundPick Pick;
	if (!Resolve(Id, true, Pick))
	{
		return false;
	}
	UGameplayStatics::PlaySoundAtLocation(this, Pick.Sound, Location, Pick.Volume * VolumeMultiplier,
		Pick.Pitch * PitchMultiplier, 0.f, Pick.Attenuation);
	return true;
}

UAudioComponent* UJRAudioSubsystem::PlayAttached(FName Id, USceneComponent* AttachTo, FName Socket, float VolumeMultiplier)
{
	FJRSoundPick Pick;
	if (!AttachTo || !Resolve(Id, true, Pick))
	{
		return nullptr;
	}
	return UGameplayStatics::SpawnSoundAttached(Pick.Sound, AttachTo, Socket, FVector::ZeroVector,
		EAttachLocation::KeepRelativeOffset, true, Pick.Volume * VolumeMultiplier, Pick.Pitch, 0.f, Pick.Attenuation);
}

UAudioComponent* UJRAudioSubsystem::CreateLoop(FName Id, USceneComponent* AttachTo)
{
	FJRSoundPick Pick;
	if (!Resolve(Id, false, Pick))
	{
		return nullptr;
	}
	UAudioComponent* C = nullptr;
	if (AttachTo)
	{
		C = UGameplayStatics::SpawnSoundAttached(Pick.Sound, AttachTo, NAME_None, FVector::ZeroVector,
			EAttachLocation::KeepRelativeOffset, true, 0.001f, 1.f, 0.f, Pick.Attenuation, nullptr, false);
	}
	else
	{
		C = UGameplayStatics::CreateSound2D(this, Pick.Sound, 0.001f, 1.f, 0.f, nullptr, false, false);
	}
	return C;
}

void UJRAudioSubsystem::UpdateLoopSlot(TObjectPtr<UAudioComponent>& Slot, FName Id, float Level, USceneComponent* AttachTo, float Pitch)
{
	if (Level <= 0.01f)
	{
		if (IsValid(Slot) && Slot->IsPlaying())
		{
			Slot->Stop();
		}
		return;
	}
	if (!IsValid(Slot))
	{
		Slot = CreateLoop(Id, AttachTo);
		if (!Slot)
		{
			return;
		}
	}
	float Scale = 1.f;
	const FJRSoundEntry* E = FindEntry(Id, &Scale);
	const float Base = E ? E->Volume * Scale : 1.f;
	Slot->SetVolumeMultiplier(Base * Level);
	Slot->SetPitchMultiplier(Pitch);
	if (!Slot->IsPlaying())
	{
		Slot->Play();
	}
}

void UJRAudioSubsystem::PlayMusic(FName Id, float FadeSeconds)
{
	if (Id == CurrentMusicId)
	{
		return;
	}
	CurrentMusicId = Id;
	const UWorld* W = GetWorld();
	LastMusicSwitchTime = W ? W->GetRealTimeSeconds() : 0.0;
	// A toca o atual; o novo entra no B e os dois trocam de lugar.
	if (IsValid(MusicA) && MusicA->IsPlaying())
	{
		MusicA->FadeOut(FadeSeconds, 0.f);
	}
	if (IsValid(MusicB))
	{
		MusicB->Stop();
		MusicB->DestroyComponent();
	}
	MusicB = MusicA;
	MusicA = nullptr;
	if (Id.IsNone())
	{
		return;
	}
	FJRSoundPick Pick;
	if (!Resolve(Id, false, Pick))
	{
		return;
	}
	MusicA = UGameplayStatics::CreateSound2D(this, Pick.Sound, Pick.Volume, 1.f, 0.f, nullptr, false, false);
	if (MusicA)
	{
		MusicA->FadeIn(FadeSeconds, 1.f);
	}
}

void UJRAudioSubsystem::PlayStinger(FName Id, float HoldSeconds)
{
	PlayMusic(NAME_None, 1.f);
	Play2D(Id);
	if (const UWorld* W = GetWorld())
	{
		MusicHoldUntil = W->GetRealTimeSeconds() + HoldSeconds;
	}
}

void UJRAudioSubsystem::NotifyToast()
{
	// O toast costuma vir antes do som do item (AJRPickup avisa depois): espera um pouquinho e decide no Tick.
	if (const UWorld* W = GetWorld(); W && !bToastPending)
	{
		bToastPending = true;
		ToastRequestTime = W->GetRealTimeSeconds();
	}
}

// ===================================================================== Tick

void UJRAudioSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UWorld* W = GetWorld();
	if (!bStarted || !W || !SoundBank)
	{
		return;
	}
	const double Now = W->GetRealTimeSeconds();
	const float RealDelta = FMath::Clamp(static_cast<float>(Now - LastRealTime), 0.f, 0.1f);
	LastRealTime = Now;

	if (const APlayerController* PC = W->GetFirstPlayerController())
	{
		if (PC->PlayerCameraManager)
		{
			ListenerLocation = PC->PlayerCameraManager->GetCameraLocation();
		}
		else if (const APawn* P = PC->GetPawn())
		{
			ListenerLocation = P->GetActorLocation();
		}
	}
	UpdatePlayerPawn();
	if (AJRCharacter* Hero = Cast<AJRCharacter>(PlayerPawn.Get()))
	{
		UpdateHero(Hero, DeltaTime);
	}
	UpdateVehiclesFast(DeltaTime);
	UpdateLowHealth(RealDelta);
	UpdateAmbienceLevels(RealDelta);
	if (bToastPending && Now - ToastRequestTime >= 0.05)
	{
		bToastPending = false;
		if (Last2DSoundTime < ToastRequestTime - 0.3)
		{
			Play2D(TEXT("UI.Toast"));
		}
	}

	if (Now >= NextEnemyUpdate)
	{
		NextEnemyUpdate = Now + JRAudio::EnemyUpdateInterval;
		UpdateEnemies(Now);
	}
	if (Now >= NextSlowUpdate)
	{
		NextSlowUpdate = Now + JRAudio::SlowUpdateInterval;
		if (!Director.IsValid())
		{
			BindDirector();
		}
		UpdateVehiclesSlow(Now);
		UpdateAmbienceTargets(Now);
		UpdateMusic(Now);
	}
}

// ===================================================================== jogador

void UJRAudioSubsystem::UpdatePlayerPawn()
{
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	APawn* NewPawn = PC ? PC->GetPawn() : nullptr;
	APawn* OldPawn = PlayerPawn.Get();
	if (NewPawn != OldPawn)
	{
		PlayerPawn = NewPawn;
		OnPlayerPawnChanged(OldPawn, NewPawn);
	}
}

void UJRAudioSubsystem::OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn)
{
	if (AJRVehiclePawn* NewCar = Cast<AJRVehiclePawn>(NewPawn))
	{
		BindVehicle(NewCar);
		PlayAt(TEXT("Car.Door.Close"), NewCar->GetActorLocation());
	}
	else if (AJRVehiclePawn* OldCar = Cast<AJRVehiclePawn>(OldPawn))
	{
		if (NewPawn)
		{
			PlayAt(TEXT("Car.Door.Open"), OldCar->GetActorLocation());
		}
	}
	if (AJRCharacter* Hero = Cast<AJRCharacter>(NewPawn))
	{
		BindHero(Hero);
		HeroStepAccum = 0.f;
	}
}

void UJRAudioSubsystem::UpdateHero(AJRCharacter* Hero, float DeltaTime)
{
	UpdateItemWheel(Hero);
	const UCharacterMovementComponent* CMC = Hero->GetCharacterMovement();
	const FVector Vel = Hero->GetVelocity();
	const float Speed2D = Vel.Size2D();
	const float Stride = FMath::GetMappedRangeValueClamped(FVector2f(150.f, 650.f), FVector2f(115.f, 190.f), Speed2D);
	if (!CMC || !CMC->IsMovingOnGround() || Speed2D < 60.f)
	{
		// Parado: o primeiro passo ao voltar a andar sai logo.
		HeroStepAccum = Stride * 0.6f;
	}
	else
	{
		HeroStepAccum += Speed2D * DeltaTime;
		if (HeroStepAccum >= Stride)
		{
			HeroStepAccum = FMath::Fmod(HeroStepAccum, Stride);
			PlayFootstep(Hero, Speed2D);
		}
	}
	LastHeroVz = Vel.Z;
}

void UJRAudioSubsystem::PlayFootstep(AJRCharacter* Hero, float Speed2D)
{
	const FVector Feet = Hero->GetActorLocation() - FVector(0.f, 0.f, Hero->GetSimpleCollisionHalfHeight());
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRAudioStep), false, Hero);
	Params.bReturnPhysicalMaterial = true;
	FName Surface = NAME_None;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Feet + FVector(0.f, 0.f, 30.f), Feet - FVector(0.f, 0.f, 60.f), ECC_Visibility, Params))
	{
		Surface = JRAudio::SurfaceFromHit(Hit);
	}
	if (Surface.IsNone())
	{
		Surface = ZoneSurface.IsNone() ? FName(TEXT("Dirt")) : ZoneSurface;
	}
	const float Vol = FMath::GetMappedRangeValueClamped(FVector2f(150.f, 600.f), FVector2f(0.45f, 1.f), Speed2D);
	const FName StepId(*FString::Printf(TEXT("Hero.Step.%s"), *Surface.ToString()));
	if (!PlayAt(StepId, Feet, Vol))
	{
		PlayAt(TEXT("Hero.Step.Dirt"), Feet, Vol);
	}
	if (!ZoneFootExtraId.IsNone() && Rand.FRand() < ZoneFootExtraChance)
	{
		PlayAt(ZoneFootExtraId, Feet, 0.8f);
	}
}

void UJRAudioSubsystem::UpdateItemWheel(AJRCharacter* Hero)
{
	const bool bOpen = Hero->IsItemWheelOpen();
	if (bOpen != bWheelOpen)
	{
		bWheelOpen = bOpen;
		Play2D(bOpen ? FName(TEXT("UI.Wheel.Open")) : FName(TEXT("UI.Wheel.Close")));
		WheelHighlight = bOpen ? Hero->GetItemWheelHighlight() : -1;
		WheelTab = bOpen ? Hero->GetItemWheelTab() : -1;
		return;
	}
	if (!bOpen)
	{
		return;
	}
	const int32 Tab = Hero->GetItemWheelTab();
	if (Tab != WheelTab)
	{
		WheelTab = Tab;
		WheelHighlight = Hero->GetItemWheelHighlight();
		Play2D(TEXT("UI.Wheel.Tab"));
		return;
	}
	const int32 Highlight = Hero->GetItemWheelHighlight();
	if (Highlight != WheelHighlight)
	{
		WheelHighlight = Highlight;
		Play2D(TEXT("UI.Wheel.Hover"));
	}
}

void UJRAudioSubsystem::UpdateLowHealth(float RealDelta)
{
	float Target = 0.f;
	if (const AJRCharacter* Hero = BoundHero.Get())
	{
		const UJRHealthComponent* HC = Hero->GetHealthComponent();
		if (HC && !HC->IsDead() && HC->GetHealthNormalized() < SoundBank->LowHealthFraction)
		{
			// Mais forte quanto menos vida.
			Target = FMath::GetMappedRangeValueClamped(FVector2f(SoundBank->LowHealthFraction, 0.f), FVector2f(0.5f, 1.f),
				HC->GetHealthNormalized());
		}
	}
	LowHealthLevel = FMath::FInterpConstantTo(LowHealthLevel, Target, RealDelta, 0.8f);
	UpdateLoopSlot(LowHealthLoop, TEXT("Hero.LowHealth"), LowHealthLevel, nullptr);
}

void UJRAudioSubsystem::HandleHeroLanded(const FHitResult& Hit)
{
	const float Fall = -LastHeroVz;
	if (Fall > 300.f)
	{
		if (const AJRCharacter* Hero = BoundHero.Get())
		{
			PlayAt(TEXT("Hero.Land"), Hit.ImpactPoint.IsNearlyZero() ? Hero->GetActorLocation() : FVector(Hit.ImpactPoint),
				FMath::GetMappedRangeValueClamped(FVector2f(300.f, 1200.f), FVector2f(0.4f, 1.f), Fall));
		}
	}
	HeroStepAccum = 0.f;
}

void UJRAudioSubsystem::HandleHeroMovementModeChanged(ACharacter* Character, EMovementMode PrevMovementMode, uint8 PreviousCustomMode)
{
	const UCharacterMovementComponent* CMC = Character ? Character->GetCharacterMovement() : nullptr;
	if (CMC && CMC->MovementMode == MOVE_Falling && PrevMovementMode == MOVE_Walking && Character->GetVelocity().Z > 150.f)
	{
		PlayAt(TEXT("Hero.Jump"), Character->GetActorLocation());
	}
}

void UJRAudioSubsystem::HandleHeroHealthChanged(UJRHealthComponent* HealthComp, float NewHealth, float Delta)
{
	if (Delta < -0.5f && NewHealth > 0.f && HealthComp && HealthComp->GetOwner())
	{
		PlayAt(TEXT("Hero.Hurt"), HealthComp->GetOwner()->GetActorLocation());
	}
}

void UJRAudioSubsystem::HandleHeroDeath(UJRHealthComponent* HealthComp, AActor* Killer)
{
	if (HealthComp && HealthComp->GetOwner())
	{
		PlayAt(TEXT("Hero.Death"), HealthComp->GetOwner()->GetActorLocation());
	}
	PlayStinger(JRAudio::MusicDefeat, 9.f);
}

void UJRAudioSubsystem::HandleInventoryChanged(EJRConsumable Item, int32 NewCount)
{
	const int32 Slot = static_cast<int32>(Item);
	if (Slot < 0 || Slot >= static_cast<int32>(UE_ARRAY_COUNT(InventoryCounts)))
	{
		return;
	}
	const int32 OldCount = InventoryCounts[Slot];
	InventoryCounts[Slot] = NewCount;
	if (NewCount < OldCount)
	{
		// Gastou: bandagem/kit (pegar já tem som no AJRPickup e no baú).
		// [A-075] fúria tem som próprio (antes: bipe de pickup)
		Play2D(Item == EJRConsumable::Fury ? FName(TEXT("Hero.Fury")) : FName(TEXT("Hero.Bandage")));
	}
}

// ===================================================================== carro

FJRVehicleAudio* UJRAudioSubsystem::FindVehicleAudio(const AActor* Vehicle)
{
	for (FJRVehicleAudio& VA : Vehicles)
	{
		if (VA.Vehicle.Get() == Vehicle)
		{
			return &VA;
		}
	}
	return nullptr;
}

void UJRAudioSubsystem::UpdateVehiclesFast(float DeltaTime)
{
	const APawn* Driven = PlayerPawn.Get();
	const float Dt = FMath::Max(DeltaTime, 1.e-3f);
	for (int32 i = Vehicles.Num() - 1; i >= 0; --i)
	{
		FJRVehicleAudio& VA = Vehicles[i];
		AJRVehiclePawn* V = VA.Vehicle.Get();
		if (!V)
		{
			Vehicles.RemoveAt(i);
			continue;
		}
		USceneComponent* Root = V->GetRootComponent();
		const FVector Vel = V->GetVelocity();
		if (V != Driven || V->IsWrecked())
		{
			UpdateLoopSlot(VA.Engine, TEXT("Car.Engine"), 0.f, Root);
			UpdateLoopSlot(VA.Skid, TEXT("Car.Skid"), 0.f, Root);
			UpdateLoopSlot(VA.Nitro, TEXT("Car.Nitro"), 0.f, Root);
			VA.bNitroWasActive = false;
			VA.SkidLevel = 0.f;
			VA.AirTime = 0.f;
			VA.PrevVelocity = Vel;
			continue;
		}
		// Motor: tom pelo RPM do Chaos (ou pela velocidade, se não houver RPM).
		const float SpeedKmh = FMath::Abs(V->GetSpeedKmh());
		float Rpm01 = SpeedKmh / 140.f;
		if (const UChaosWheeledVehicleMovementComponent* Move = Cast<UChaosWheeledVehicleMovementComponent>(V->GetVehicleMovementComponent()))
		{
			const float MaxRpm = Move->GetEngineMaxRotationSpeed();
			if (MaxRpm > 1.f)
			{
				Rpm01 = Move->GetEngineRotationSpeed() / MaxRpm;
			}
		}
		Rpm01 = FMath::Clamp(Rpm01, 0.f, 1.f);
		const bool bNitro = V->IsNitroActive();
		const float TargetPitch = FMath::Lerp(0.7f, 1.85f, Rpm01) + (bNitro ? 0.1f : 0.f);
		VA.EnginePitch = FMath::FInterpTo(VA.EnginePitch, TargetPitch, Dt, 6.f);
		// [A-075] tanque seco: motor calado. Engasgando: volume e tom "tossem".
		float EngineLevel = 0.55f + 0.45f * Rpm01;
		float EnginePitchOut = VA.EnginePitch;
		if (V->IsEngineDead())
		{
			EngineLevel = 0.f;
		}
		else if (V->IsFuelSputtering())
		{
			const float Cough = Rand.FRand() < 0.18f ? 0.25f : 1.f;
			EngineLevel *= Cough;
			EnginePitchOut *= Rand.FRandRange(0.88f, 1.02f);
		}
		UpdateLoopSlot(VA.Engine, TEXT("Car.Engine"), EngineLevel, Root, EnginePitchOut);

		// No chão? (traço curto para baixo; só o carro do jogador)
		FHitResult Ground;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(JRAudioCarGround), false, V);
		const FVector Loc = V->GetActorLocation();
		const bool bGrounded = GetWorld()->LineTraceSingleByChannel(Ground, Loc + FVector(0.f, 0.f, 50.f), Loc - FVector(0.f, 0.f, 200.f),
			ECC_Visibility, Params);
		if (!bGrounded)
		{
			VA.AirTime += Dt;
			VA.FallSpeed = FMath::Max(VA.FallSpeed, -Vel.Z);
		}
		else
		{
			if (VA.AirTime > 0.35f && VA.FallSpeed > 300.f)
			{
				PlayAt(TEXT("Car.Land"), Loc, FMath::GetMappedRangeValueClamped(FVector2f(300.f, 1500.f), FVector2f(0.4f, 1.f), VA.FallSpeed));
			}
			VA.AirTime = 0.f;
			VA.FallSpeed = 0.f;
		}

		// Derrapagem: deslize lateral ou freada forte, só no chão.
		const float Lateral = FMath::Abs(FVector::DotProduct(Vel, V->GetActorRightVector()));
		const float Decel = (VA.PrevVelocity.Size() - Vel.Size()) / Dt;
		float SkidTarget = bGrounded ? FMath::Clamp((Lateral - 300.f) / 700.f, 0.f, 1.f) : 0.f;
		if (bGrounded && Decel > 1400.f && SpeedKmh > 20.f)
		{
			SkidTarget = FMath::Max(SkidTarget, 0.6f);
		}
		VA.SkidLevel = FMath::FInterpTo(VA.SkidLevel, SkidTarget, Dt, 8.f);
		UpdateLoopSlot(VA.Skid, TEXT("Car.Skid"), VA.SkidLevel, Root, 0.9f + 0.2f * VA.SkidLevel);

		// Nitro: arranque + rugido enquanto ativo.
		if (bNitro && !VA.bNitroWasActive)
		{
			PlayAt(TEXT("Car.Nitro.Start"), Loc);
		}
		VA.bNitroWasActive = bNitro;
		UpdateLoopSlot(VA.Nitro, TEXT("Car.Nitro"), bNitro ? 1.f : 0.f, Root);
		VA.PrevVelocity = Vel;
	}
}

void UJRAudioSubsystem::UpdateVehiclesSlow(double Now)
{
	const APawn* Driven = PlayerPawn.Get();
	for (FJRVehicleAudio& VA : Vehicles)
	{
		AJRVehiclePawn* V = VA.Vehicle.Get();
		if (!V)
		{
			continue;
		}
		const FVector Loc = V->GetActorLocation();
		// Fogo
		const EJRVehicleDamageFXState FX = V->GetDamageFXState();
		const float FireLevel = FX == EJRVehicleDamageFXState::Burning ? 1.f : (FX == EJRVehicleDamageFXState::Wrecked ? 0.6f : 0.f);
		UpdateLoopSlot(VA.Fire, TEXT("Car.Fire"), FireLevel, V->GetRootComponent());

		// Pneus furados (bit novo = estouro)
		if (const UJRVehicleDamageComponent* Damage = V->GetDamageComponent())
		{
			uint8 Mask = 0;
			for (int32 w = 0; w < static_cast<int32>(EJRWheel::Count); ++w)
			{
				if (Damage->IsTireFlat(static_cast<EJRWheel>(w)))
				{
					Mask |= static_cast<uint8>(1 << w);
				}
			}
			if ((Mask & ~VA.FlatMask) != 0)
			{
				PlayAt(TEXT("Car.TireFlat"), Loc);
			}
			VA.FlatMask = Mask;
		}

		// Gasolina: o carro passou a esperar o item Fuel (alerta) ou recebeu o galão (enchendo).
		const FName Pending = V->GetPendingRequiredItem();
		if (Pending != VA.PrevPendingItem)
		{
			if (Pending == JRAudio::Fuel)
			{
				Play2D(TEXT("UI.LowFuel"));
			}
			else if (VA.PrevPendingItem == JRAudio::Fuel)
			{
				PlayAt(TEXT("World.Fuel.Fill"), Loc);
			}
			VA.PrevPendingItem = Pending;
		}
		// [A-075] entrou na reserva dirigindo: alerta uma vez (rearma quando o tanque passa da reserva de novo)
		if (V == Driven && Pending.IsNone())
		{
			if (V->IsFuelReserve() && !VA.bFuelReserveWarned)
			{
				Play2D(TEXT("UI.LowFuel"));
				VA.bFuelReserveWarned = true;
			}
			else if (!V->IsFuelReserve())
			{
				VA.bFuelReserveWarned = false;
			}
		}

		// Unhas no capô enquanto houver zumbi agarrado no carro do jogador.
		if (V == Driven && Now >= VA.NextNailsTime)
		{
			for (const FJREnemyAudio& EA : Enemies)
			{
				const AJREnemyCharacter* E = EA.Enemy.Get();
				if (E && !E->IsDead() && E->IsGrabbingVehicle() && FVector::DistSquared(E->GetActorLocation(), Loc) < FMath::Square(700.f))
				{
					PlayAt(TEXT("Zombie.Nails"), E->GetActorLocation());
					VA.NextNailsTime = Now + Rand.FRandRange(1.0f, 2.0f);
					break;
				}
			}
		}
	}
}

void UJRAudioSubsystem::HandleVehicleHit(AActor* SelfActor, AActor* OtherActor, FVector NormalImpulse, const FHitResult& Hit)
{
	FJRVehicleAudio* VA = FindVehicleAudio(SelfActor);
	if (!VA || !SelfActor || Cast<AJREnemyCharacter>(OtherActor))
	{
		return; // zumbi x carro tem os eventos próprios
	}
	const FVector N = Hit.ImpactNormal;
	if (N.Z > 0.65f)
	{
		return; // chão/rampa (pouso tratado à parte)
	}
	const double Now = GetWorld()->GetRealTimeSeconds();
	// Velocidade de antes da batida (a física já pode ter refletido a atual).
	const FVector Vel = VA->PrevVelocity.IsNearlyZero() ? SelfActor->GetVelocity() : VA->PrevVelocity;
	const float IntoKmh = FMath::Max(0.f, -static_cast<float>(FVector::DotProduct(Vel, N))) * JRAudio::KmhPerCms;
	const float AlongKmh = (Vel - N * FVector::DotProduct(Vel, N)).Size() * JRAudio::KmhPerCms;
	const FVector Where = Hit.ImpactPoint;
	if (IntoKmh > 28.f && Now - VA->LastImpactTime > 0.3)
	{
		PlayAt(TEXT("Car.Impact.Heavy"), Where, FMath::GetMappedRangeValueClamped(FVector2f(28.f, 80.f), FVector2f(0.7f, 1.f), IntoKmh));
		VA->LastImpactTime = Now;
	}
	else if (IntoKmh > 7.f && Now - VA->LastImpactTime > 0.25)
	{
		PlayAt(TEXT("Car.Impact.Light"), Where, FMath::GetMappedRangeValueClamped(FVector2f(7.f, 28.f), FVector2f(0.4f, 1.f), IntoKmh));
		VA->LastImpactTime = Now;
	}
	else if (AlongKmh > 15.f && Now - VA->LastScrapeTime > 0.35)
	{
		PlayAt(TEXT("Car.Scrape"), Where, FMath::GetMappedRangeValueClamped(FVector2f(15.f, 90.f), FVector2f(0.4f, 1.f), AlongKmh));
		VA->LastScrapeTime = Now;
	}
}

void UJRAudioSubsystem::HandleZombieCarEvent(EJRZombieCarEvent Event, AActor* Zombie, FVector Location, float Value)
{
	switch (Event)
	{
	case EJRZombieCarEvent::ZombieHitCar:
		PlayAt(TEXT("Car.Impact.Light"), Location, 0.7f);
		break;
	case EJRZombieCarEvent::ZombieGrabbed:
		PlayAt(TEXT("Zombie.Nails"), Location);
		PlayAt(TEXT("Zombie.Growl"), Location, 0.8f);
		break;
	case EJRZombieCarEvent::ZombieThrownOff:
		PlayAt(TEXT("Zombie.Pain"), Location);
		break;
	case EJRZombieCarEvent::RunOver:
		PlayAt(TEXT("Zombie.HitCar"), Location, FMath::GetMappedRangeValueClamped(FVector2f(20.f, 90.f), FVector2f(0.7f, 1.f), Value));
		break;
	case EJRZombieCarEvent::ZombiePushed:
		PlayAt(TEXT("Zombie.HitCar"), Location, 0.5f, 1.1f);
		break;
	case EJRZombieCarEvent::BarricadeBroken:
		PlayAt(TEXT("World.Barricade.Break"), Location);
		break;
	case EJRZombieCarEvent::Explosion:
		PlayAt(TEXT("Car.Explosion"), Location);
		break;
	default:
		break;
	}
}

// ===================================================================== zumbis

void UJRAudioSubsystem::UpdateEnemies(double Now)
{
	const float VoiceR2 = FMath::Square(SoundBank->ZombieVoiceRadius);
	const float StepR2 = FMath::Square(SoundBank->ZombieStepRadius);
	// Ponteiros (não índices): o RemoveAtSwap abaixo muda a ordem do array.
	TArray<AJREnemyCharacter*, TInlineAllocator<16>> Calm;
	TArray<AJREnemyCharacter*, TInlineAllocator<16>> Engaged;
	int32 EngagedClose = 0;
	for (int32 i = Enemies.Num() - 1; i >= 0; --i)
	{
		FJREnemyAudio& EA = Enemies[i];
		AJREnemyCharacter* E = EA.Enemy.Get();
		if (!E)
		{
			Enemies.RemoveAtSwap(i);
			continue;
		}
		if (E->IsDead())
		{
			continue;
		}
		if (!EA.bEliteKnown)
		{
			if (const UJREnemyArchetype* Arch = E->GetArchetype())
			{
				EA.bEliteKnown = true;
				EA.bElite = SoundBank->EliteArchetypeIds.Contains(Arch->ArchetypeId) || Arch->MaxHealth >= SoundBank->EliteMinHealth;
			}
		}
		const FVector Loc = E->GetActorLocation();
		const EJREnemyState State = E->GetEnemyState();
		const float DistSq = FVector::DistSquared(Loc, ListenerLocation);
		if (DistSq < VoiceR2)
		{
			if (State != EA.PrevState)
			{
				if ((State == EJREnemyState::Alert || State == EJREnemyState::Chase) && JRAudio::IsCalmState(EA.PrevState) && Now >= EA.NextVoiceTime)
				{
					PlayAt(EA.bElite ? FName(TEXT("Zombie.EliteRoar")) : FName(TEXT("Zombie.Growl")), Loc);
					EA.NextVoiceTime = Now + 4.0;
				}
				if (State == EJREnemyState::Attack)
				{
					PlayAt(TEXT("Zombie.Attack"), Loc);
					EA.NextAttackTime = Now + Rand.FRandRange(1.1f, 1.5f);
				}
			}
			else if (State == EJREnemyState::Attack && Now >= EA.NextAttackTime)
			{
				PlayAt(TEXT("Zombie.Attack"), Loc);
				EA.NextAttackTime = Now + Rand.FRandRange(1.1f, 1.5f);
			}
			if (JRAudio::IsCalmState(State))
			{
				Calm.Add(E);
			}
			else
			{
				Engaged.Add(E);
				if (DistSq < FMath::Square(2000.f))
				{
					++EngagedClose;
				}
			}
			// Passos arrastados (só os perto)
			if (DistSq < StepR2 && !E->IsGrabbingVehicle())
			{
				const float Moved = FVector::Dist2D(Loc, EA.PrevLocation);
				const UCharacterMovementComponent* CMC = E->GetCharacterMovement();
				if (Moved > 1.f && Moved < 400.f && CMC && CMC->IsMovingOnGround())
				{
					EA.StepAccum += Moved;
					const bool bFast = !JRAudio::IsCalmState(State);
					if (EA.StepAccum >= (bFast ? 120.f : 85.f))
					{
						EA.StepAccum = 0.f;
						PlayAt(TEXT("Zombie.Step"), Loc - FVector(0.f, 0.f, E->GetSimpleCollisionHalfHeight()), bFast ? 0.9f : 0.6f);
					}
				}
			}
		}
		EA.PrevState = State;
		EA.PrevLocation = Loc;
	}
	EngagedNearCount = EngagedClose;
	// Gemido de um zumbi calmo qualquer e rosnados de quem persegue, de tempos em tempos.
	if (Calm.Num() > 0 && Now >= NextMoanTime)
	{
		PlayAt(TEXT("Zombie.Moan"), Calm[Rand.RandRange(0, Calm.Num() - 1)]->GetActorLocation());
		NextMoanTime = Now + Rand.FRandRange(2.0f, 5.0f);
	}
	if (Engaged.Num() > 0 && Now >= NextChaseGrowlTime)
	{
		PlayAt(TEXT("Zombie.Growl"), Engaged[Rand.RandRange(0, Engaged.Num() - 1)]->GetActorLocation(), 0.7f);
		NextChaseGrowlTime = Now + Rand.FRandRange(2.5f, 5.0f);
	}
}

void UJRAudioSubsystem::HandleEnemyDied(AJREnemyCharacter* Enemy)
{
	if (Enemy && FVector::DistSquared(Enemy->GetActorLocation(), ListenerLocation) < FMath::Square(SoundBank ? SoundBank->ZombieVoiceRadius : 5000.f))
	{
		PlayAt(TEXT("Zombie.Death"), Enemy->GetActorLocation());
	}
}

void UJRAudioSubsystem::HandleEnemyHealthChanged(UJRHealthComponent* HealthComp, float NewHealth, float Delta)
{
	const AActor* Owner = HealthComp ? HealthComp->GetOwner() : nullptr;
	if (Owner && Delta < 0.f && NewHealth > 0.f && Rand.FRand() < 0.7f
		&& FVector::DistSquared(Owner->GetActorLocation(), ListenerLocation) < FMath::Square(4000.f))
	{
		PlayAt(TEXT("Zombie.Pain"), Owner->GetActorLocation());
	}
}

// ===================================================================== mundo, diretor, fase

void UJRAudioSubsystem::HandleGateOpened(AJRBlockingGate* Gate)
{
	if (Gate)
	{
		PlayAt(TEXT("World.Gate.Open"), Gate->GetActorLocation());
	}
}

void UJRAudioSubsystem::HandleDirectorPhaseChanged(EJRDirectorPhase OldPhase, EJRDirectorPhase NewPhase)
{
	if (const UWorld* W = GetWorld())
	{
		UpdateMusic(W->GetRealTimeSeconds());
	}
}

void UJRAudioSubsystem::HandleHordeTriggered(FName Reason, int32 Size)
{
	Play2D(TEXT("Zombie.Horde"));
}

void UJRAudioSubsystem::HandleStageChanged(EJRLevelStage OldStage, EJRLevelStage NewStage)
{
	const UWorld* W = GetWorld();
	const double Now = W ? W->GetRealTimeSeconds() : 0.0;
	if (NewStage == EJRLevelStage::Completed)
	{
		bLevelEnded = true;
		PlayStinger(JRAudio::MusicVictory, 1000.f);
		return;
	}
	if (NewStage == EJRLevelStage::Failed)
	{
		if (Now > MusicHoldUntil - 5.0) // a morte do herói já tocou a derrota
		{
			PlayStinger(JRAudio::MusicDefeat, 9.f);
		}
		return;
	}
	if (NewStage != EJRLevelStage::NotStarted && Now - LastObjectiveSoundTime > 1.0)
	{
		LastObjectiveSoundTime = Now;
		Play2D(TEXT("UI.Objective"));
	}
	UpdateMusic(Now);
}

void UJRAudioSubsystem::HandleCheckpointReached(AJRCheckpoint* Checkpoint)
{
	const double Now = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
	if (Now - LastObjectiveSoundTime > 1.0)
	{
		LastObjectiveSoundTime = Now;
		Play2D(TEXT("UI.Objective"));
	}
}

void UJRAudioSubsystem::UpdateMusic(double Now)
{
	if (!SoundBank || bLevelEnded || Now < MusicHoldUntil)
	{
		return;
	}
	EJRLevelStage Stage = EJRLevelStage::NotStarted;
	if (const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Stage = Objective->GetStage();
	}
	FName Want = JRAudio::MusicExplore;
	const AJRAIDirector* D = Director.Get();
	const bool bPeak = D && D->IsDirectorEnabled() && D->GetPhase() == EJRDirectorPhase::Peak;
	if (Stage == EJRLevelStage::FinalHorde || bPeak)
	{
		Want = JRAudio::MusicHorde;
	}
	else if ((D && D->GetPhase() == EJRDirectorPhase::BuildUp && D->GetIntensity() >= SoundBank->TensionIntensity)
		|| EngagedNearCount >= SoundBank->TensionEngagedCount)
	{
		Want = JRAudio::MusicTension;
	}
	if (Want == CurrentMusicId)
	{
		return;
	}
	const bool bFirst = CurrentMusicId.IsNone();
	if (bFirst || Want == JRAudio::MusicHorde || Now - LastMusicSwitchTime >= SoundBank->MusicMinHoldSeconds)
	{
		PlayMusic(Want, Want == JRAudio::MusicHorde ? 1.5f : SoundBank->MusicCrossfadeSeconds);
	}
}

// ===================================================================== ambiente

void UJRAudioSubsystem::UpdateAmbienceTargets(double Now)
{
	AmbienceTargets.Reset();
	for (int32 i = 0; i < SoundBank->BaseAmbienceIds.Num(); ++i)
	{
		const float Vol = SoundBank->BaseAmbienceVolumes.IsValidIndex(i) ? SoundBank->BaseAmbienceVolumes[i] : 1.f;
		float& T = AmbienceTargets.FindOrAdd(SoundBank->BaseAmbienceIds[i]);
		T = FMath::Max(T, Vol);
	}
	float BestWeight = 0.f;
	float BestExtraWeight = 0.f;
	FName BestSurface = NAME_None;
	FName BestExtra = NAME_None;
	float BestExtraChance = 0.f;
	float Thunder = 0.f;
	for (const FJRAmbienceZone& Z : SoundBank->AmbienceZones)
	{
		if (!Z.MapName.IsNone() && Z.MapName != CurrentMapName)
		{
			continue;
		}
		const float Weight = JRAudio::ZoneWeight(static_cast<float>(FVector::Dist2D(ListenerLocation, Z.Center)), Z.Radius, SoundBank->ZoneFadeFactor);
		if (Weight <= 0.f)
		{
			continue;
		}
		for (int32 k = 0; k < Z.LoopIds.Num(); ++k)
		{
			const float Vol = Z.LoopVolumes.IsValidIndex(k) ? Z.LoopVolumes[k] : 1.f;
			float& T = AmbienceTargets.FindOrAdd(Z.LoopIds[k]);
			T = FMath::Max(T, Weight * Vol);
		}
		if (!Z.FootSurface.IsNone() && Weight > BestWeight)
		{
			BestWeight = Weight;
			BestSurface = Z.FootSurface;
		}
		// Ponte etc.: só valendo de verdade (dentro do raio).
		if (!Z.FootExtraId.IsNone() && Weight >= 1.f && Weight >= BestExtraWeight)
		{
			BestExtraWeight = Weight;
			BestExtra = Z.FootExtraId;
			BestExtraChance = Z.FootExtraChance;
		}
		Thunder = FMath::Max(Thunder, Weight * Z.ThunderWeight);
	}
	ZoneSurface = BestWeight >= 0.5f ? BestSurface : FName(NAME_None);
	ZoneFootExtraId = BestExtra;
	ZoneFootExtraChance = BestExtraChance;
	ZoneThunderWeight = Thunder;
	// Loops que saíram da lista vão para zero (o UpdateAmbienceLevels desliga).
	for (const TPair<FName, float>& Pair : AmbienceLevels)
	{
		AmbienceTargets.FindOrAdd(Pair.Key);
	}
	if (Now >= NextThunderTime)
	{
		NextThunderTime = Now + Rand.FRandRange(SoundBank->ThunderMinInterval, FMath::Max(SoundBank->ThunderMinInterval, SoundBank->ThunderMaxInterval));
		const float Vol = SoundBank->ThunderBaseVolume + ZoneThunderWeight;
		if (Vol > 0.01f)
		{
			Play2D(TEXT("Amb.Thunder"), Vol, Rand.FRandRange(0.85f, 1.1f));
		}
	}
}

void UJRAudioSubsystem::UpdateAmbienceLevels(float RealDelta)
{
	for (const TPair<FName, float>& Pair : AmbienceTargets)
	{
		float& Level = AmbienceLevels.FindOrAdd(Pair.Key);
		Level = FMath::FInterpConstantTo(Level, Pair.Value, RealDelta, 0.4f);
		UpdateLoopSlot(AmbienceLoops.FindOrAdd(Pair.Key), Pair.Key, Level, nullptr);
	}
}

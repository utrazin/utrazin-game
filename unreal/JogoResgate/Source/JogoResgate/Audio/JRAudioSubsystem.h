// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Engine/EngineTypes.h"
#include "AI/JRAIDirector.h"
#include "AI/JREnemyStateLogic.h"
#include "Combat/JRInventoryComponent.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "Vehicles/JRZombieCarTypes.h"
#include "JRAudioSubsystem.generated.h"

class AActor;
class ACharacter;
class AJRBlockingGate;
class AJRCharacter;
class AJRCheckpoint;
class AJREnemyCharacter;
class AJRVehiclePawn;
class APawn;
class UAudioComponent;
class UJRHealthComponent;
class UJRSoundBank;
class USceneComponent;
class USoundAttenuation;
class USoundBase;
struct FJRSoundEntry;

/** Loops de um carro (componentes presos no carro; o carro é o dono). */
USTRUCT()
struct FJRVehicleAudio
{
	GENERATED_BODY()

	TWeakObjectPtr<AJRVehiclePawn> Vehicle;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Engine;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Skid;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Nitro;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Fire;

	FVector PrevVelocity = FVector::ZeroVector;
	FName PrevPendingItem;
	float EnginePitch = 0.8f;
	float SkidLevel = 0.f;
	float AirTime = 0.f;
	float FallSpeed = 0.f;
	double LastImpactTime = -10.0;
	double LastScrapeTime = -10.0;
	double NextNailsTime = 0.0;
	uint8 FlatMask = 0;
	bool bNitroWasActive = false;
	bool bFuelReserveWarned = false; // [A-075] alerta da reserva tocou (rearma ao abastecer)
};

/** Estado de áudio de um zumbi (só C++). */
struct FJREnemyAudio
{
	TWeakObjectPtr<AJREnemyCharacter> Enemy;
	FVector PrevLocation = FVector::ZeroVector;
	EJREnemyState PrevState = EJREnemyState::Idle;
	float StepAccum = 0.f;
	double NextVoiceTime = 0.0;
	double NextAttackTime = 0.0;
	bool bEliteKnown = false;
	bool bElite = false;
};

/** Um som resolvido do banco, pronto para tocar. */
struct FJRSoundPick
{
	USoundBase* Sound = nullptr;
	USoundAttenuation* Attenuation = nullptr;
	float Volume = 1.f;
	float Pitch = 1.f;
};

/**
 * Áudio do jogo (Etapa 10, A-061): banco de sons (/Game/Audio/DA_SoundBank), música com crossfade guiada
 * pelo AJRAIDirector e pelo fim da fase, ambiente por zona, motor/derrapagem/nitro/fogo do carro, passos,
 * vozes dos zumbis, interface (roda de itens, toasts, objetivo).
 *
 * Quase tudo vem de delegates que já existiam (diretor, objetivo, carro x zumbi, vida, bolsa, portão, pouso)
 * e de leitura do estado público (velocidade/RPM do carro, roda de itens, estado dos zumbis); só pickups,
 * baú, barril, espinhos, rádio da história e toast ganharam uma linha marcada "[Áudio/A-061]".
 *
 * Tick: justificado. O tom do motor e a derrapagem precisam ser suaves a cada quadro, os passos dependem
 * da distância andada e a roda de itens roda em câmera lenta (timers ficariam 4x mais lentos). As partes
 * pesadas (zumbis, ambiente, música) rodam em fatias de 0,1 s e 0,25 s.
 */
UCLASS()
class JOGORESGATE_API UJRAudioSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	static UJRAudioSubsystem* Get(const UObject* WorldContext);

	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** Toca um som do banco sem posição (interface, música curta). False se o id não existe ou está em espera. */
	bool Play2D(FName Id, float VolumeMultiplier = 1.f, float PitchMultiplier = 1.f);

	/** Toca um som do banco num ponto do mundo (3D, com a atenuação do som). */
	bool PlayAt(FName Id, const FVector& Location, float VolumeMultiplier = 1.f, float PitchMultiplier = 1.f);

	/** Toca preso a um componente (acompanha o movimento). */
	UAudioComponent* PlayAttached(FName Id, USceneComponent* AttachTo, FName Socket = NAME_None, float VolumeMultiplier = 1.f);

	/** Troca a música com crossfade (NAME_None = silêncio). Não faz nada se já é a música atual. */
	void PlayMusic(FName Id, float FadeSeconds);

	/** Para a música e toca um trecho curto (vitória/derrota). HoldSeconds = tempo sem música de fundo depois. */
	void PlayStinger(FName Id, float HoldSeconds);

	/** Chamado pelo AJRHUD::ShowToast: bipe curto 0,05 s depois, a menos que outro som 2D (pegar item, baú) toque junto. */
	void NotifyToast();

	UJRSoundBank* GetBank() const { return SoundBank; }

protected:
	// ---- carga e ligações
	void LoadBank();
	void BindWorldActors();
	void HandleActorSpawned(AActor* Actor);
	void BindVehicle(AJRVehiclePawn* Vehicle);
	void BindEnemy(AJREnemyCharacter* Enemy);
	void BindGate(AJRBlockingGate* Gate);
	void BindDirector();
	void BindHero(AJRCharacter* Hero);
	void UnbindHero();
	void SpawnEmitters();

	// ---- resolução de sons
	const FJRSoundEntry* FindEntry(FName Id, float* OutCategoryScale = nullptr) const;
	bool Resolve(FName Id, bool bCheckLimits, FJRSoundPick& Out);
	UAudioComponent* CreateLoop(FName Id, USceneComponent* AttachTo);
	/** Liga/desliga e ajusta um loop guardado em Slot (Level 0 = para). AttachTo nulo = 2D. */
	void UpdateLoopSlot(TObjectPtr<UAudioComponent>& Slot, FName Id, float Level, USceneComponent* AttachTo, float Pitch = 1.f);

	// ---- atualizações
	void UpdatePlayerPawn();
	void OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn);
	void UpdateHero(AJRCharacter* Hero, float DeltaTime);
	void PlayFootstep(AJRCharacter* Hero, float Speed2D);
	void UpdateItemWheel(AJRCharacter* Hero);
	void UpdateLowHealth(float RealDelta);
	void UpdateVehiclesFast(float DeltaTime);
	void UpdateVehiclesSlow(double Now);
	void UpdateEnemies(double Now);
	void UpdateAmbienceTargets(double Now);
	void UpdateAmbienceLevels(float RealDelta);
	void UpdateMusic(double Now);
	FJRVehicleAudio* FindVehicleAudio(const AActor* Vehicle);

	// ---- delegates
	UFUNCTION()
	void HandleZombieCarEvent(EJRZombieCarEvent Event, AActor* Zombie, FVector Location, float Value);

	UFUNCTION()
	void HandleVehicleHit(AActor* SelfActor, AActor* OtherActor, FVector NormalImpulse, const FHitResult& Hit);

	UFUNCTION()
	void HandleEnemyDied(AJREnemyCharacter* Enemy);

	UFUNCTION()
	void HandleEnemyHealthChanged(UJRHealthComponent* HealthComp, float NewHealth, float Delta);

	UFUNCTION()
	void HandleGateOpened(AJRBlockingGate* Gate);

	UFUNCTION()
	void HandleDirectorPhaseChanged(EJRDirectorPhase OldPhase, EJRDirectorPhase NewPhase);

	UFUNCTION()
	void HandleHordeTriggered(FName Reason, int32 Size);

	UFUNCTION()
	void HandleStageChanged(EJRLevelStage OldStage, EJRLevelStage NewStage);

	UFUNCTION()
	void HandleCheckpointReached(AJRCheckpoint* Checkpoint);

	UFUNCTION()
	void HandleHeroLanded(const FHitResult& Hit);

	UFUNCTION()
	void HandleHeroMovementModeChanged(ACharacter* Character, EMovementMode PrevMovementMode, uint8 PreviousCustomMode);

	UFUNCTION()
	void HandleHeroHealthChanged(UJRHealthComponent* HealthComp, float NewHealth, float Delta);

	UFUNCTION()
	void HandleHeroDeath(UJRHealthComponent* HealthComp, AActor* Killer);

	UFUNCTION()
	void HandleInventoryChanged(EJRConsumable Item, int32 NewCount);

private:
	UPROPERTY(Transient)
	TObjectPtr<UJRSoundBank> SoundBank;

	/** Sons/atenuações pré-carregados (mantém vivos enquanto a fase roda). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UObject>> LoadedAssets;

	UPROPERTY(Transient)
	TObjectPtr<USoundAttenuation> DefaultAttenuationAsset;

	UPROPERTY(Transient)
	TArray<FJRVehicleAudio> Vehicles;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> MusicA;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> MusicB;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> LowHealthLoop;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UAudioComponent>> AmbienceLoops;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UAudioComponent>> EmitterLoops;

	UPROPERTY(Transient)
	TArray<TObjectPtr<USoundAttenuation>> EmitterAttenuations;

	TMap<FName, int32> SoundIndex;
	TArray<float> SoundCategoryScale;
	TMap<FName, double> LastPlayTime;
	TMap<FName, int32> LastVariation;
	TArray<double> RecentZombieVoices;
	TArray<FJREnemyAudio> Enemies;
	TMap<FName, float> AmbienceTargets;
	TMap<FName, float> AmbienceLevels;

	TWeakObjectPtr<APawn> PlayerPawn;
	TWeakObjectPtr<AJRCharacter> BoundHero;
	TWeakObjectPtr<AJRAIDirector> Director;
	FDelegateHandle ActorSpawnedHandle;
	FRandomStream Rand;
	FVector ListenerLocation = FVector::ZeroVector;

	FName CurrentMusicId;
	FName CurrentMapName;
	FName ZoneSurface;
	FName ZoneFootExtraId;
	float ZoneFootExtraChance = 0.f;
	float ZoneThunderWeight = 0.f;
	float HeroStepAccum = 0.f;
	float LastHeroVz = 0.f;
	float LowHealthLevel = 0.f;
	int32 InventoryCounts[3] = { 0, 0, 0 };
	int32 EngagedNearCount = 0;
	int32 WheelHighlight = -1;
	int32 WheelTab = -1;
	double LastRealTime = 0.0;
	double NextEnemyUpdate = 0.0;
	double NextSlowUpdate = 0.0;
	double NextMoanTime = 0.0;
	double NextChaseGrowlTime = 0.0;
	double NextThunderTime = 0.0;
	double LastMusicSwitchTime = -100.0;
	double MusicHoldUntil = 0.0;
	double Last2DSoundTime = -10.0;
	double LastObjectiveSoundTime = -10.0;
	double ToastRequestTime = 0.0;
	bool bStarted = false;
	bool bWarnedNoBank = false;
	bool bWheelOpen = false;
	bool bLevelEnded = false;
	bool bToastPending = false;
};

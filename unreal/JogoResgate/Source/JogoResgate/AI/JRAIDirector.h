// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "JRAIDirector.generated.h"

class AJREnemyCharacter;
class UBoxComponent;
class UJRHealthComponent;
class UJRVehicleDamageComponent;

/** Fases do diretor (ritmo estilo Left 4 Dead). */
UENUM(BlueprintType)
enum class EJRDirectorPhase : uint8
{
	/** Subida: pequenos grupos de tempos em tempos; a tensão sobe. */
	BuildUp UMETA(DisplayName = "Subida"),
	/** Pico: horda por ~60 s. */
	Peak UMETA(DisplayName = "Pico"),
	/** Calmaria: nada nasce por 30 a 45 s. */
	Relax UMETA(DisplayName = "Calmaria")
};

/** Um tipo de inimigo e seu peso no sorteio (melee comum, arqueiro/atirador às vezes, elite raro). */
USTRUCT(BlueprintType)
struct FJRDirectorEnemyEntry
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director")
	TSubclassOf<AJREnemyCharacter> EnemyClass;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director", meta = (ClampMin = "0"))
	float Weight = 1.f;

	/** Máximo vivo deste tipo criado pelo diretor ao mesmo tempo (0 = sem limite). Ex.: elite 1. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director", meta = (ClampMin = "0"))
	int32 MaxAlive = 0;
};

/** Ajustes do diretor. Intensidade vai de 0 (calmo) a 1 (jogador sobrecarregado). */
USTRUCT(BlueprintType)
struct FJRDirectorSettings
{
	GENERATED_BODY()

	// ---- Intensidade

	/** Intensidade por ponto de vida perdido pelo herói (100 de vida perdida = +0,8). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "0"))
	float DamageToIntensity = 0.008f;

	/** Intensidade por fração de integridade perdida pelo carro (0,1 de integridade = +0,15). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "0"))
	float VehicleDamageToIntensity = 1.5f;

	/** Intensidade por zumbi morto perto do jogador. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "0"))
	float KillIntensity = 0.03f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (Units = "cm"))
	float KillNearRadius = 2500.f;

	/** Zumbis vivos dentro deste raio contam como "em cima do jogador". */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (Units = "cm"))
	float NearbyRadius = 1500.f;

	/** Por segundo, por zumbi dentro de NearbyRadius (conta no máximo NearbyMaxCount). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "0"))
	float NearbyIntensityPerSecond = 0.003f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "1"))
	int32 NearbyMaxCount = 8;

	/** Por segundo com zumbi perseguindo/atacando/agarrado perto (em combate). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "0"))
	float CombatIntensityPerSecond = 0.01f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (Units = "cm"))
	float CombatRadius = 2000.f;

	/** Queda por segundo fora de combate e sem zumbi perto (na Calmaria usa RelaxDecayPerSecond). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "0"))
	float DecayPerSecond = 0.03f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Intensity", meta = (ClampMin = "0"))
	float RelaxDecayPerSecond = 0.06f;

	// ---- Fases

	/** Subida vira Pico quando a intensidade passa disto (depois de MinBuildUpTime)... */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (ClampMin = "0", ClampMax = "1"))
	float PeakTriggerIntensity = 0.6f;

	/** Tempo mínimo de Subida antes que a intensidade possa chamar um Pico. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (Units = "s"))
	float MinBuildUpTime = 45.f;

	/** ...ou depois deste tempo de Subida (sempre acontece horda). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (Units = "s"))
	float MaxBuildUpTime = 150.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (Units = "s"))
	float PeakDuration = 60.f;

	/** O Pico não acaba cedo antes deste tempo, mesmo com intensidade alta. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (Units = "s"))
	float PeakMinDuration = 30.f;

	/** Intensidade "muito alta": na Subida vai direto para a Calmaria; no Pico (depois de PeakMinDuration) encerra a horda. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (ClampMin = "0", ClampMax = "1"))
	float RelaxTriggerIntensity = 0.9f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (Units = "s"))
	float RelaxMinTime = 30.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (Units = "s"))
	float RelaxMaxTime = 45.f;

	/** Espera antes do primeiro grupo da Subida. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Phases", meta = (Units = "s"))
	float FirstSpawnDelay = 8.f;

	// ---- Spawns

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "s"))
	float BuildUpMinInterval = 20.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "s"))
	float BuildUpMaxInterval = 40.f;

	/** Dirigindo, os intervalos da Subida são multiplicados por isto (o carro passa rápido pelos grupos). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "0.1", ClampMax = "1"))
	float DrivingIntervalScale = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "1"))
	int32 BuildUpMinGroup = 1;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "1"))
	int32 BuildUpMaxGroup = 4;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "s"))
	float PeakMinInterval = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "s"))
	float PeakMaxInterval = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "1"))
	int32 PeakMinGroup = 3;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "1"))
	int32 PeakMaxGroup = 6;

	/** Sem ponto válido: tenta de novo depois disto (em vez de esperar o intervalo inteiro). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "s"))
	float RetryDelay = 4.f;

	/** A pé: anel em volta do jogador. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float OnFootMinDistance = 2500.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float OnFootMaxDistance = 6000.f;

	/** Dirigindo: à frente do carro, na direção em que ele anda. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float DrivingMinDistance = 6000.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float DrivingMaxDistance = 15000.f;

	/** Desvio para o lado da linha do carro (mínimo e máximo): nascem na beira e cruzam a estrada. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float DrivingLateralMin = 800.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float DrivingLateralMax = 3000.f;

	/** Abaixo desta velocidade (cm/s; 300 = ~11 km/h) o carro conta como parado (usa o anel em volta, como a pé). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "0"))
	float DrivingMinSpeed = 300.f;

	/** Horda disparada por evento com local: anel em volta do ponto do evento. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float EventHordeMinDistance = 1500.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float EventHordeMaxDistance = 4000.f;

	/** Meio-ângulo à frente da câmera em que só nasce se algo tapar a visão (usa o FOV da câmera + 10° se for maior). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "0", ClampMax = "180"))
	float HiddenConeHalfAngle = 60.f;

	/** Teto de inimigos vivos NO MAPA (inclui os colocados à mão) na Subida / no Pico. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "0"))
	int32 MaxAliveBuildUp = 25;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (ClampMin = "0"))
	int32 MaxAlivePeak = 40;

	/** Some com zumbis do diretor mais longe que isto e fora da visão (reciclagem do orçamento). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns", meta = (Units = "cm"))
	float DespawnDistance = 18000.f;

	/** Recicla também zumbis colocados à mão (longe, fora da visão e ATRÁS do jogador). Desligado: o elite da escopeta é colocado à mão. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Spawns")
	bool bRecycleHandPlaced = false;
};

/**
 * Zona do diretor (caixa): o level designer marca o acampamento, o posto de gasolina etc.
 * Zona segura (bNoSpawns): nada nasce DENTRO dela e, com o jogador dentro, o diretor não cria grupos.
 * Com o jogador dentro, a zona de maior Priority também muda a densidade e as classes permitidas.
 */
UCLASS()
class JOGORESGATE_API AJRDirectorZone : public AActor
{
	GENERATED_BODY()

public:
	AJRDirectorZone();

	/** O ponto está dentro da caixa (respeita rotação e escala)? */
	UFUNCTION(BlueprintPure, Category = "Director Zone")
	bool ContainsPoint(const FVector& Point) const;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Director Zone")
	TObjectPtr<UBoxComponent> Box;

	/** Zona segura: nenhum zumbi nasce aqui dentro; com o jogador dentro, sem grupos nem hordas automáticas. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director Zone")
	bool bNoSpawns = false;

	/** Zona segura bloqueia também hordas de evento (TriggerHorde) enquanto o jogador estiver dentro. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director Zone")
	bool bBlockEventHordes = false;

	/** Multiplica o tamanho dos grupos e os tetos de vivos (0,5 = metade; 2 = o dobro). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director Zone", meta = (ClampMin = "0"))
	float DensityMultiplier = 1.f;

	/** Multiplica a queda da intensidade (zona segura: 2 = o jogador "respira" mais rápido). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director Zone", meta = (ClampMin = "0"))
	float IntensityDecayMultiplier = 1.f;

	/** Só estas classes nascem com o jogador dentro (vazio = as da tabela da fase). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director Zone")
	TArray<TSubclassOf<AJREnemyCharacter>> AllowedClasses;

	/** Zonas sobrepostas: vale a de maior prioridade. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Director Zone")
	int32 Priority = 0;
};

/** Ponto de vista do jogador, calculado uma vez por atualização do diretor (não é UPROPERTY). */
struct FJRDirectorViewInfo
{
	FVector Location = FVector::ZeroVector;
	FVector Dir = FVector::ForwardVector;
	float CosHalfAngle = 0.5f;
	bool bValid = false;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnDirectorPhaseChanged, EJRDirectorPhase, OldPhase, EJRDirectorPhase, NewPhase);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnDirectorHorde, FName, Reason, int32, Size);

/**
 * Diretor de IA (estilo Left 4 Dead): mede a intensidade do jogador (dano recebido, mortes perto,
 * zumbis a menos de 15 m, tempo em combate; cai com o tempo) e alterna Subida -> Pico -> Calmaria.
 * Cria grupos fora da visão, a pé em volta do jogador (25 a 60 m) ou à frente do carro (60 a 150 m,
 * dos lados da linha de movimento), em pontos de navmesh com caminho até o jogador. Recicla os
 * zumbis do diretor que ficaram longe (180 m) e fora da visão. Substitui o AJRAmbientSpawner.
 * Coloque UM por mapa (tools/unreal/setup_ai_director.py). Sem Tick: timer de 0,5 s.
 * Debug: console "JRDiretor" (texto na tela), "jr.Director.Debug 1" ou bShowDebug no ator.
 */
UCLASS()
class JOGORESGATE_API AJRAIDirector : public AActor
{
	GENERATED_BODY()

public:
	AJRAIDirector();

	/** O diretor do mundo (o primeiro encontrado) ou nulo. */
	static AJRAIDirector* Find(const UObject* WorldContext);

	/**
	 * Começa uma horda agora em volta do jogador (portão, gerador, barulho).
	 * Duration <= 0 usa PeakDuration; Size = total de zumbis da horda (0 = sem limite, só os tetos).
	 */
	UFUNCTION(BlueprintCallable, Category = "Director")
	void TriggerHorde(FName Reason, float Duration = 60.f, int32 Size = 0);

	/** Igual a TriggerHorde, mas os zumbis vêm de perto de Location (ex.: o gerador que fez barulho). */
	UFUNCTION(BlueprintCallable, Category = "Director")
	void TriggerHordeAt(FName Reason, FVector Location, float Duration = 60.f, int32 Size = 0);

	/** Teste/script: muda de fase na hora (Pico = horda "Console"). */
	UFUNCTION(BlueprintCallable, Category = "Director")
	void ForcePhase(EJRDirectorPhase NewPhase);

	/** Soma intensidade (eventos de script). */
	UFUNCTION(BlueprintCallable, Category = "Director")
	void AddIntensity(float Amount);

	/** Chamado por AJREnemyCharacter ao morrer (qualquer inimigo, não só os do diretor). */
	void NotifyEnemyKilled(AJREnemyCharacter* Enemy);

	UFUNCTION(BlueprintPure, Category = "Director")
	EJRDirectorPhase GetPhase() const { return Phase; }

	UFUNCTION(BlueprintPure, Category = "Director")
	float GetIntensity() const { return Intensity; }

	/** Vivos criados pelo diretor. */
	UFUNCTION(BlueprintPure, Category = "Director")
	int32 GetDirectorAliveCount() const { return Spawned.Num(); }

	/** Ligado e no estágio certo da fase, ou numa horda de evento (os outros spawners cedem a vez quando true). */
	UFUNCTION(BlueprintPure, Category = "Director")
	bool IsActiveNow() const;

	UFUNCTION(BlueprintCallable, Category = "Director")
	void SetDirectorEnabled(bool bNewEnabled) { bEnabled = bNewEnabled; }

	UFUNCTION(BlueprintPure, Category = "Director")
	bool IsDirectorEnabled() const { return bEnabled; }

	/** Texto do diretor na tela (console "JRDiretor" / cvar jr.Director.Debug). */
	static bool IsDebugEnabled();
	static void SetDebugEnabled(bool bDebug);

	/** Uma linha de status (fase, intensidade, vivos) para o console/HUD. */
	FString GetStatusLine() const;

	/** Mudou de fase (para a música/áudio da Etapa 10). */
	UPROPERTY(BlueprintAssignable, Category = "Director")
	FJROnDirectorPhaseChanged OnDirectorPhaseChanged;

	/** Começou uma horda (automática "Ritmo", por evento, ou "Console"). Size 0 = sem limite. */
	UPROPERTY(BlueprintAssignable, Category = "Director")
	FJROnDirectorHorde OnHordeTriggered;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** Mesmo momento do OnDirectorPhaseChanged, para quem fizer um Blueprint filho do diretor. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Director", meta = (DisplayName = "On Phase Changed"))
	void ReceivePhaseChanged(EJRDirectorPhase OldPhase, EJRDirectorPhase NewPhase);

	void UpdateDirector();
	void UpdateIntensity(const APawn* Player, float DeltaSeconds, const AJRDirectorZone* Zone);
	void SetPhase(EJRDirectorPhase NewPhase, float Duration = 0.f);
	void StartPeak(FName Reason, const FVector& Location, float Duration, int32 Size);
	void ScheduleNextSpawn();
	/** Retorna quantos nasceram; -1 se não achou ponto (tenta de novo logo). */
	int32 SpawnGroup(const APawn* Player, int32 Count, const AJRDirectorZone* Zone);
	bool FindSpawnPoint(const APawn* Player, bool bUseHordeFocus, const FJRDirectorViewInfo& View, FVector& OutPoint);
	FJRDirectorViewInfo GetViewInfo(const APawn* Player) const;
	bool IsHiddenFromView(const FJRDirectorViewInfo& View, const FVector& Point, const AActor* IgnoreA, const AActor* IgnoreB) const;
	TSubclassOf<AJREnemyCharacter> PickEnemyClass(const AJRDirectorZone* Zone);
	int32 CountSpawnedOfClass(const UClass* Cls) const;
	const AJRDirectorZone* FindZoneAt(const FVector& Point) const;
	bool IsInNoSpawnZone(const FVector& Point) const;
	void BindPlayerPawn(APawn* Player);
	void RecycleFarEnemies(const APawn* Player);
	void DrawDebug() const;

	UFUNCTION()
	void HandlePlayerHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta);

	UFUNCTION()
	void HandleVehicleIntegrityChanged(float Integrity);

	UPROPERTY(EditAnywhere, Category = "Director")
	bool bEnabled = true;

	/** Mostra o status na tela mesmo sem o comando de console. */
	UPROPERTY(EditAnywhere, Category = "Director")
	bool bShowDebug = false;

	/** Aviso "Horda chegando!" no começo do Pico. */
	UPROPERTY(EditAnywhere, Category = "Director")
	bool bShowHordeToast = true;

	/** Estágios da fase em que o diretor trabalha (a horda final tem o AJRHordeDirector). */
	UPROPERTY(EditAnywhere, Category = "Director")
	TArray<EJRLevelStage> ActiveStages = { EJRLevelStage::Driving, EJRLevelStage::OnFoot };

	/** Sem sistema de objetivo (mapa de teste sem fase): trabalha mesmo assim. */
	UPROPERTY(EditAnywhere, Category = "Director")
	bool bActiveWithoutObjective = true;

	/** Sorteio na Subida (vazio = usa EnemyTable). */
	UPROPERTY(EditAnywhere, Category = "Director|Tables")
	TArray<FJRDirectorEnemyEntry> BuildUpTable;

	/** Sorteio no Pico; o elite (raro, MaxAlive 1) fica só aqui (vazio = usa EnemyTable). */
	UPROPERTY(EditAnywhere, Category = "Director|Tables")
	TArray<FJRDirectorEnemyEntry> PeakTable;

	/** Tabela antiga/geral (usada pelos scripts build_l01.py e build_vehicle_test.py) quando a da fase está vazia. */
	UPROPERTY(EditAnywhere, Category = "Director|Tables")
	TArray<FJRDirectorEnemyEntry> EnemyTable;

	UPROPERTY(EditAnywhere, Category = "Director", meta = (ShowOnlyInnerProperties))
	FJRDirectorSettings Settings;

	UPROPERTY(EditAnywhere, Category = "Director", meta = (Units = "s"))
	float UpdateInterval = 0.5f;

private:
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Spawned;
	TWeakObjectPtr<APawn> BoundPawn;
	TWeakObjectPtr<UJRHealthComponent> BoundHealth;
	TWeakObjectPtr<UJRVehicleDamageComponent> BoundVehicleDamage;
	FString CurrentZoneName;
	FTimerHandle UpdateTimer;
	FRandomStream Random;
	EJRDirectorPhase Phase = EJRDirectorPhase::BuildUp;
	float Intensity = 0.f;
	float LastIntegrity = 1.f;
	float CombatTime = 0.f;
	int32 NearbyCount = 0;
	double PhaseStartTime = 0.0;
	double PhaseEndTime = 0.0;
	double NextSpawnTime = 0.0;
	double LastUpdateTime = 0.0;
	double LastRecycleTime = 0.0;
	double EventActiveUntil = -1.0;
	FVector HordeFocus = FVector::ZeroVector;
	FName HordeReason;
	/** Zumbis que ainda faltam nascer nesta horda (-1 = sem limite). */
	int32 HordeRemaining = -1;
	bool bHasHordeFocus = false;
	bool bWasActive = false;
	bool bPlayerDriving = false;
	int32 TotalSpawned = 0;
	int32 TotalRecycled = 0;
};

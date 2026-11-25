// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRArenaDirector.generated.h"

class AJRArenaGenerator;
class AJRArenaNest;
class AJRCharacter;
class AJREnemyCharacter;
class AJRExtractionShip;
class UJRHealthComponent;
class UJRRunSubsystem;

/** Um tipo de inimigo que o diretor pode "comprar" (REMAP 6.3). Energia e créditos do abate saem do custo. */
USTRUCT(BlueprintType)
struct FJRArenaEnemy
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Arena")
	FString Label;

	UPROPERTY(EditAnywhere, Category = "Arena")
	TSoftClassPtr<AJREnemyCharacter> EnemyClass;

	/** Custo no orçamento do diretor (comum 1, corredor 2, arqueiro 3, atirador 4, tanque 8). */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 Cost = 1;

	/** Começa a aparecer nesta onda. */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 FirstWave = 1;

	/** Peso no sorteio da compra. */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "0"))
	float Weight = 1.f;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 GroupMin = 1;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 GroupMax = 1;

	/** Vida x este valor (além da escala por nível). */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "0.1"))
	float HealthMultiplier = 1.f;

	/** Ritmo do inimigo (CustomTimeDilation): 1,35 = corredor, 0,85 = tanque lento. */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "0.5", ClampMax = "2"))
	float Pace = 1.f;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "0.5", ClampMax = "2"))
	float Scale = 1.f;
};

/** Objetivos sorteados por arena (REMAP 6.4). */
UENUM()
enum class EJRArenaObjective : uint8
{
	None,
	SurviveWaves,
	KillMarkedElite,
	DestroyNests,
	Combo
};

/** Um objetivo da arena e seu estado (plain C++, só o diretor usa). */
struct FJRArenaObjectiveState
{
	EJRArenaObjective Type = EJRArenaObjective::None;
	int32 Target = 0;
	int32 Progress = 0;
	int64 Reward = 0;
	bool bDone = false;
};

/** Um inimigo comprado, esperando a vez de nascer. */
struct FJRArenaPendingSpawn
{
	int32 EnemyIndex = 0;
	bool bElite = false;
	bool bMarked = false;
	FVector Location = FVector::ZeroVector;
	int32 Fails = 0;
	int32 PaidCost = 0;
};

/** Fase do ritmo de tensão dentro da onda. */
enum class EJRArenaPacing : uint8
{
	BuildUp,  // compra grupos até o pico
	Peak,     // segura as compras até a horda baixar
	Relax     // respiro curto
};

/**
 * [Remap F2] Diretor da arena procedural (REMAP 6.3 a 6.6).
 * Ondas sem fim do ponto de vista do jogador (anúncio, pausa curta, nave a cada 3 ondas com multiplicador), mas por
 * dentro cada onda é um orçamento: o diretor ganha pontos com o tempo (mais rápido em nível alto) e compra grupos
 * (comum 1, corredor 2, arqueiro 3, atirador 4, tanque 8; elite = custo x 6). Ritmo de tensão: junta pressão até um
 * pico, espera a horda baixar e dá um respiro curto (mais longo se o herói está com pouca vida).
 * Surgimento sempre fora da visão, anunciado por som de onde vem; elites com aviso e luz.
 * 2 objetivos por arena: "Sobreviva 3 ondas" + um opcional sorteado (elite marcado, 3 ninhos ou combo).
 * Pontos: do AJRArenaGenerator (se existir), senão atores com tag "ArenaSpawn"/"ArenaExtracao", senão navmesh.
 * Cartas, energia e créditos continuam como no F1.
 */
UCLASS()
class JOGORESGATE_API AJRArenaDirector : public AActor
{
	GENERATED_BODY()

public:
	AJRArenaDirector();

	virtual void Tick(float DeltaSeconds) override;

	/** Chamado pela HUD: escolheu a carta Index (0..2). */
	void ConfirmCard(int32 Index);

	/** Chamado pela nave: sai da arena com o multiplicador. */
	void Extract(float Multiplier);

	/** A nave foi embora sem o herói. */
	void HandleShipLeft(AJRExtractionShip* Ship);

	/** O herói morreu: para tudo (o GameMode cuida da corrida e da volta para a cidade). */
	void StopArena();

	// ---------------- leitura (HUD)
	AJRExtractionShip* GetActiveShip() const { return ActiveShip.Get(); }
	int32 GetAliveCount() const { return Alive.Num(); }
	/** Inimigos vivos + na fila + estimativa do que o diretor ainda vai comprar nesta onda. */
	int32 GetEnemiesLeftInWave() const;
	bool IsInBreak() const { return bInBreak; }
	float GetBreakSecondsLeft() const;
	bool IsEnded() const { return bEnded; }

	/** Texto do objetivo atual (o opcional enquanto não cumprido, depois o principal). Vazio se nenhum. */
	FString GetObjectiveLine() const;
	/** Progresso 0..1 do objetivo da GetObjectiveLine; negativo se não há objetivo ou progresso. */
	float GetObjectiveProgress() const;

	static AJRArenaDirector* FindInWorld(const UObject* WorldContext);

protected:
	virtual void BeginPlay() override;

	void PrepareHero();
	void BeginWave(int32 WaveNumber);
	void DirectorTick();
	void FinishWave();
	bool TryBuyGroup();
	bool SpawnPending(FJRArenaPendingSpawn& Entry);
	bool PickSpawnLocation(FVector& OutLocation, bool bPreferNest) const;
	bool IsHiddenFromPlayer(const FVector& Location) const;
	int32 RemainingWaveBudget() const;
	int32 CostOfEntry(int32 EnemyIndex, bool bElite) const;
	void AnnounceGroup(const FVector& Location, bool bElite, bool bMarked, int32 GroupCost);
	FString DirectionFromHero(const FVector& Location) const;
	void MakeElite(AJREnemyCharacter* Enemy, bool bMarked) const;
	void SetupObjectives();
	void CompleteObjective(FJRArenaObjectiveState& Objective);
	FString DescribeObjective(const FJRArenaObjectiveState& Objective) const;
	void SpawnNests();
	void SpawnShip();
	void OpenCardChoice();
	void Shockwave(AJRCharacter* Hero);
	void ReturnToCity();

	UFUNCTION()
	void HandleEnemyDied(AJREnemyCharacter* Enemy);

	UFUNCTION()
	void HandleHeroHealthChanged(UJRHealthComponent* ChangedHealth, float NewHealth, float Delta);

	UFUNCTION()
	void HandleNestDestroyed(UJRHealthComponent* DeadHealth, AActor* Killer);

	AJRCharacter* GetHero() const;
	UJRRunSubsystem* GetRun() const;
	int32 GetSectorLevelSafe() const;

	/** Tipos de inimigo. O primeiro é o "padrão" (zumbi comum, usado quando algo falha). */
	UPROPERTY(EditAnywhere, Category = "Arena")
	TArray<FJRArenaEnemy> Enemies;

	// ---------------- diretor por créditos
	/** Elite = custo x este valor ("elite multiplica"). */
	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (ClampMin = "1"))
	int32 EliteCostMultiplier = 6;

	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (ClampMin = "1"))
	float EliteHealthMultiplier = 4.f;

	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (ClampMin = "1"))
	int32 EliteFirstWave = 4;

	/** Chance de virar elite quando o diretor está rico (carteira >= 3 x o preço do elite). */
	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (ClampMin = "0", ClampMax = "1"))
	float EliteChanceWhenRich = 0.45f;

	/** Carteira inicial de cada onda (fração do orçamento): o primeiro grupo chega logo. */
	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (ClampMin = "0", ClampMax = "1"))
	float WaveStartWallet = 0.35f;

	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (Units = "s"))
	float RelaxSeconds = 3.f;

	/** Respiro extra quando o herói está com menos de 40% de vida. */
	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (Units = "s"))
	float MercySeconds = 2.5f;

	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (Units = "s"))
	float DirectorInterval = 0.2f;

	UPROPERTY(EditAnywhere, Category = "Arena|Diretor", meta = (ClampMin = "1"))
	int32 MaxAlive = 30;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "s"))
	float FirstWaveDelay = 4.f;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "s"))
	float BreakBetweenWaves = 6.f;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "cm"))
	float MinSpawnDistance = 1400.f;

	/** Preferência: nascer até esta distância (chegam logo, mas fora da visão). */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "cm"))
	float PreferredMaxSpawnDistance = 4200.f;

	/** Raio usado para pontos aleatórios na navmesh quando não há gerador nem atores "ArenaSpawn". */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "cm"))
	float RandomSpawnRadius = 3800.f;

	UPROPERTY(EditAnywhere, Category = "Arena|Extracao", meta = (ClampMin = "1"))
	int32 ExtractionEveryWaves = 3;

	UPROPERTY(EditAnywhere, Category = "Arena|Extracao", meta = (Units = "s"))
	float ExtractionSeconds = 30.f;

	UPROPERTY(EditAnywhere, Category = "Arena|Extracao")
	TSubclassOf<AJRExtractionShip> ShipClass;

	/** Munição dada ao fim de cada onda (+ 5 por onda). */
	UPROPERTY(EditAnywhere, Category = "Arena")
	int32 AmmoPerWave = 25;

	UPROPERTY(EditAnywhere, Category = "Arena|Cartas", meta = (Units = "cm"))
	float ShockwaveRadius = 900.f;

	UPROPERTY(EditAnywhere, Category = "Arena|Cartas")
	float ShockwaveDamage = 35.f;

	UPROPERTY(EditAnywhere, Category = "Arena|Cartas", meta = (Units = "s"))
	float InvulnerableAfterCard = 1.5f;

	// ---------------- objetivos
	UPROPERTY(EditAnywhere, Category = "Arena|Objetivos", meta = (ClampMin = "1"))
	int32 SurviveWavesTarget = 3;

	/** Onda em que o elite marcado aparece. */
	UPROPERTY(EditAnywhere, Category = "Arena|Objetivos", meta = (ClampMin = "1"))
	int32 MarkedEliteWave = 2;

	UPROPERTY(EditAnywhere, Category = "Arena|Objetivos", meta = (ClampMin = "1"))
	int32 NestCount = 3;

	UPROPERTY(EditAnywhere, Category = "Arena|Objetivos")
	float NestBaseHealth = 260.f;

	/** Recompensa do principal e do opcional: x nível do setor. */
	UPROPERTY(EditAnywhere, Category = "Arena|Objetivos")
	int32 PrimaryRewardPerLevel = 80;

	UPROPERTY(EditAnywhere, Category = "Arena|Objetivos")
	int32 OptionalRewardPerLevel = 150;

	/** Nível do setor quando se dá Play direto na arena (sem passar pelo portão). */
	UPROPERTY(EditAnywhere, Category = "Arena")
	int32 DefaultSectorLevel = 1;

private:
	UPROPERTY()
	TArray<TSubclassOf<AJREnemyCharacter>> LoadedClasses;

	TArray<FVector> SpawnSpots;
	TArray<FVector> ExtractionSpots;
	TArray<FVector> ObjectiveSpots;
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Alive;
	TMap<TWeakObjectPtr<AJREnemyCharacter>, int32> CostOf;
	TWeakObjectPtr<AJREnemyCharacter> MarkedElite;
	TArray<TWeakObjectPtr<AJRArenaNest>> Nests;
	TWeakObjectPtr<AJRExtractionShip> ActiveShip;
	TWeakObjectPtr<AJRArenaGenerator> Generator;
	TArray<FJRArenaPendingSpawn> Pending;

	FJRArenaObjectiveState PrimaryObjective;
	FJRArenaObjectiveState OptionalObjective;

	FTimerHandle WaveTimer;
	FTimerHandle SpawnTimer;
	FTimerHandle HeroTimer;
	FTimerHandle ExitTimer;
	double BreakEndTime = 0.0;
	double RelaxEndTime = 0.0;
	double LastDirectorTime = 0.0;

	EJRArenaPacing Pacing = EJRArenaPacing::BuildUp;
	float Wallet = 0.f;
	/** [A-098] Próximo grupo já escolhido: o diretor junta a carteira até poder pagar (antes gastava cada ponto
	 *  assim que entrava e nunca chegava aos 8 do Tanque: 13 ondas só de zumbi comum). */
	int32 PlannedPick = INDEX_NONE;
	bool bPlannedElite = false;
	int32 PlannedCount = 0;
	bool bTankThisWave = false;
	int32 WaveBudget = 0;
	int32 WaveSpent = 0;
	int32 PeakCost = 0;
	int32 GroupsThisWave = 0;
	int32 Wave = 0;
	bool bMarkedEliteSpawned = false;
	bool bInBreak = true;
	bool bEnded = false;
	bool bChoiceOpen = false;
	bool bHeroReady = false;
};

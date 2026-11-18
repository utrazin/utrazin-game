// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRArenaDirector.generated.h"

class AJRCharacter;
class AJREnemyCharacter;
class AJRExtractionShip;
class UJRRunSubsystem;

/** Um tipo de inimigo da arena e quanto ele "custa" (energia e créditos saem do custo, REMAP 6.3). */
USTRUCT(BlueprintType)
struct FJRArenaEnemy
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Arena")
	TSoftClassPtr<AJREnemyCharacter> EnemyClass;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 Cost = 1;

	/** Começa a aparecer nesta onda. */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 FirstWave = 1;

	/** Chance de cada inimigo da onda ser deste tipo (o primeiro da lista fica com o que sobrar). */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "0", ClampMax = "1"))
	float Chance = 0.f;
};

/**
 * [Remap F1] Diretor da arena fixa do protótipo (REMAP 6.5 e 6.6): ondas sem fim cada vez mais fortes,
 * nave de extração a cada 3 ondas, energia por abate e escolha de 3 cartas ao subir de nível
 * (o jogo congela, escolhe com 1/2/3, sai uma onda de choque e 1,5 s sem levar dano).
 * Pontos de surgimento: atores com a tag "ArenaSpawn" (ou pontos aleatórios na navmesh, se não houver).
 * Pontos da nave: atores com a tag "ArenaExtracao". O F2 troca isto pelo gerador procedural + diretor por créditos.
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
	int32 GetEnemiesLeftInWave() const { return FMath::Max(0, WaveTotal - SpawnedInWave) + Alive.Num(); }
	bool IsInBreak() const { return bInBreak; }
	float GetBreakSecondsLeft() const;
	bool IsEnded() const { return bEnded; }

	static AJRArenaDirector* FindInWorld(const UObject* WorldContext);

protected:
	virtual void BeginPlay() override;

	void PrepareHero();
	void BeginWave(int32 WaveNumber);
	void SpawnTick();
	void FinishWave();
	bool PickSpawnLocation(FVector& OutLocation) const;
	bool IsHiddenFromPlayer(const FVector& Location) const;
	int32 PickEnemyIndex(bool bForceElite) const;
	void SpawnShip();
	void OpenCardChoice();
	void Shockwave(AJRCharacter* Hero);
	void ReturnToCity();

	UFUNCTION()
	void HandleEnemyDied(AJREnemyCharacter* Enemy);

	AJRCharacter* GetHero() const;
	UJRRunSubsystem* GetRun() const;

	/** Tipos de inimigo. O primeiro é o "padrão" (zumbi comum). */
	UPROPERTY(EditAnywhere, Category = "Arena")
	TArray<FJRArenaEnemy> Enemies;

	/** Índice em Enemies do elite que fecha toda onda múltipla de EliteEveryWaves (-1 = sem elite). */
	UPROPERTY(EditAnywhere, Category = "Arena")
	int32 EliteIndex = 3;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 EliteEveryWaves = 5;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 MaxAlive = 30;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "s"))
	float SpawnInterval = 0.5f;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "s"))
	float FirstWaveDelay = 4.f;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "s"))
	float BreakBetweenWaves = 5.f;

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "cm"))
	float MinSpawnDistance = 1400.f;

	/** Raio usado para pontos aleatórios na navmesh quando não há atores "ArenaSpawn". */
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

	/** Nível do setor quando se dá Play direto na arena (sem passar pelo portão). */
	UPROPERTY(EditAnywhere, Category = "Arena")
	int32 DefaultSectorLevel = 1;

private:
	UPROPERTY()
	TArray<TSubclassOf<AJREnemyCharacter>> LoadedClasses;

	TArray<TObjectPtr<AActor>> SpawnPoints;
	TArray<TObjectPtr<AActor>> ExtractionPoints;
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Alive;
	TMap<TWeakObjectPtr<AJREnemyCharacter>, int32> CostOf;
	TWeakObjectPtr<AJRExtractionShip> ActiveShip;

	FTimerHandle WaveTimer;
	FTimerHandle SpawnTimer;
	FTimerHandle HeroTimer;
	FTimerHandle ExitTimer;
	double BreakEndTime = 0.0;

	int32 Wave = 0;
	int32 WaveTotal = 0;
	int32 SpawnedInWave = 0;
	bool bInBreak = true;
	bool bEnded = false;
	bool bChoiceOpen = false;
	bool bHeroReady = false;
};

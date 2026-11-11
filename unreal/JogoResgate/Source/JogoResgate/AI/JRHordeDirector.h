// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRHordeDirector.generated.h"

class AJREnemyCharacter;
class UBoxComponent;

/** Uma onda da horda. */
USTRUCT(BlueprintType)
struct FJRWave
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wave")
	TSubclassOf<AJREnemyCharacter> EnemyClass;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wave", meta = (ClampMin = "1"))
	int32 Count = 6;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wave", meta = (Units = "s"))
	float SpawnInterval = 1.f;

	/** Pausa antes da próxima onda. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wave", meta = (Units = "s"))
	float DelayAfterWave = 4.f;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnWaveStarted, int32, WaveIndex, int32, TotalWaves);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FJROnHordeCompleted);

/**
 * Diretor de ondas (GDD 8.2). Ativado quando o jogador entra no gatilho. Spawna só em pontos
 * fora da visão e a uma distância mínima; respeita o limite de inimigos vivos.
 * Se bIsFinalHorde, ao terminar muda a fase para o estágio Rescue.
 */
UCLASS()
class JOGORESGATE_API AJRHordeDirector : public AActor
{
	GENERATED_BODY()

public:
	AJRHordeDirector();

	UFUNCTION(BlueprintCallable, Category = "Horde")
	void StartHorde();

	UFUNCTION(BlueprintPure, Category = "Horde")
	bool IsRunning() const { return bRunning; }

	UFUNCTION(BlueprintPure, Category = "Horde")
	int32 GetCurrentWave() const { return CurrentWave; }

	UPROPERTY(BlueprintAssignable, Category = "Horde")
	FJROnWaveStarted OnWaveStarted;

	UPROPERTY(BlueprintAssignable, Category = "Horde")
	FJROnHordeCompleted OnHordeCompleted;

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleTriggerOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void HandleEnemyDied(AJREnemyCharacter* Enemy);

	void BeginWave(int32 WaveIndex);
	void SpawnTick();
	void CheckWaveFinished();
	bool IsSpawnPointValid(const AActor* Point) const;

	UPROPERTY(VisibleAnywhere, Category = "Horde")
	TObjectPtr<UBoxComponent> ActivationTrigger;

	UPROPERTY(EditAnywhere, Category = "Horde")
	TArray<FJRWave> Waves;

	/** Target Points/atores usados como pontos de spawn. */
	UPROPERTY(EditInstanceOnly, Category = "Horde")
	TArray<TObjectPtr<AActor>> SpawnPoints;

	UPROPERTY(EditAnywhere, Category = "Horde", meta = (Units = "cm"))
	float MinSpawnDistance = 1500.f;

	/** Limite de vivos simultâneos (A-029: até 30 visíveis). */
	UPROPERTY(EditAnywhere, Category = "Horde", meta = (ClampMin = "1"))
	int32 MaxAlive = 30;

	UPROPERTY(EditAnywhere, Category = "Horde")
	bool bIsFinalHorde = true;

private:
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Alive;
	FTimerHandle SpawnTimer;
	FTimerHandle NextWaveTimer;
	int32 CurrentWave = INDEX_NONE;
	int32 SpawnedInWave = 0;
	bool bRunning = false;
	bool bCompleted = false;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "JREnemyBudgetSubsystem.generated.h"

class AJREnemyCharacter;

/**
 * Limita quantos inimigos recebem atualização completa (A-029: 12 por padrão).
 * A cada RebalanceInterval, os mais próximos do jogador ficam "completos"; os demais, reduzidos.
 */
UCLASS()
class JOGORESGATE_API UJREnemyBudgetSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;

	void RegisterEnemy(AJREnemyCharacter* Enemy);
	void UnregisterEnemy(AJREnemyCharacter* Enemy);

	UFUNCTION(BlueprintCallable, Category = "Enemy Budget")
	void SetMaxFullUpdateEnemies(int32 NewMax);

	UFUNCTION(BlueprintPure, Category = "Enemy Budget")
	int32 GetMaxFullUpdateEnemies() const { return MaxFullUpdateEnemies; }

	UFUNCTION(BlueprintPure, Category = "Enemy Budget")
	int32 GetAliveEnemyCount() const;

	/** Força recálculo imediato. */
	void Rebalance();

private:
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Enemies;
	FTimerHandle RebalanceTimer;
	int32 MaxFullUpdateEnemies = 12;
	float RebalanceInterval = 0.5f;
};

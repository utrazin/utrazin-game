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

	/** Registra um corpo em ragdoll; acima de MaxActiveRagdolls o mais antigo congela e some logo. */
	void RegisterRagdoll(AJREnemyCharacter* Enemy);

	UFUNCTION(BlueprintCallable, Category = "Enemy Budget")
	void SetMaxActiveRagdolls(int32 NewMax) { MaxActiveRagdolls = FMath::Max(1, NewMax); }

private:
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Enemies;
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Ragdolls;
	int32 MaxActiveRagdolls = 15;
	FTimerHandle RebalanceTimer;
	int32 MaxFullUpdateEnemies = 12;
	float RebalanceInterval = 0.5f;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "AI/JREnemyStateLogic.h"
#include "GameFramework/Character.h"
#include "JREnemyCharacter.generated.h"

class UJREnemyArchetype;
class UJRHealthComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnEnemyDied, AJREnemyCharacter*, Enemy);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnEnemyStateChanged, EJREnemyState, OldState, EJREnemyState, NewState);

/**
 * Inimigo genérico parametrizado por UJREnemyArchetype (ADR-002).
 * Decisão de estado: FJREnemyStateLogic. Execução: este ator, por timer (não Tick), com
 * frequência definida pelo UJREnemyBudgetSubsystem. Um StateTree no AIController pode assumir
 * a decisão (bUseBuiltInBrain = false) chamando as funções BlueprintCallable abaixo.
 */
UCLASS()
class JOGORESGATE_API AJREnemyCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AJREnemyCharacter();

	UFUNCTION(BlueprintCallable, Category = "Enemy")
	void SetFullUpdate(bool bFull);

	UFUNCTION(BlueprintPure, Category = "Enemy")
	bool IsFullUpdate() const { return bFullUpdate; }

	UFUNCTION(BlueprintPure, Category = "Enemy")
	EJREnemyState GetEnemyState() const { return CurrentState; }

	UFUNCTION(BlueprintPure, Category = "Enemy")
	bool IsDead() const { return CurrentState == EJREnemyState::Dead; }

	UFUNCTION(BlueprintPure, Category = "Enemy")
	UJREnemyArchetype* GetArchetype() const { return Archetype; }

	/** Uma iteração de percepção + decisão + ação. Chamado pelo timer ou por task de StateTree. */
	UFUNCTION(BlueprintCallable, Category = "Enemy")
	void UpdateBrain();

	/** Executa o ataque do arquétipo contra o alvo atual, respeitando o intervalo. */
	UFUNCTION(BlueprintCallable, Category = "Enemy")
	bool TryAttack();

	UPROPERTY(BlueprintAssignable, Category = "Enemy")
	FJROnEnemyDied OnEnemyDied;

	UPROPERTY(BlueprintAssignable, Category = "Enemy")
	FJROnEnemyStateChanged OnEnemyStateChanged;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UFUNCTION()
	void HandleDeath(UJRHealthComponent* Health, AActor* Killer);

	void SetEnemyState(EJREnemyState NewState);
	void RestartBrainTimer();
	void FireRangedShot();
	FVector GetMuzzleLocation() const;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Enemy")
	TObjectPtr<UJRHealthComponent> HealthComponent;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Enemy")
	TObjectPtr<UJREnemyArchetype> Archetype;

	UPROPERTY(EditAnywhere, Category = "Enemy")
	bool bUseBuiltInBrain = true;

	UPROPERTY(EditAnywhere, Category = "Enemy")
	bool bHasPatrol = false;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Performance", meta = (Units = "s"))
	float FullUpdateInterval = 0.1f;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Performance", meta = (Units = "s"))
	float ReducedUpdateInterval = 0.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy")
	FName MuzzleSocket = TEXT("hand_r");

private:
	TWeakObjectPtr<AActor> Target;
	FTimerHandle BrainTimer;
	FTimerHandle BurstTimer;
	FRandomStream Random;
	EJREnemyState CurrentState = EJREnemyState::Idle;
	double StateEnterTime = 0.0;
	double LastAttackTime = -1000.0;
	int32 BurstShotsRemaining = 0;
	bool bFullUpdate = false;
};

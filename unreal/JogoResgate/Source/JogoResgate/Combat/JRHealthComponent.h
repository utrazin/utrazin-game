// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "JRHealthComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FJROnHealthChanged, UJRHealthComponent*, HealthComponent, float, NewHealth, float, Delta);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnDeath, UJRHealthComponent*, HealthComponent, AActor*, Killer);

/**
 * Saúde de qualquer ator (personagem, inimigo, vítima). Ponto único de dano (ADR-001):
 * recebe o dano nativo da engine (OnTakeAnyDamage) e expõe delegates. Sem Tick.
 */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRHealthComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRHealthComponent();

	UFUNCTION(BlueprintCallable, Category = "Health")
	float ApplyDamage(float Amount, AActor* DamageCauser);

	UFUNCTION(BlueprintCallable, Category = "Health")
	float Heal(float Amount);

	/** Restaura a vida máxima (respawn em checkpoint). */
	UFUNCTION(BlueprintCallable, Category = "Health")
	void ResetHealth();

	UFUNCTION(BlueprintPure, Category = "Health")
	float GetHealth() const { return Health; }

	UFUNCTION(BlueprintPure, Category = "Health")
	float GetMaxHealth() const { return MaxHealth; }

	UFUNCTION(BlueprintPure, Category = "Health")
	float GetHealthNormalized() const { return MaxHealth > 0.f ? Health / MaxHealth : 0.f; }

	UFUNCTION(BlueprintPure, Category = "Health")
	bool IsDead() const { return bIsDead; }

	void SetMaxHealth(float NewMax, bool bRefill);

	UPROPERTY(BlueprintAssignable, Category = "Health")
	FJROnHealthChanged OnHealthChanged;

	UPROPERTY(BlueprintAssignable, Category = "Health")
	FJROnDeath OnDeath;

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleTakeAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType,
		AController* InstigatedBy, AActor* DamageCauser);

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Health", meta = (ClampMin = "1"))
	float MaxHealth = 100.f;

	/** Multiplicador de dano recebido (ex.: dificuldade). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Health", meta = (ClampMin = "0"))
	float DamageTakenMultiplier = 1.f;

private:
	UPROPERTY(VisibleInstanceOnly, Category = "Health")
	float Health = 100.f;

	bool bIsDead = false;
};

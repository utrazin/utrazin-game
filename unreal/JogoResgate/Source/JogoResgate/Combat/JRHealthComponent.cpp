// Copyright utrazin. All Rights Reserved.

#include "Combat/JRHealthComponent.h"
#include "GameFramework/Actor.h"
#include "JogoResgate.h"

UJRHealthComponent::UJRHealthComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UJRHealthComponent::BeginPlay()
{
	Super::BeginPlay();
	Health = MaxHealth;
	bIsDead = false;
	if (AActor* Owner = GetOwner())
	{
		Owner->OnTakeAnyDamage.AddDynamic(this, &UJRHealthComponent::HandleTakeAnyDamage);
	}
}

void UJRHealthComponent::HandleTakeAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType,
	AController* InstigatedBy, AActor* DamageCauser)
{
	ApplyDamage(Damage, DamageCauser);
}

float UJRHealthComponent::ApplyDamage(float Amount, AActor* DamageCauser)
{
	if (bIsDead || Amount <= 0.f)
	{
		return 0.f;
	}
	const float Before = Health;
	Health = FMath::Clamp(Health - Amount * DamageTakenMultiplier, 0.f, MaxHealth);
	const float Delta = Health - Before;
	OnHealthChanged.Broadcast(this, Health, Delta);
	if (Health <= 0.f)
	{
		bIsDead = true;
		UE_LOG(LogJR, Verbose, TEXT("%s morreu (causador: %s)"), *GetNameSafe(GetOwner()), *GetNameSafe(DamageCauser));
		OnDeath.Broadcast(this, DamageCauser);
	}
	return -Delta;
}

float UJRHealthComponent::Heal(float Amount)
{
	if (bIsDead || Amount <= 0.f)
	{
		return 0.f;
	}
	const float Before = Health;
	Health = FMath::Clamp(Health + Amount, 0.f, MaxHealth);
	const float Delta = Health - Before;
	if (Delta > 0.f)
	{
		OnHealthChanged.Broadcast(this, Health, Delta);
	}
	return Delta;
}

void UJRHealthComponent::ResetHealth()
{
	bIsDead = false;
	const float Delta = MaxHealth - Health;
	Health = MaxHealth;
	OnHealthChanged.Broadcast(this, Health, Delta);
}

void UJRHealthComponent::SetMaxHealth(float NewMax, bool bRefill)
{
	MaxHealth = FMath::Max(1.f, NewMax);
	Health = bRefill ? MaxHealth : FMath::Min(Health, MaxHealth);
}

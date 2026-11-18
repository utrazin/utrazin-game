// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Remap/JRRemapTypes.h"
#include "JREconomySubsystem.generated.h"

class AJRCharacter;
class UJRSaveGame;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnWalletChanged, int64, NewCredits);

/**
 * [Remap F1] Carteira e compras permanentes (REMAP 7.1 e 9.3). Guarda tudo no save v3 do UJRProgressionSubsystem.
 * F1: créditos, Bancada (Ix-Vel) e armas do Armeiro (Krug). Sucata e cristais já ficam no save para o F3.
 * (No F3 a Bancada/Laboratório vão para o UJRUpgradeSubsystem com DataTable; aqui é o mínimo do protótipo.)
 */
UCLASS()
class JOGORESGATE_API UJREconomySubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	UFUNCTION(BlueprintPure, Category = "Economy")
	int64 GetCredits() const;

	UFUNCTION(BlueprintCallable, Category = "Economy")
	void AddCredits(int64 Amount, bool bSave = true);

	/** Gasta se tiver; retorna false sem mexer em nada se faltar. */
	UFUNCTION(BlueprintCallable, Category = "Economy")
	bool SpendCredits(int64 Amount);

	// ---------------- Bancada
	UFUNCTION(BlueprintPure, Category = "Economy")
	int32 GetBenchLevel() const;

	UFUNCTION(BlueprintPure, Category = "Economy")
	int64 GetNextBenchCost() const { return FJRRemapRules::BenchCost(GetBenchLevel()); }

	UFUNCTION(BlueprintCallable, Category = "Economy")
	bool BuyBenchLevel();

	UFUNCTION(BlueprintPure, Category = "Economy")
	float GetPermanentDamageMultiplier() const { return FJRRemapRules::BenchDamageMultiplier(GetBenchLevel()); }

	// ---------------- Armeiro
	/** Graveto e pistola são sempre da pessoa. */
	UFUNCTION(BlueprintPure, Category = "Economy")
	bool OwnsWeapon(EJRWeaponSlot Slot) const;

	UFUNCTION(BlueprintCallable, Category = "Economy")
	bool BuyWeapon(EJRWeaponSlot Slot);

	/** Dá ao herói as armas compradas (equipa a melhor) e aplica a Bancada. Sem cartas (isso é do UJRRunSubsystem). */
	void GrantOwnedWeapons(AJRCharacter* Hero) const;

	// ---------------- recordes
	UFUNCTION(BlueprintPure, Category = "Economy")
	int32 GetBestWave() const;

	/** Registra o fim de uma corrida. Retorna true se bateu o recorde de ondas. */
	bool RecordRun(int32 Waves);

	UPROPERTY(BlueprintAssignable, Category = "Economy")
	FJROnWalletChanged OnWalletChanged;

	void Save();

private:
	UJRSaveGame* GetSaveGame() const;
};

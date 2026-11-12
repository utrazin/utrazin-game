// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Combat/JRAmmoState.h"
#include "JRWeaponComponent.generated.h"

class UJRWeaponDefinition;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnAmmoChanged, int32, Magazine, int32, Reserve);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnWeaponFired, const FVector&, Start, const FVector&, End);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnReloadStateChanged, bool, bIsReloading);

/**
 * Arma hitscan do personagem (pistola alienígena). Disparo automático por timer, sem Tick.
 * Visual/áudio ficam no Blueprint via delegates.
 */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRWeaponComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRWeaponComponent();

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void EquipDefinition(UJRWeaponDefinition* NewDefinition);

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void StartFire();

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void StopFire();

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	bool StartReload();

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void SetAiming(bool bNewAiming) { bAiming = bNewAiming; }

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void AddReserveAmmo(int32 Amount);

	UFUNCTION(BlueprintPure, Category = "Weapon")
	FJRAmmoState GetAmmo() const { return Ammo; }

	UFUNCTION(BlueprintPure, Category = "Weapon")
	bool IsReloading() const { return bReloading; }

	UFUNCTION(BlueprintPure, Category = "Weapon")
	UJRWeaponDefinition* GetDefinition() const { return Definition; }

	/** Cancela disparo e recarga (morte, troca de pawn). */
	void CancelAll();

	UPROPERTY(BlueprintAssignable, Category = "Weapon")
	FJROnAmmoChanged OnAmmoChanged;

	UPROPERTY(BlueprintAssignable, Category = "Weapon")
	FJROnWeaponFired OnWeaponFired;

	UPROPERTY(BlueprintAssignable, Category = "Weapon")
	FJROnReloadStateChanged OnReloadStateChanged;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	void FireOnce();
	void FinishReload();
	bool GetAimViewPoint(FVector& OutLocation, FRotator& OutRotation) const;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon")
	TObjectPtr<UJRWeaponDefinition> Definition;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	TEnumAsByte<ECollisionChannel> TraceChannel = ECC_Visibility;

	/** Desenha o rastro do tiro (greybox, até existir arma/VFX). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	bool bDrawDebugTracer = true;

private:
	FJRAmmoState Ammo;
	FTimerHandle FireTimer;
	FTimerHandle ReloadTimer;
	FRandomStream SpreadStream;
	double LastFireTime = -1000.0;
	bool bWantsToFire = false;
	bool bReloading = false;
	bool bAiming = false;
};

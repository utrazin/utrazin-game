// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Combat/JRAmmoState.h"
#include "JRWeaponComponent.generated.h"

class UJRWeaponDefinition;
class USceneComponent;
class USoundBase;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnAmmoChanged, int32, Magazine, int32, Reserve);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnWeaponFired, const FVector&, Start, const FVector&, End);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnReloadStateChanged, bool, bIsReloading);

/**
 * Arma do personagem (pistola/escopeta alienígenas). Disparo automático por timer, sem Tick.
 * Mira por traço (hitscan) da câmera; o PLASMA visível sai do cano e o dano chega junto com ele (A-057).
 * Sons de tiro/recarga/impacto e efeitos vêm da definição da arma; o coice fica no AJRCharacter.
 */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRWeaponComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRWeaponComponent();

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void EquipDefinition(UJRWeaponDefinition* NewDefinition);

	/** Troca de arma mantendo a munição total (as armas de fogo dividem as mesmas células). */
	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void SwitchDefinitionKeepAmmo(UJRWeaponDefinition* NewDefinition);

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

	/** Poderes temporários (ex.: Fúria): multiplicam dano e cadência. */
	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void SetBoost(float InDamageMultiplier, float InFireRateMultiplier);

	/** [Remap F1] Bancada + cartas da corrida. Multiplica junto com o SetBoost (Fúria), sem um apagar o outro. */
	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void SetUpgradeMultipliers(float InDamageMultiplier, float InFireRateMultiplier);

	UFUNCTION(BlueprintPure, Category = "Weapon")
	float GetUpgradeDamageMultiplier() const { return UpgradeDamageMultiplier; }

	UFUNCTION(BlueprintPure, Category = "Weapon")
	UJRWeaponDefinition* GetDefinition() const { return Definition; }

	/** Cancela disparo e recarga (morte, troca de pawn). */
	void CancelAll();

	/** Malha da arma na mão: o plasma sai da ponta dela (soquete "Muzzle" ou ponta do cano pelos limites). */
	void SetMuzzleComponent(USceneComponent* InMuzzle) { MuzzleComponent = InMuzzle; }

	/** Ponto de saída do plasma agora. */
	FVector GetMuzzleLocation(const FVector& FallbackDir) const;

	/** Abertura da mira 0..1 (sobe a cada tiro e fecha sozinha). */
	UFUNCTION(BlueprintPure, Category = "Weapon")
	float GetCrosshairBloom() const;

	/** Marcador de acerto: hora (mundo) do último acerto em algo com vida e se foi abate. */
	double GetLastHitConfirmTime() const { return LastHitConfirmTime; }
	bool WasLastHitKill() const { return bLastHitKill; }

	/** Registra um acerto confirmado (tiro ou golpe corpo a corpo) para o marcador da mira e o som. */
	void NotifyHitConfirmed(bool bKill);

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

	/** Linhas de depuração do tiro: só valem com o comando de console "jr.Weapon.Debug 1" (A-057). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	bool bDrawDebugTracer = true;

	/** Bipe do marcador de acerto / abate (só para o jogador). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Feedback")
	TSoftObjectPtr<USoundBase> HitMarkerSound = TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Audio/SFX/Weapons/SFX_UI_HitMarker.SFX_UI_HitMarker")));

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Feedback")
	TSoftObjectPtr<USoundBase> KillMarkerSound = TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Audio/SFX/Weapons/SFX_UI_KillMarker.SFX_UI_KillMarker")));

	/** Volume da camada 2D (o próprio jogador ouvindo a arma "na mão"). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Feedback", meta = (ClampMin = "0"))
	float Player2DVolume = 0.6f;

	/** Velocidade com que a mira fecha depois dos tiros (1/s). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Feedback", meta = (ClampMin = "0.1"))
	float BloomDecay = 5.f;

	/** Empurrão em objetos com física (cones, caixas, corpos) ao acertar. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	float HitImpulse = 600.f;

	/** Dano, empurrão, impacto e marcador de um projétil que chegou (chamado quando o plasma visível chega). */
	void ApplyPelletHit(const FHitResult& Hit, const FVector& Dir, float Amount, bool bImpactSound);

	/** Toca um som da arma: 3D no cano (atenuado) + camada 2D se for o jogador. */
	void PlayWeaponSound(USoundBase* Sound, const FVector& Location, float Volume, bool bPitchVariation) const;

	/** Dono controlado pelo jogador local? */
	bool IsLocalPlayerOwner() const;

private:
	FJRAmmoState Ammo;
	FTimerHandle FireTimer;
	FTimerHandle ReloadTimer;
	FRandomStream SpreadStream;
	double LastFireTime = -1000.0;
	bool bWantsToFire = false;
	bool bReloading = false;
	bool bAiming = false;
	float DamageMultiplier = 1.f;
	float FireRateMultiplier = 1.f;
	/** Traço do tiro: cenário pelo TraceChannel e corpos pela cápsula (Pawn). */
	bool TraceShot(UWorld* World, FHitResult& OutHit, const FVector& Start, const FVector& End, const FCollisionQueryParams& Params) const;
	float UpgradeDamageMultiplier = 1.f;   // [Remap F1]
	float UpgradeFireRateMultiplier = 1.f; // [Remap F1]

	TWeakObjectPtr<USceneComponent> MuzzleComponent;
	float BloomValue = 0.f;
	double BloomTime = 0.0;
	double LastHitConfirmTime = -100.0;
	bool bLastHitKill = false;
};

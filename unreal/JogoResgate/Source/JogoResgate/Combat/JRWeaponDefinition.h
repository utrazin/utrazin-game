// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "JRWeaponDefinition.generated.h"

class UAnimMontage;
class USoundBase;
class UNiagaraSystem;
class USkeletalMesh;
class USoundAttenuation;

/** Definição de arma (DA_Weapon_*). Uma arma no MVP (A-011), sistema extensível. */
UCLASS(BlueprintType)
class JOGORESGATE_API UJRWeaponDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon")
	FName WeaponId = TEXT("WPN-001");

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon")
	FText DisplayName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0"))
	float Damage = 25.f;

	/** Tiros por segundo. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0.1"))
	float FireRate = 4.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "1"))
	int32 MagazineSize = 12;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0"))
	int32 StartingReserve = 48;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0", Units = "s"))
	float ReloadTime = 1.6f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0", Units = "cm"))
	float Range = 6000.f;

	/** Meio-ângulo de dispersão em graus (mirando reduz pela metade). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0"))
	float SpreadHalfAngleDegrees = 1.5f;

	/** Projéteis por disparo (escopeta > 1). Cada um aplica Damage. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "1"))
	int32 PelletCount = 1;

	/** Dispersão mínima dos projéteis (graus), mesmo mirando. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0"))
	float PelletSpreadDegrees = 0.f;

	/** Quantos corpos o tiro atravessa depois do primeiro (rifle de precisão: 1). Paredes sempre param. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Stats", meta = (ClampMin = "0", ClampMax = "4"))
	int32 MaxPierce = 0;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Visual")
	TSoftObjectPtr<USkeletalMesh> Mesh;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Visual")
	FName AttachSocket = TEXT("hand_r_weapon");

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Visual")
	TObjectPtr<UAnimMontage> FireMontage;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Visual")
	TObjectPtr<UAnimMontage> ReloadMontage;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback")
	TObjectPtr<USoundBase> FireSound;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback")
	TObjectPtr<USoundBase> ReloadSound;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback")
	TObjectPtr<UNiagaraSystem> MuzzleEffect;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback")
	TObjectPtr<UNiagaraSystem> ImpactEffect;

	// ------------------------------------------------------------ Sensação de combate (A-057)

	/** Coice da câmera por tiro: graus para cima (pistola pouco, escopeta muito). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (Units = "Degrees", ClampMin = "0"))
	float RecoilPitch = 1.2f;

	/** Desvio lateral aleatório por tiro (graus, para um lado ou outro). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (Units = "Degrees", ClampMin = "0"))
	float RecoilYaw = 0.35f;

	/** Rapidez com que a câmera volta depois do coice (maior = volta mais rápido). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (ClampMin = "0.5"))
	float RecoilRecovery = 9.f;

	/** Parte do coice que fica na mira (sobe de verdade; o resto volta sozinho). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (ClampMin = "0", ClampMax = "1"))
	float RecoilKeepFraction = 0.2f;

	/** Quanto a arma recua na mão (cm, para trás ao longo do cano). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (Units = "cm", ClampMin = "0"))
	float KickBack = 3.f;

	/** Quanto o cano sobe na mão (graus). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (Units = "Degrees", ClampMin = "0"))
	float KickPitch = 7.f;

	/** Rapidez com que a arma volta para a mão (maior = mais seco). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (ClampMin = "0.5"))
	float KickRecovery = 14.f;

	/** Tremor de câmera por tiro (0 = nada, 1 = forte). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (ClampMin = "0", ClampMax = "1"))
	float ShakeScale = 0.2f;

	/** Quanto a mira abre a cada tiro (0..1; fecha sozinha). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (ClampMin = "0", ClampMax = "1"))
	float CrosshairBloom = 0.35f;

	/** Escopeta: tempo depois do tiro em que a célula "bombeia" (som + tranco leve da arma). 0 = sem. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil", meta = (Units = "s", ClampMin = "0"))
	float FollowUpDelay = 0.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Recoil")
	TObjectPtr<USoundBase> FollowUpSound;

	/** Cor do plasma (projétil, rastro, clarão do cano, impacto). Combina com o brilho da arma. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma")
	FLinearColor PlasmaColor = FLinearColor(0.55f, 0.15f, 1.f, 1.f);

	/** Brilho (emissivo) do plasma. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma", meta = (ClampMin = "0"))
	float PlasmaIntensity = 25.f;

	/** Velocidade VISUAL do projétil (cm/s). O dano chega junto com ele. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma", meta = (Units = "cm/s", ClampMin = "1000"))
	float BoltSpeed = 12000.f;

	/** Comprimento do núcleo brilhante do projétil. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma", meta = (Units = "cm", ClampMin = "1"))
	float BoltLength = 70.f;

	/** Espessura do projétil. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma", meta = (Units = "cm", ClampMin = "0.5"))
	float BoltWidth = 6.f;

	/** Comprimento do rastro atrás do projétil. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma", meta = (Units = "cm", ClampMin = "0"))
	float TrailLength = 400.f;

	/** Tamanho do clarão do cano. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma", meta = (ClampMin = "0"))
	float MuzzleFlashScale = 1.f;

	/** Tamanho do estouro no impacto. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma", meta = (ClampMin = "0"))
	float ImpactScale = 1.f;

	/** Ajuste do ponto de saída do plasma (espaço da malha da arma; X = ao longo do cano). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Plasma")
	FVector MuzzleOffset = FVector::ZeroVector;

	/** Chiado do plasma batendo (no ponto do impacto). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback")
	TObjectPtr<USoundBase> ImpactSound;

	/** Gatilho sem célula nenhuma. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback")
	TObjectPtr<USoundBase> DryFireSound;

	/** Atenuação dos sons 3D da arma (distância). Vazio = padrão do som. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback")
	TObjectPtr<USoundAttenuation> SoundAttenuation;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback", meta = (ClampMin = "0"))
	float FireVolume = 1.f;

	/** Variação aleatória do tom de cada tiro (0,06 = +-6%). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Weapon|Feedback", meta = (ClampMin = "0", ClampMax = "0.5"))
	float PitchVariance = 0.06f;
};

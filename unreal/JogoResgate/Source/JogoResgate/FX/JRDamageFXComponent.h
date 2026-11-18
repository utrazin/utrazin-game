// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "JRDamageFXComponent.generated.h"

class AController;
class UDamageType;
class UDecalComponent;
class UJRHealthComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UPrimitiveComponent;
class USkeletalMeshComponent;
class USoundBase;
class UStaticMeshComponent;

/** Tipo de sangue: humano (vermelho) ou zumbi (azul brilhante). */
UENUM(BlueprintType)
enum class EJRBloodType : uint8
{
	Human,
	Zombie
};

/** Ferimento marcado no corpo (mancha presa no osso). */
USTRUCT()
struct FJRWoundMark
{
	GENERATED_BODY()

	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> Blob;

	UPROPERTY(Transient)
	TObjectPtr<UDecalComponent> Decal;

	double Time = 0.0;
};

/** Um golpe recente (indicador de direção do dano no HUD). */
struct FJRDamageIndicator
{
	FVector From = FVector::ZeroVector;
	double Time = 0.0;
	float Amount = 0.f;
};

/**
 * Sangue e reação visual a dano de qualquer personagem (A-057). Escuta o dano nativo do ator:
 *  - respingo no ponto do acerto (gotinhas), mancha na parede/chão atrás;
 *  - FERIMENTO no corpo no ponto exato (mancha presa ao osso: decal + "bolha" achatada), some depois;
 *  - gotejar das feridas enquanto o ferimento é recente ou a vida está baixa (rastro no chão);
 *  - flash do corpo (zumbis) e registro da direção do golpe (herói: indicador no HUD).
 * Dano sem ponto (atropelamento, explosão, soco antigo) acha um ponto do corpo virado para quem causou.
 * Sem Tick: timers só enquanto há ferida/gotejar.
 */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRDamageFXComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRDamageFXComponent();

	/** Define o tipo e as cores padrão (vermelho humano / azul zumbi). Chame no construtor do dono. */
	void SetBloodType(EJRBloodType NewType);

	UFUNCTION(BlueprintPure, Category = "DamageFX")
	EJRBloodType GetBloodType() const { return BloodType; }

	/** Efeito completo de um acerto (usado pelos handlers de dano; pode ser chamado direto). */
	void PlayHit(const FVector& Point, const FVector& ShotDir, FName Bone, UPrimitiveComponent* HitComp, float Damage, AActor* Causer);

	/** Golpes recentes (para o indicador de direção do HUD). */
	const TArray<FJRDamageIndicator>& GetRecentHits() const { return RecentHits; }

	/** Apaga todos os ferimentos (respawn). */
	UFUNCTION(BlueprintCallable, Category = "DamageFX")
	void ClearWounds();

	/**
	 * Acha um ponto na SUPERFÍCIE do corpo do alvo virado para From, numa faixa de altura
	 * (-1 = pé, 0 = meio, 1 = topo da cápsula/limites da malha). Traço só contra a malha do alvo (corpos do
	 * Physics Asset); sem acerto usa o osso mais próximo. Usado pelo soco do zumbi e por dano sem ponto.
	 */
	static bool FindBodyHit(AActor* Target, const FVector& From, float BandMin, float BandMax, FHitResult& OutHit);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UFUNCTION()
	void HandlePointDamage(AActor* DamagedActor, float Damage, AController* InstigatedBy, FVector HitLocation,
		UPrimitiveComponent* FHitComponent, FName BoneName, FVector ShotFromDirection, const UDamageType* DamageType,
		AActor* DamageCauser);

	UFUNCTION()
	void HandleAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType, AController* InstigatedBy,
		AActor* DamageCauser);

	UFUNCTION()
	void HandleHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta);

	void AddWound(USkeletalMeshComponent* BodyMesh, FName Bone, const FVector& Point, const FVector& Normal);
	void RemoveWound(int32 Index);
	void UpdateWounds();
	void Drip();
	void EnsureDripTimer();
	void StartHitFlash();
	void EndHitFlash();
	bool IsNearViewer(float MaxDistance) const;
	USkeletalMeshComponent* GetBodyMesh() const;

	UPROPERTY(EditAnywhere, Category = "DamageFX")
	EJRBloodType BloodType = EJRBloodType::Human;

	/** Cor do sangue (linear). Humano: vermelho escuro; zumbi: azul-ciano. */
	UPROPERTY(EditAnywhere, Category = "DamageFX")
	FLinearColor BloodColor = FLinearColor(0.32f, 0.01f, 0.01f, 1.f);

	/** Brilho do sangue (0 = sem brilho; zumbi brilha). */
	UPROPERTY(EditAnywhere, Category = "DamageFX", meta = (ClampMin = "0"))
	float BloodEmissive = 0.f;

	/** Gotinhas por acerto (escala com o dano). */
	UPROPERTY(EditAnywhere, Category = "DamageFX", meta = (ClampMin = "0"))
	int32 SprayCount = 10;

	UPROPERTY(EditAnywhere, Category = "DamageFX", meta = (Units = "cm/s"))
	float SpraySpeed = 380.f;

	/** Mancha na parede/chão atrás do acerto (tamanho em cm). */
	UPROPERTY(EditAnywhere, Category = "DamageFX", meta = (Units = "cm"))
	float SplatterSize = 45.f;

	/** Ferimentos marcados no corpo ao mesmo tempo (o mais velho some). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Wounds", meta = (ClampMin = "0"))
	int32 MaxWounds = 6;

	/** Tamanho da mancha do ferimento no corpo (cm). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Wounds", meta = (Units = "cm"))
	float WoundSize = 10.f;

	/** Quanto tempo o ferimento fica no corpo (some em 2 s depois disso). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Wounds", meta = (Units = "s"))
	float WoundLifetime = 40.f;

	/** "Bolha" achatada de sangue sob o decal (garante a marca mesmo se o decal não aparecer na pele). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Wounds")
	bool bWoundBlob = true;

	/** Decal preso ao osso (mancha que acompanha a pele). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Wounds")
	bool bWoundDecal = true;

	/** Ossos sem marca (a cabeça some em primeira pessoa; a marca ficaria flutuando na frente da câmera). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Wounds")
	TArray<FName> NoWoundBones = { TEXT("head"), TEXT("neck_01"), TEXT("neck_02") };

	/** Intervalo entre gotas enquanto sangra. */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Drip", meta = (Units = "s", ClampMin = "0.1"))
	float DripInterval = 0.4f;

	/** Sangra por este tempo depois de cada acerto. */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Drip", meta = (Units = "s"))
	float DripAfterHit = 5.f;

	/** Com a vida abaixo desta fração sangra sem parar (rastro no chão). 0 = nunca. */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Drip", meta = (ClampMin = "0", ClampMax = "1"))
	float LowHealthDripFraction = 0.35f;

	/** Gotas só perto da câmera (desempenho). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Drip", meta = (Units = "cm"))
	float DripMaxDistance = 3500.f;

	UPROPERTY(EditAnywhere, Category = "DamageFX|Drip", meta = (Units = "cm"))
	float DripDecalSize = 9.f;

	/** Flash no corpo ao levar dano (overlay; zumbis). */
	UPROPERTY(EditAnywhere, Category = "DamageFX|Flash")
	bool bHitFlash = false;

	UPROPERTY(EditAnywhere, Category = "DamageFX|Flash")
	FLinearColor HitFlashColor = FLinearColor(0.6f, 0.9f, 1.f, 1.f);

	UPROPERTY(EditAnywhere, Category = "DamageFX|Flash", meta = (Units = "s"))
	float HitFlashTime = 0.08f;

	/** Som de carne ao ser atingido (3D; vazio = sem som). */
	UPROPERTY(EditAnywhere, Category = "DamageFX")
	TSoftObjectPtr<USoundBase> FleshHitSound = TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Audio/SFX/Weapons/SFX_Flesh_Hit.SFX_Flesh_Hit")));

private:
	UPROPERTY(Transient)
	TArray<FJRWoundMark> Wounds;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> FlashMID;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> SavedOverlay;

	TWeakObjectPtr<UJRHealthComponent> OwnerHealth;
	TArray<FJRDamageIndicator> RecentHits;
	FTimerHandle DripTimer;
	FTimerHandle WoundTimer;
	FTimerHandle FlashTimer;
	double LastHitTime = -100.0;
	uint64 LastPointDamageFrame = 0;
	bool bFlashing = false;
	FRandomStream Rand;
};

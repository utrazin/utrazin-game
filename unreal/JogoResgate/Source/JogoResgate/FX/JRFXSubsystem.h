// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "JRFXSubsystem.generated.h"

class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;

/** Tipo de decal do sistema (cada um tem seu material). */
enum class EJRDecalKind : uint8
{
	Blood,
	Scorch
};

/** Uma partícula simples (malha de esfera esticada) do pool. */
USTRUCT()
struct FJRFXParticle
{
	GENERATED_BODY()

	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> Material;

	uint8 Kind = 0;
	bool bActive = false;
	FVector Origin = FVector::ZeroVector;
	FVector Position = FVector::ZeroVector;
	FVector Velocity = FVector::ZeroVector;
	FVector Direction = FVector::ForwardVector;
	float Age = 0.f;
	float Life = 0.1f;
	float Speed = 0.f;
	float Length = 10.f;
	float Width = 5.f;
	float StartSize = 5.f;
	float EndSize = 5.f;
	float Gravity = 0.f;
	float Opacity = 1.f;
	/** Gotas: altura do chão (onde viram decal). Muito baixo = sem chão. */
	double FloorZ = -1.0e9;
	float DecalSize = 0.f;
	FLinearColor Color = FLinearColor::White;
	float Emissive = 0.f;
	int32 Light = INDEX_NONE;
};

/** Luz piscando (clarão do cano/impacto) ou seguindo um projétil. */
USTRUCT()
struct FJRFXLight
{
	GENERATED_BODY()

	UPROPERTY(Transient)
	TObjectPtr<UPointLightComponent> Light;

	bool bActive = false;
	float Age = 0.f;
	float Life = 0.1f;
	float Peak = 0.f;
	/** Índice no pool de plasma que a luz segue (INDEX_NONE = parada). */
	int32 Follow = INDEX_NONE;
};

/**
 * Efeitos visuais leves do combate SEM Niagara (A-057): projéteis e clarões de plasma, faíscas, respingos e
 * gotas de sangue, decals de sangue e de queimado. Tudo em pools de componentes reaproveitados num ator
 * escondido, atualizados num único Tick do subsistema (Tick justificado: os efeitos se movem a cada quadro;
 * sem efeitos ativos o trabalho é só percorrer listas pequenas).
 * Materiais por caminho fixo, criados pelo tools/unreal/setup_combat_feel.py (sem eles: só não desenha).
 */
UCLASS()
class JOGORESGATE_API UJRFXSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	static UJRFXSubsystem* Get(const UObject* WorldContext);

	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** Projétil de plasma visível do cano até o ponto de impacto (núcleo + rastro + luz opcional). */
	void SpawnPlasmaBolt(const FVector& From, const FVector& To, const FLinearColor& Color, float Intensity, float Speed,
		float Length, float Width, float TrailLength, bool bWithLight);

	/** Clarão (esfera que cresce e some) com luz opcional (LightIntensity 0 = sem luz). */
	void SpawnFlash(const FVector& Location, const FLinearColor& Color, float Intensity, float StartSize, float EndSize,
		float Life, float LightIntensity, float LightRadius);

	/** Estouro do plasma batendo: clarão, faíscas, luz e (em superfície) marca de queimado. */
	void SpawnPlasmaImpact(const FVector& Location, const FVector& Normal, const FLinearColor& Color, float Intensity,
		float Scale, bool bScorchDecal);

	/** Respingo de sangue: gotinhas voando na direção do tiro (saída) e um pouco para fora do corpo. */
	void SpawnBloodSpray(const FVector& Location, const FVector& ShotDir, const FVector& Normal, const FLinearColor& Color,
		float Emissive, int32 Count, float Speed);

	/**
	 * [A-073] Terra levantada (aterrissagem forte, golpe no chão): torrõezinhos foscos saindo em leque e caindo.
	 * Usa o pool das gotas com Emissive 0; somem ao tocar o chão (FloorZ), sem decal.
	 */
	void SpawnDustPuff(const FVector& Location, const FLinearColor& Color, int32 Count, float Speed);

	/** Gota caindo; ao chegar no chão vira uma manchinha (DecalSize 0 = sem mancha). */
	void SpawnBloodDrop(const FVector& Location, const FLinearColor& Color, float Emissive, float DecalSize,
		const AActor* IgnoreActor);

	/** Decal no mundo (sangue/queimado) com fade; o total é limitado (os mais velhos somem). */
	UDecalComponent* SpawnDecal(EJRDecalKind Kind, const FVector& Location, const FVector& Normal, float Size,
		const FLinearColor& Color, float Emissive, float Life);

	/** Material das manchas presas no corpo (mesmo das gotas). Pode ser nulo antes do script. */
	UMaterialInterface* GetBloodMaterial();
	UMaterialInterface* GetBloodDecalMaterial();
	UMaterialInterface* GetHitFlashMaterial();
	UStaticMesh* GetSphereMesh();

protected:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
	bool EnsureHost();
	/** Índice livre no pool (cresce até o teto; cheio: rouba o mais velho). */
	int32 Acquire(bool bBloodPool);
	int32 AcquireLight();
	void UpdateParticle(FJRFXParticle& P, float DeltaTime, bool bBloodPool, int32 Index);
	void Release(FJRFXParticle& P);
	void ReleaseLight(FJRFXLight& L);
	void LoadAssets();

	UPROPERTY(Transient)
	TObjectPtr<AActor> Host;

	UPROPERTY(Transient)
	TArray<FJRFXParticle> Plasma;

	UPROPERTY(Transient)
	TArray<FJRFXParticle> Blood;

	UPROPERTY(Transient)
	TArray<FJRFXLight> Lights;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UDecalComponent>> Decals;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> Sphere;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> PlasmaMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> BloodMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> BloodDecalMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> ScorchDecalMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> HitFlashMaterial;

	bool bAssetsLoaded = false;
	int32 ActiveCount = 0;
	FRandomStream Rand;
};

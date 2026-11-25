// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRLootChest.h"
#include "JRArenaInteractives.generated.h"

class UBoxComponent;
class UCapsuleComponent;
class UJRHealthComponent;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * [Remap F2] Baú grátis da arena (REMAP 6.2, passo 5): o baú de sempre (E abre), com munição, vida, 1 bandagem
 * e créditos da corrida (CreditsPerLevel x nível do setor). Usa a malha do baú do usuário quando existe.
 */
UCLASS()
class JOGORESGATE_API AJRArenaChest : public AJRLootChest
{
	GENERATED_BODY()

public:
	AJRArenaChest();

	virtual void Interact_Implementation(AActor* InstigatorActor) override;

protected:
	UPROPERTY(EditAnywhere, Category = "Chest", meta = (ClampMin = "0"))
	int32 CreditsPerLevel = 40;
};

/**
 * [Remap F2] Ninho alienígena (objetivo "Destrua 3 ninhos", REMAP 6.4). Leva tiro (caixa simples bloqueia tudo),
 * tem vida própria e brilha. Enquanto vivo, o diretor usa o ninho como ponto de surgimento extra.
 */
UCLASS()
class JOGORESGATE_API AJRArenaNest : public AActor
{
	GENERATED_BODY()

public:
	AJRArenaNest();

	/** Vida máxima (o diretor escala com o nível). */
	void SetupNest(float InMaxHealth);

	UJRHealthComponent* GetHealthComponent() const { return HealthComponent; }
	bool IsNestDestroyed() const { return bNestDestroyed; }

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleNestDeath(UJRHealthComponent* DeadHealth, AActor* Killer);

	/** [A-088] Cápsula (topo redondo e "não andável"): o herói escorrega se tentar subir no ninho. */
	UPROPERTY(VisibleAnywhere, Category = "Nest")
	TObjectPtr<UCapsuleComponent> Collision;

	UPROPERTY(VisibleAnywhere, Category = "Nest")
	TObjectPtr<UStaticMeshComponent> NestMesh;

	UPROPERTY(VisibleAnywhere, Category = "Nest")
	TObjectPtr<UPointLightComponent> Glow;

	UPROPERTY(VisibleAnywhere, Category = "Nest")
	TObjectPtr<UJRHealthComponent> HealthComponent;

	UPROPERTY(EditAnywhere, Category = "Nest")
	TSoftObjectPtr<UStaticMesh> NestMeshAsset;

	UPROPERTY(EditAnywhere, Category = "Nest", meta = (Units = "cm"))
	float TargetHeight = 120.f; // [A-093] o ninho novo tem 1,14 m (2,3 m de largura)

private:
	bool bNestDestroyed = false;
};

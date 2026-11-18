// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRZombieBarricade.generated.h"

class AJREnemyCharacter;
class AJRVehiclePawn;
class AJRZombieBarricade;
class UBoxComponent;
class UStaticMesh;
class UStaticMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnBarricadeBroken, AJRZombieBarricade*, Barricade, float, SpeedKmh);

/**
 * Barricada na estrada: uma fileira de destroços (PropMeshes: carcaças, bloqueios, caixas) com um
 * aglomerado de zumbis parados atrás. A seta X do ator aponta para de onde o carro vem.
 * - Destroços bloqueiam o carro de verdade (colisão). Chegar acima de BreakSpeedKmh "fura": os destroços
 *   viram física, voam e deixam de bater no carro; o carro leva BreakDamage na frente (metade no motor).
 * - Devagar o carro para nos destroços: dê ré e acelere, ou desvie.
 * - Sem PropMeshes vira só o aglomerado de zumbis (furar a RamMinSpeedKmh+ custa RamDamage).
 * Os zumbis só nascem quando o jogador chega a SpawnWhenPlayerWithin (poupa orçamento).
 * Cada destroço tem colisão de caixa própria (do tamanho da malha), então serve qualquer malha,
 * inclusive as de colisão complexa (SM_CarWreck, SM_Barricade), que não poderiam simular física.
 */
UCLASS()
class JOGORESGATE_API AJRZombieBarricade : public AActor
{
	GENERATED_BODY()

public:
	AJRZombieBarricade();

	UFUNCTION(BlueprintCallable, Category = "Barricade")
	void SpawnZombies();

	/** Fura a barricada (destroços voam). Chamado sozinho quando o carro chega rápido. */
	UFUNCTION(BlueprintCallable, Category = "Barricade")
	void BreakBarricade(AJRVehiclePawn* Car, float SpeedKmh);

	UFUNCTION(BlueprintPure, Category = "Barricade")
	bool IsBroken() const { return bRammed; }

	UPROPERTY(BlueprintAssignable, Category = "Barricade")
	FJROnBarricadeBroken OnBarricadeBrokenDelegate;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	void CheckPlayerDistance();
	void BuildProps();
	/** Enquanto o carro está na área: confere velocidade e distância até os destroços. */
	void CheckRam();
	void SleepDebris();

	UFUNCTION()
	void HandleRamOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void HandleRamEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex);

	/** Gancho Blueprint (som/VFX da Etapa 10): barricada furada. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Barricade")
	void OnBarricadeBroken(float SpeedKmh);

	/** Área da barricada (detecta o carro chegando). Recalculada no BeginPlay. */
	UPROPERTY(VisibleAnywhere, Category = "Barricade")
	TObjectPtr<UBoxComponent> RamArea;

	UPROPERTY(EditAnywhere, Category = "Barricade")
	TArray<TSubclassOf<AJREnemyCharacter>> EnemyClasses;

	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (ClampMin = "0", ClampMax = "30"))
	int32 Count = 10;

	/** Largura (eixo Y, atravessa a estrada) e profundidade (eixo X) do aglomerado. */
	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (Units = "cm"))
	float Width = 900.f;

	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (Units = "cm"))
	float Depth = 300.f;

	/** 0 = nasce no BeginPlay. */
	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (Units = "cm"))
	float SpawnWhenPlayerWithin = 15000.f;

	/** Destroços sorteados para a fileira (vazio = barricada só de zumbis). */
	UPROPERTY(EditAnywhere, Category = "Barricade|Props")
	TArray<TObjectPtr<UStaticMesh>> PropMeshes;

	UPROPERTY(EditAnywhere, Category = "Barricade|Props", meta = (ClampMin = "0", ClampMax = "12"))
	int32 PropCount = 3;

	UPROPERTY(EditAnywhere, Category = "Barricade|Props", meta = (ClampMin = "0.1"))
	float PropScale = 1.f;

	/** Massa de cada destroço depois de furado (leve: voa em vez de parar o carro). */
	UPROPERTY(EditAnywhere, Category = "Barricade|Props", meta = (ClampMin = "1"))
	float PropMassKg = 120.f;

	/** Acima disto o carro fura os destroços. Abaixo para neles. */
	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (Units = "km/h"))
	float BreakSpeedKmh = 50.f;

	/** Dano na frente do carro ao furar os destroços (metade vai também para o motor). */
	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (ClampMin = "0"))
	float BreakDamage = 25.f;

	/** Sem destroços: atravessar acima disto conta como "furar a barricada" (dano extra na frente). */
	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (Units = "km/h"))
	float RamMinSpeedKmh = 30.f;

	/** Sem destroços: dano extra na frente do carro (metade vai para o motor) ao furar o aglomerado. */
	UPROPERTY(EditAnywhere, Category = "Barricade", meta = (ClampMin = "0"))
	float RamDamage = 12.f;

private:
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Zombies;
	/** Caixa de colisão de cada destroço (a malha vai presa nela, sem colisão). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UBoxComponent>> PropBodies;
	TWeakObjectPtr<AJRVehiclePawn> CarInArea;
	FTimerHandle CheckTimer;
	FTimerHandle RamTimer;
	FTimerHandle DebrisSleepTimer;
	FRandomStream Random;
	bool bSpawned = false;
	bool bRammed = false;
	bool bHintShown = false;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "JRCheckpoint.generated.h"

class UBoxComponent;
class UArrowComponent;

/**
 * Checkpoint da fase. Também serve de ponto de respawn (AJRGameMode::FindPlayerStart).
 * O checkpoint de transição dispara a saída do veículo (A-013, GDD 6.4).
 */
UCLASS()
class JOGORESGATE_API AJRCheckpoint : public AActor
{
	GENERATED_BODY()

public:
	AJRCheckpoint();

	UFUNCTION(BlueprintPure, Category = "Checkpoint")
	FName GetCheckpointId() const { return CheckpointId; }

	UFUNCTION(BlueprintPure, Category = "Checkpoint")
	EJRLevelStage GetStageOnRespawn() const { return StageOnRespawn; }

	UFUNCTION(BlueprintPure, Category = "Checkpoint")
	bool IsVehicleTransition() const { return bIsVehicleTransition; }

	UFUNCTION(BlueprintPure, Category = "Checkpoint")
	bool IsLevelStart() const { return bIsLevelStart; }

	/** Transform onde o personagem sai do carro / renasce. */
	UFUNCTION(BlueprintPure, Category = "Checkpoint")
	FTransform GetRespawnTransform() const;

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UPROPERTY(VisibleAnywhere, Category = "Checkpoint")
	TObjectPtr<UBoxComponent> Trigger;

	UPROPERTY(VisibleAnywhere, Category = "Checkpoint")
	TObjectPtr<UArrowComponent> RespawnPoint;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint")
	FName CheckpointId = TEXT("Start");

	/** Estágio em que a fase fica ao alcançar/renascer aqui. */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint")
	EJRLevelStage StageOnRespawn = EJRLevelStage::Driving;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint")
	bool bIsVehicleTransition = false;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint")
	bool bIsLevelStart = false;

public:
	/** Armas que o herói já tem ao renascer aqui (o mapa recarrega e zera o inventário). */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Respawn")
	bool bRespawnWithMelee = false;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Respawn")
	bool bRespawnWithPistol = false;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Respawn")
	bool bRespawnWithShotgun = false;

	/** Itens-chave que o jogador já tem ao renascer aqui (ex.: CarKey). */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Respawn")
	TArray<FName> RespawnKeyItems;

	/** Renascer aqui (a pé) estaciona o carro do mapa em VehicleParkLocation/VehicleParkYaw (mundo). */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle")
	bool bParkVehicleOnRespawn = false;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle", meta = (EditCondition = "bParkVehicleOnRespawn"))
	FVector VehicleParkLocation = FVector::ZeroVector;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle", meta = (EditCondition = "bParkVehicleOnRespawn"))
	float VehicleParkYaw = 0.f;

	/** Carro parado aqui (transição) só volta a andar com este item (ex.: Fuel no posto). Vazio = nada. */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle")
	FName VehicleNeedsItem;

	/** Nome mostrado na mensagem ("o galão de gasolina"). */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle")
	FString VehicleNeedsItemLabel = TEXT("combustível");

private:
	bool bReached = false;
};

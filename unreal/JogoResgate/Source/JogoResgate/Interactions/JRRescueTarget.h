// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRRescueTarget.generated.h"

class UAnimMontage;
class UAnimSequenceBase;
class AJRVehiclePawn;
class USkeletalMeshComponent;
class UStaticMeshComponent;

/**
 * Pessoa presa (GDD 4.1, passo 7). Só pode ser libertada no estágio Rescue.
 * Abre a cela (evento BP), alinha jogador e vítima, toca o abraço e conclui a fase.
 */
UCLASS()
class JOGORESGATE_API AJRRescueTarget : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRRescueTarget();

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	UFUNCTION(BlueprintPure, Category = "Rescue")
	FName GetRescueId() const { return RescueId; }

	UFUNCTION(BlueprintPure, Category = "Rescue")
	bool IsRescued() const { return bRescued; }

	/** [A-075] Já está sentada no buggy (carona). */
	UFUNCTION(BlueprintPure, Category = "Rescue|Follow")
	bool IsInVehicle() const { return BoardedVehicle.IsValid(); }

	virtual void Tick(float DeltaSeconds) override;

protected:
	/** Animação/efeito de abrir a grade (implementado no BP). */
	UFUNCTION(BlueprintImplementableEvent, Category = "Rescue")
	void OnCageOpened();

	UFUNCTION(BlueprintImplementableEvent, Category = "Rescue")
	void OnRescueCompleted();

	void FinishRescue();

	// ---- [A-075] Depois de solta (L01 v3): segue o herói a pé e entra no buggy quando ele entra.
	/** Começa a seguir (liga o Tick). */
	void StartFollowing();

	/** Anda a malha da vítima até perto do herói (sem física: traço no chão, sem colisão). */
	void TickFollow(float DeltaSeconds, const APawn* Hero);

	/** Esconde a vítima e senta a cópia no banco do carona do buggy (fade curto esconde o "teleporte"). */
	void BoardVehicle(AJRVehiclePawn* Vehicle);

	/** Troca a animação da vítima só quando muda (0 parada, 1 andando, 2 correndo). */
	void SetFollowGait(int32 Gait, float PlayRate);

	/** Segue o herói a pé depois de solta (só no L01 v3, bCompleteLevelOnRescue = false). */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow")
	bool bFollowAfterRescue = true;

	/** Entra no buggy quando o herói entra (de qualquer distância; sem andar a tempo, aparece sentada com um fade). */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow")
	bool bBoardVehicleWithHero = true;

	/** Para a esta distância do herói. */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "cm"))
	float FollowStopDistance = 260.f;

	/** Acima disto ela corre. */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "cm"))
	float FollowRunDistance = 700.f;

	/** Ficou para trás demais (fora da tela): reaparece atrás do herói. */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "cm"))
	float FollowCatchUpDistance = 4000.f;

	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "cm/s"))
	float FollowWalkSpeed = 170.f;

	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "cm/s"))
	float FollowRunSpeed = 430.f;

	/** Velocidade natural das animações (para casar o passo com o deslocamento). */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "cm/s"))
	float WalkAnimSpeed = 150.f;

	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "cm/s"))
	float RunAnimSpeed = 400.f;

	/** Giro da malha em relação à direção do movimento (malhas Mixamo/UE olham para +Y: -90). */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow", meta = (Units = "Degrees"))
	float VictimMeshYawOffset = -90.f;

	/** Animações da sobrevivente (geradas por tools/unreal/setup_passenger.py). Sem andar/correr: ela espera e embarca com o fade. */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow")
	TSoftObjectPtr<UAnimSequenceBase> FollowWalkAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Survivor/Anims/A_NPC_Sobrevivente_Andar.A_NPC_Sobrevivente_Andar")));

	UPROPERTY(EditAnywhere, Category = "Rescue|Follow")
	TSoftObjectPtr<UAnimSequenceBase> FollowRunAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Survivor/Anims/A_NPC_Sobrevivente_Correr.A_NPC_Sobrevivente_Correr")));

	/** Sentada no buggy. Sem ela: a pose atual com as pernas escondidas. */
	UPROPERTY(EditAnywhere, Category = "Rescue|Follow")
	TSoftObjectPtr<UAnimSequenceBase> PassengerSitAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Survivor/Anims/A_NPC_Sobrevivente_Sentada.A_NPC_Sobrevivente_Sentada")));

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<UStaticMeshComponent> CageMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<USkeletalMeshComponent> VictimMesh;

	/** Onde o jogador é posicionado para o abraço. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<USceneComponent> PlayerAlignPoint;

	UPROPERTY(EditAnywhere, Category = "Rescue")
	FName RescueId = TEXT("Victim01");

	/** true: libertar conclui a fase (L01 v2). false (L01 v3): o jogador ainda dirige até o portão de saída. */
	UPROPERTY(EditAnywhere, Category = "Rescue")
	bool bCompleteLevelOnRescue = true;

	UPROPERTY(EditDefaultsOnly, Category = "Rescue")
	TObjectPtr<UAnimMontage> VictimHugMontage;

	UPROPERTY(EditDefaultsOnly, Category = "Rescue")
	FText InteractionText;

	/** Usado se nenhuma montage tiver duração. */
	UPROPERTY(EditDefaultsOnly, Category = "Rescue", meta = (Units = "s"))
	float FallbackHugDuration = 3.f;

private:
	FTimerHandle FinishTimer;
	bool bRescued = false;
	TWeakObjectPtr<AController> Rescuer;
	// [A-075]
	bool bFollowing = false;
	int32 CurrentGait = -1;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequenceBase> IdleAnimCache;

	UPROPERTY(Transient)
	TObjectPtr<UAnimSequenceBase> WalkAnimCache;

	UPROPERTY(Transient)
	TObjectPtr<UAnimSequenceBase> RunAnimCache;
	TWeakObjectPtr<AJRVehiclePawn> BoardedVehicle;
};

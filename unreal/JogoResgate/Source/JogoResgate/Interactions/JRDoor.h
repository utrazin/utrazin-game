// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRDoor.generated.h"

class UBoxComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * [A-076] Porta de verdade nos vãos das construções com interior (loja, casas, oficina, galpão...).
 * O herói aperta E e a folha gira na dobradiça com uma animação curta (acelera, passa um pouco do ponto e assenta),
 * sempre para o lado de longe de quem abriu. Zumbis e a sobrevivente abrem sozinhos ao chegar perto (a navmesh passa
 * pela porta: a folha não afeta a navegação). Vão largo (>= 1,7 m) vira porta dupla; portões muito largos
 * (bStartOpen) já começam abertos para o buggy passar.
 * Eixos do ator: X = normal da parede, Y = ao longo da parede, origem no chão no centro do vão.
 * A malha da folha (SM_INT_Porta*) tem 1 m de largura em +Y a partir da dobradiça e 2,2 m de altura; o ator estica
 * para o tamanho do vão. Colocada por tools/unreal/build_interiors_l01.py.
 */
UCLASS()
class JOGORESGATE_API AJRDoor : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRDoor();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void Tick(float DeltaSeconds) override;

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	/** Abre para longe de quem está em FromLocation. */
	UFUNCTION(BlueprintCallable, Category = "Door")
	void OpenAwayFrom(const FVector& FromLocation);

	UFUNCTION(BlueprintCallable, Category = "Door")
	void Close();

	bool IsOpen() const { return bOpen; }

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleDetectOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	void ApplyLayout();
	void SetLeafYaw(float Yaw);
	void SetLeavesBlockPawns(bool bBlock);

	UPROPERTY(VisibleAnywhere, Category = "Door")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, Category = "Door")
	TObjectPtr<USceneComponent> HingeA;

	UPROPERTY(VisibleAnywhere, Category = "Door")
	TObjectPtr<UStaticMeshComponent> LeafA;

	UPROPERTY(VisibleAnywhere, Category = "Door")
	TObjectPtr<USceneComponent> HingeB;

	UPROPERTY(VisibleAnywhere, Category = "Door")
	TObjectPtr<UStaticMeshComponent> LeafB;

	/** Caixa dos dois lados da porta: zumbi ou sobrevivente entrando nela abre a porta. */
	UPROPERTY(VisibleAnywhere, Category = "Door")
	TObjectPtr<UBoxComponent> Detect;

	/** Malha da folha (1 m de largura em +Y a partir da dobradiça, 2,2 m de altura). */
	UPROPERTY(EditAnywhere, Category = "Door")
	TObjectPtr<UStaticMesh> LeafMesh;

	/** Largura do vão (a folha fica 7 cm menor de cada lado por causa do batente). */
	UPROPERTY(EditAnywhere, Category = "Door", meta = (Units = "cm", ClampMin = "60"))
	float OpeningWidth = 130.f;

	/** Altura do vão. */
	UPROPERTY(EditAnywhere, Category = "Door", meta = (Units = "cm", ClampMin = "150"))
	float OpeningHeight = 225.f;

	/** Duas folhas (vão largo). */
	UPROPERTY(EditAnywhere, Category = "Door")
	bool bDouble = false;

	/** Começa aberta (portão de oficina/galpão por onde o buggy passa). */
	UPROPERTY(EditAnywhere, Category = "Door")
	bool bStartOpen = false;

	/** O herói pode fechar de novo com E. */
	UPROPERTY(EditAnywhere, Category = "Door")
	bool bAllowClose = true;

	/** Inimigos (e a sobrevivente) abrem a porta sozinhos ao chegar perto. */
	UPROPERTY(EditAnywhere, Category = "Door")
	bool bAutoOpenForAI = true;

	/** Ângulo da porta aberta. */
	UPROPERTY(EditAnywhere, Category = "Door", meta = (Units = "Degrees", ClampMin = "30", ClampMax = "170"))
	float OpenAngle = 100.f;

	/** Tempo da animação de abrir. */
	UPROPERTY(EditAnywhere, Category = "Door", meta = (Units = "s", ClampMin = "0.1"))
	float OpenTime = 0.55f;

	/** Tempo da animação de fechar (um pouco mais rápida, batendo). */
	UPROPERTY(EditAnywhere, Category = "Door", meta = (Units = "s", ClampMin = "0.1"))
	float CloseTime = 0.4f;

	/** Quanto passa do ponto antes de assentar (0 = sem balanço). */
	UPROPERTY(EditAnywhere, Category = "Door", meta = (ClampMin = "0", ClampMax = "0.3"))
	float Overshoot = 0.08f;

private:
	float CurrentYaw = 0.f;
	float FromYaw = 0.f;
	float TargetYaw = 0.f;
	float AnimTime = 0.f;
	float AnimDuration = 0.f;
	bool bOpen = false;
	bool bAnimating = false;
};

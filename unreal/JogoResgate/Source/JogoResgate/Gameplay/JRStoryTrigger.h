// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRStoryTrigger.generated.h"

class UBoxComponent;

/**
 * Momento da história: quando o jogador entra, mostra uma fala/aviso e passa a TAREFA atual do HUD
 * (ex.: "Pegue o graveto", "Procure a chave"). Uma vez por fase.
 * [A-064] A tarefa vira o texto principal do painel OBJETIVO e o marcador/minimapa apontam para TaskTarget.
 * Ela termina sozinha: item pego, baú aberto, portão aberto, sobrevivente solta, carro com o jogador ou,
 * para qualquer outro alvo, jogador a menos de TaskReachRadius. Aí vem a próxima da fila ou o objetivo geral.
 */
UCLASS()
class JOGORESGATE_API AJRStoryTrigger : public AActor
{
	GENERATED_BODY()

public:
	AJRStoryTrigger();

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UPROPERTY(VisibleAnywhere, Category = "Story")
	TObjectPtr<UBoxComponent> Box;

	/** Fala/aviso mostrado ao entrar. */
	UPROPERTY(EditAnywhere, Category = "Story")
	FString Message;

	/** Nova dica de objetivo (vazio = mantém). */
	UPROPERTY(EditAnywhere, Category = "Story")
	FString ObjectiveHint;

	/** Só dispara a pé (true) ou também no carro. */
	UPROPERTY(EditAnywhere, Category = "Story")
	bool bOnFootOnly = false;

	/** [A-064] Para onde a tarefa aponta (item, baú, carro, ponto). Vazio = o marcador segue o objetivo geral. */
	UPROPERTY(EditInstanceOnly, Category = "Story")
	TObjectPtr<AActor> TaskTarget;

	/** [A-064] Alvo que não é item, baú, portão, sobrevivente nem carro: a tarefa termina ao chegar a esta distância. */
	UPROPERTY(EditAnywhere, Category = "Story", meta = (Units = "cm", ClampMin = "100"))
	float TaskReachRadius = 1500.f;

	/** Portão de saída: conclui a fase (só depois de libertar todos os AJRRescueTarget do mapa). */
	UPROPERTY(EditAnywhere, Category = "Story")
	bool bCompletesLevel = false;

private:
	bool bDone = false;
};

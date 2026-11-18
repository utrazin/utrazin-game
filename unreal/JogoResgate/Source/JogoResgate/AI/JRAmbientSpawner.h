// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "JRAmbientSpawner.generated.h"

class AJREnemyCharacter;

/**
 * "Zumbis chegando": enquanto o jogador está no estágio configurado, de tempos em tempos
 * aparecem pequenos grupos fora da visão dele, que já vêm atrás. Garante que nenhum trecho
 * fique vazio. Respeita um teto de vivos. Sem Tick (timer).
 * OBSOLETO (Etapa 3): substituído pelo AJRAIDirector (ritmo Subida/Pico/Calmaria, zonas AJRDirectorZone).
 * Continua compilando porque build_l01.py ainda o coloca no L01; com bYieldToDirector (padrão) ele fica
 * quieto sempre que houver um diretor ativo. Não use em mapas novos: rode tools/unreal/setup_ai_director.py.
 */
UCLASS()
class JOGORESGATE_API AJRAmbientSpawner : public AActor
{
	GENERATED_BODY()

public:
	AJRAmbientSpawner();

protected:
	virtual void BeginPlay() override;
	void TrySpawnGroup();
	bool FindSpawnPoint(const APawn* Player, FVector& OutPoint) const;
	void ScheduleNext();

	UPROPERTY(EditAnywhere, Category = "Ambient")
	TArray<TSubclassOf<AJREnemyCharacter>> EnemyClasses;

	/** Estágio da fase em que o spawner trabalha (ex.: OnFoot). */
	UPROPERTY(EditAnywhere, Category = "Ambient")
	EJRLevelStage ActiveStage = EJRLevelStage::OnFoot;

	UPROPERTY(EditAnywhere, Category = "Ambient", meta = (Units = "s"))
	float MinInterval = 7.f;

	UPROPERTY(EditAnywhere, Category = "Ambient", meta = (Units = "s"))
	float MaxInterval = 13.f;

	UPROPERTY(EditAnywhere, Category = "Ambient")
	int32 MinGroup = 1;

	UPROPERTY(EditAnywhere, Category = "Ambient")
	int32 MaxGroup = 3;

	UPROPERTY(EditAnywhere, Category = "Ambient", meta = (Units = "cm"))
	float MinDistance = 1800.f;

	UPROPERTY(EditAnywhere, Category = "Ambient", meta = (Units = "cm"))
	float MaxDistance = 3200.f;

	/** Teto de zumbis vivos criados por este spawner. */
	UPROPERTY(EditAnywhere, Category = "Ambient")
	int32 MaxAlive = 8;

	/** Ângulo (graus) à frente da câmera em que NÃO se spawna (nasce fora da visão). */
	UPROPERTY(EditAnywhere, Category = "Ambient")
	float HiddenConeHalfAngle = 55.f;

	/** Se houver um AJRAIDirector ativo no estágio atual, este spawner fica quieto (o diretor manda no ritmo). */
	UPROPERTY(EditAnywhere, Category = "Ambient")
	bool bYieldToDirector = true;

private:
	TArray<TWeakObjectPtr<AJREnemyCharacter>> Spawned;
	FTimerHandle Timer;
	FRandomStream Random;
};

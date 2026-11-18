// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "JRInteractionCameraComponent.generated.h"

class ACameraActor;
class APlayerController;

/** Enquadramentos prontos das interações (A-058). */
UENUM(BlueprintType)
enum class EJRInteractionShot : uint8
{
	Chest,         // abrir baú: 3/4 de lado, altura do baú
	PickupGround,  // pegar arma do chão: ângulo baixo, de frente
	VehicleExit,   // sair do carro: aberto, de lado
	VehicleEnter,  // entrar no carro (reservado: o herói some na hora; o controller faz só a mistura de câmeras)
	GatePlant,     // armar o explosivo: por trás e de cima
	Rescue,        // libertar a sobrevivente: plano com os dois
	FuelPump       // bomba de gasolina: 3/4 do outro lado
};

/** Um enquadramento: posição da câmera em relação ao foco, no referencial do herói virado para o objeto. */
USTRUCT(BlueprintType)
struct FJRInteractionShotFraming
{
	GENERATED_BODY()

	/** cm; X = para o objeto, Y = direita do herói, Z = cima (a partir do ponto de foco). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	FVector CameraOffset = FVector(-120.f, 160.f, 70.f);

	/** Altura do foco acima dos pés do herói (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot")
	float FocusHeight = 90.f;

	/** Foco entre o herói (0) e o objeto (1); 0,5 enquadra os dois. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (ClampMin = "0", ClampMax = "1"))
	float FocusTowardTarget = 0.4f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (Units = "Degrees"))
	float FOV = 60.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (Units = "s"))
	float BlendIn = 0.45f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Shot", meta = (Units = "s"))
	float BlendOut = 0.5f;
};

/**
 * Câmera cinematográfica das interações (A-058): ao abrir um baú, pegar arma do chão, armar o explosivo,
 * sair do carro, libertar a sobrevivente... a câmera vai suave (entrada/saída suavizadas) para um enquadramento
 * fixo, o jogador não anda/olha/atira, e ao fim da animação tudo volta ao normal.
 * Terceira pessoa: câmera temporária (ACameraActor) + SetViewTargetWithBlend.
 * Primeira pessoa: NÃO sai do corpo: só vira o olhar suave para o objeto (Tick ligado só nesse caso).
 * Pula a cena se houver inimigo vivo a menos de SafetyRadius (menos onde o chamador pede, ex.: resgate).
 */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRInteractionCameraComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRInteractionCameraComponent();

	/**
	 * Toca o enquadramento por ActionSeconds (duração da animação; a volta começa um pouco antes do fim).
	 * BlendFrom: ator cuja câmera é o ponto de partida (ex.: o carro ao sair). Retorna false se pulou.
	 */
	UFUNCTION(BlueprintCallable, Category = "InteractionCamera")
	bool PlayShot(EJRInteractionShot Shot, AActor* Target, float ActionSeconds, bool bIgnoreEnemies = false, AActor* BlendFrom = nullptr);

	/** Volta para a câmera normal (bInstant = corte seco: morte, troca de pawn). */
	UFUNCTION(BlueprintCallable, Category = "InteractionCamera")
	void StopShot(bool bInstant);

	UFUNCTION(BlueprintPure, Category = "InteractionCamera")
	bool IsShotActive() const { return bShotActive; }

	/** Inimigo vivo perto (as cenas são puladas por segurança). */
	bool IsEnemyNearby() const;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	void FinishHold();
	void ReleaseInput();
	void DestroyShotCamera();

	/** Liga/desliga todas as cenas (opção do jogador no futuro). */
	UPROPERTY(EditAnywhere, Category = "InteractionCamera")
	bool bShotsEnabled = true;

	/** Inimigo vivo a menos disto: sem cena (o jogador precisa da câmera livre). */
	UPROPERTY(EditAnywhere, Category = "InteractionCamera", meta = (Units = "cm"))
	float SafetyRadius = 500.f;

	/** Primeira pessoa: rapidez com que o olhar vira para o objeto. */
	UPROPERTY(EditAnywhere, Category = "InteractionCamera")
	float FirstPersonLookSpeed = 5.f;

	UPROPERTY(EditAnywhere, Category = "InteractionCamera")
	TMap<EJRInteractionShot, FJRInteractionShotFraming> Shots;

private:
	UPROPERTY(Transient)
	TObjectPtr<ACameraActor> ShotCamera;

	TWeakObjectPtr<APlayerController> LockedController;
	FTimerHandle HoldTimer;
	FTimerHandle CleanupTimer;
	FRotator FirstPersonLookAt = FRotator::ZeroRotator;
	float ActiveBlendOut = 0.5f;
	bool bShotActive = false;
	bool bInputLocked = false;
	bool bFirstPersonShot = false;
};

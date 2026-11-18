// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "Interactions/JRInteractable.h"
#include "Vehicles/JRVehicleDamageModel.h"
#include "Vehicles/JRZombieCarTypes.h"
#include "JRVehiclePawn.generated.h"

class AJREnemyCharacter;
class UCameraComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USoundBase;
class UInputAction;
class UJRVehicleDamageComponent;
class UAnimSequenceBase;
class UPhysicalMaterial;
class UPrimitiveComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class USpringArmComponent;
class UStaticMeshComponent;
struct FMinimalViewInfo;
struct FInputActionValue;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_FourParams(FJROnZombieCarEvent, EJRZombieCarEvent, Event, AActor*, Zombie, FVector, Location, float, Value);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnVehicleDamageFXStateChanged, EJRVehicleDamageFXState, NewState);

/**
 * SUV jogável (A-008) sobre Chaos Vehicles. Tuning de rodas/motor fica no Blueprint
 * derivado (BP_Vehicle_SUV) e em docs/gameplay/VEHICLE.md.
 */
UCLASS()
class JOGORESGATE_API AJRVehiclePawn : public AWheeledVehiclePawn, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRVehiclePawn();

	// ---- Entrar a pé (E perto do carro): ver AJRPlayerController::RequestEnterVehicle
	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	/** Religa o carro estacionado (depois de ParkAndDisable/StopThenExit). */
	UFUNCTION(BlueprintCallable, Category = "Vehicle")
	void EnableDriving();

	/** Teleporta parado (zera velocidades): respawn e estacionar no checkpoint. */
	void MoveToTransform(const FTransform& NewTransform);

	UFUNCTION(BlueprintPure, Category = "Vehicle|Enter")
	FName GetRequiredKeyItem() const { return RequiredKeyItem; }

	/** Item que falta para o carro andar de novo (ex.: Fuel no posto). None = nenhum. */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Enter")
	FName GetPendingRequiredItem() const { return PendingRequiredItem; }

	const FString& GetPendingRequiredItemLabel() const { return PendingRequiredItemLabel; }

	/** [A-075] Item Fuel pendente = tanque seco (combustível vai a 0 e o motor morre). */
	void SetPendingRequiredItem(FName Item, const FString& Label);

	/** [A-075] Entregou o item pendente. Se era o Fuel, o galão enche o tanque. */
	void ClearPendingRequiredItem();

	// ---- [A-075] Combustível (tanque 0..1)
	UFUNCTION(BlueprintPure, Category = "Vehicle|Fuel")
	float GetFuel() const { return FuelLevel; }

	/** Na reserva (abaixo de FuelReserveLevel): o HUD pisca e toca o alerta. */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Fuel")
	bool IsFuelReserve() const { return FuelLevel <= FuelReserveLevel; }

	/** Nível da reserva (para a marca no medidor do HUD). */
	float GetFuelReserveMark() const { return FuelReserveLevel; }

	/** Tanque no fim (FuelLimpLevel): o motor engasga e perde força, mas nunca prende o jogador longe do posto. */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Fuel")
	bool IsFuelSputtering() const { return !bEngineDead && FuelLevel <= FuelLimpLevel + KINDA_SMALL_NUMBER; }

	/** Motor morto: tanque seco esperando o galão (item Fuel pendente). Acelerador não faz nada. */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Fuel")
	bool IsEngineDead() const { return bEngineDead; }

	/** Põe combustível (fração do tanque). Religa o motor se ele tinha morrido. */
	UFUNCTION(BlueprintCallable, Category = "Vehicle|Fuel")
	void Refuel(float Amount = 1.f);

	// ---- [A-075] Passageiro (sobrevivente resgatada), só visual
	/**
	 * Senta uma cópia visual de Source (malha e materiais) no banco do carona (caixa ao lado do banco central).
	 * bAnimIsSitting: Anim é a pose sentada (esconde só as canelas); false = pose em pé (esconde as pernas inteiras).
	 */
	void SetPassenger(const USkeletalMeshComponent* Source, UAnimSequenceBase* Anim, bool bAnimIsSitting);

	UFUNCTION(BlueprintCallable, Category = "Vehicle|Passenger")
	void ClearPassenger();

	UFUNCTION(BlueprintPure, Category = "Vehicle|Passenger")
	bool HasPassenger() const { return bHasPassenger; }

	/** Zera inputs, freia e desativa o veículo após a saída do jogador (A-015). */
	UFUNCTION(BlueprintCallable, Category = "Vehicle")
	void ParkAndDisable();

	UFUNCTION(BlueprintPure, Category = "Vehicle")
	UJRVehicleDamageComponent* GetDamageComponent() const { return DamageComponent; }

	UFUNCTION(BlueprintPure, Category = "Vehicle")
	FTransform GetExitTransform() const;

	/** Banco do motorista (onde a animação de sair do carro começa). */
	UFUNCTION(BlueprintPure, Category = "Vehicle")
	FTransform GetSeatTransform() const;

	/** Freia até quase parar (ou até ExitStopTimeout) e só então tira o jogador do carro. */
	void StopThenExit(const FTransform& FallbackTransform);

	UFUNCTION(BlueprintPure, Category = "Vehicle")
	float GetSpeedKmh() const;

	/** Carga de nitro 0..1. */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Nitro")
	float GetNitro() const { return NitroCharge; }

	UFUNCTION(BlueprintPure, Category = "Vehicle|Nitro")
	bool IsNitroActive() const { return bNitroActive; }

	/** Desvira o carro (tecla R): de pé, 1,5 m acima do chão, mesma direção. False se rápido demais ou em recarga. */
	UFUNCTION(BlueprintCallable, Category = "Vehicle|Recover")
	bool RecoverUpright() { return BeginRecover(true); }

	UFUNCTION(BlueprintPure, Category = "Vehicle|Recover")
	bool IsRecovering() const { return bRecovering; }

	UFUNCTION(BlueprintCallable, Category = "Vehicle|Nitro")
	void AddNitro(float Amount) { NitroCharge = FMath::Clamp(NitroCharge + Amount, 0.f, 1.f); }

	/** Mostra/esconde o motorista sentado (cópia visual do herói selecionado). */
	UFUNCTION(BlueprintCallable, Category = "Vehicle|Driver")
	void SetDriverVisible(bool bVisible);

	/** Copia malha, materiais e animação de dirigir do herói selecionado para o DriverMesh. */
	UFUNCTION(BlueprintCallable, Category = "Vehicle|Driver")
	void RefreshDriver();

	/**
	 * Primeira pessoa no carro: câmera na cabeça do motorista (DriverMesh), vendo o volante e o capô.
	 * Ligada pela tecla V (AJRPlayerController). Sem motorista visível, fica a câmera de trás.
	 */
	UFUNCTION(BlueprintCallable, Category = "Camera|FirstPerson")
	void SetFirstPersonView(bool bEnable, bool bInstant = false);

	UFUNCTION(BlueprintPure, Category = "Camera|FirstPerson")
	bool IsFirstPersonView() const { return bFirstPersonWanted; }

	/** Câmera final: a de trás (SpringArm) misturada com a da cabeça do motorista. */
	virtual void CalcCamera(float DeltaTime, FMinimalViewInfo& OutResult) override;

	/**
	 * Distância (cm) de um ponto do mundo até a caixa da carroceria (0 = encostado ou dentro).
	 * OutClosestPoint (opcional) recebe o ponto da lataria mais próximo.
	 */
	float GetDistanceToBody(const FVector& WorldPoint, FVector* OutClosestPoint = nullptr) const;

	/** Reserva o ponto de agarre livre mais próximo (capô, esquerda, direita). INDEX_NONE se não der. */
	int32 TryReserveGrabSlot(AJREnemyCharacter* Zombie);

	/** Libera o ponto ocupado por este zumbi (chamado pelo próprio zumbi ao soltar ou morrer). */
	void ReleaseGrabSlot(AJREnemyCharacter* Zombie);

	USceneComponent* GetGrabPoint(int32 Slot) const;

	/** Zona do carro que o zumbi agarrado neste ponto danifica. */
	EJRVehicleZone GetGrabZone(int32 Slot) const;

	UFUNCTION(BlueprintPure, Category = "Vehicle|Zombies")
	int32 GetGrabberCount() const;

	/** Solta todos os zumbis agarrados. bKill = arremessa (ragdoll) e mata. */
	UFUNCTION(BlueprintCallable, Category = "Vehicle|Zombies")
	void ReleaseAllGrabbers(bool bKill);

	/** Cada zumbi atropelado tira esta fração da velocidade, com teto: a horda freia mas não para o carro. */
	void ApplyZombieDrag(float Fraction);

	/** Explode o carro (integridade zerou): dano em área, arremessa zumbis, jogador sai a pé ou falha. */
	UFUNCTION(BlueprintCallable, Category = "Vehicle|Damage FX")
	void Explode();

	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage FX")
	bool IsWrecked() const { return bExploded; }

	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage FX")
	EJRVehicleDamageFXState GetDamageFXState() const { return DamageFXState; }

	/** Bomba armada (jogador saiu do carro pegando fogo)? */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage FX")
	bool IsCarBombArmed() const;

	/**
	 * Avisa um evento zumbi x carro: dispara OnZombieCarEvent (delegate) e BP_OnZombieCarEvent (Blueprint).
	 * Chamado pelos zumbis, pela barricada e pelo próprio carro. Gancho de som/VFX (Etapa 10).
	 */
	UFUNCTION(BlueprintCallable, Category = "Vehicle|Events")
	void NotifyZombieCarEvent(EJRZombieCarEvent Event, AActor* Zombie, FVector Location, float Value);

	UPROPERTY(BlueprintAssignable, Category = "Vehicle|Events")
	FJROnZombieCarEvent OnZombieCarEvent;

	/** Mudou o estado visual de dano (Intact, Smoking, Burning, Wrecked). */
	UPROPERTY(BlueprintAssignable, Category = "Vehicle|Events")
	FJROnVehicleDamageFXStateChanged OnDamageFXStateChanged;

	/** Acima disto os zumbis não conseguem agarrar o carro. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Vehicle|Zombies", meta = (Units = "km/h"))
	float GrabMaxSpeedKmh = 40.f;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void PossessedBy(AController* NewController) override;
	virtual void UnPossessed() override;

	/** Ajudas arcade: segura a derrapagem lateral (anti "gelo") quando as rodas estão no chão. */
	void ApplyGripAssist(float DeltaSeconds, bool bGrounded);
	bool IsNearGround() const;

	/** Freio arcade: desaceleração extra garantida com o freio (ou com o acelerador andando de ré), só no chão. */
	void ApplyBrakeAssist(bool bGrounded);

	/** Torque que mantém o carro em pé quando ele inclina demais (no chão e no ar), limitado. */
	void ApplyRollStabilization(bool bGrounded);

	/** Conta o tempo capotado/de lado e devagar; passou de AutoRecoverDelay, desvira sozinho. */
	void TickAutoRecover(float DeltaSeconds);

	/** Começa a desvirar (bManual = tecla R). False se não pode agora. */
	bool BeginRecover(bool bManual);

	/** Leva o carro suavemente até a pose de pé (teleporte físico a cada frame). */
	void TickRecover(float DeltaSeconds);

	/** Volante gira e motorista inclina com o volante (só visual). */
	void UpdateSteeringVisuals(float DeltaSeconds);

	/** Batida de raspão na parede: desliza junto à parede em vez de parar (estilo corrida). */
	UFUNCTION()
	void HandleVehicleHit(AActor* SelfActor, AActor* OtherActor, FVector NormalImpulse, const FHitResult& Hit);

	/** Gancho para faísca/som de raspão (implementar no BP depois). AngleDeg = ângulo entre carro e parede. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Vehicle|Walls")
	void OnWallScrape(FVector ImpactPoint, float SpeedKmh, float AngleDeg);

	/** Gancho Blueprint para som/VFX de cada evento zumbi x carro (mesmo conteúdo do delegate OnZombieCarEvent). */
	UFUNCTION(BlueprintImplementableEvent, Category = "Vehicle|Events")
	void BP_OnZombieCarEvent(EJRZombieCarEvent Event, AActor* Zombie, FVector Location, float Value);

	/** Gancho Blueprint: fumaça/fogo/destruído (para VFX e som de verdade depois). */
	UFUNCTION(BlueprintImplementableEvent, Category = "Vehicle|Events")
	void OnDamageStateChanged(EJRVehicleDamageFXState NewState);

	/** Volante com o input do jogador: menos curva em alta velocidade + puxão do pneu furado e dos zumbis agarrados. */
	float ComputeSteering(float RawInput) const;

	/** Puxão no volante dos zumbis agarrados (lateral puxa para o seu lado; no capô balança). */
	float GetGrabSteerBias() const;

	void HandleThrottle(const FInputActionValue& Value);
	void HandleBrake(const FInputActionValue& Value);
	void HandleSteer(const FInputActionValue& Value);
	void HandleSteerReleased(const FInputActionValue& Value);
	void HandleHandbrake(const FInputActionValue& Value);
	void HandleLook(const FInputActionValue& Value);
	void HandleNitro(const FInputActionValue& Value);
	void HandleReset(const FInputActionValue& Value);
	void TickNitro();

	/** Valor do freio/acelerador que vai para o Chaos (guardado para o freio arcade). */
	void ApplyThrottleInput(float Value);
	void ApplyBrakeInput(float Value);
	void ApplyHandbrakeInput(bool bHeld);

	/** Teclas reserva (só se a Input Action correspondente não estiver no BP): S/seta baixo, espaço, R. */
	void HandleBrakeKeyPressed() { ApplyBrakeInput(1.f); }
	void HandleBrakeKeyReleased() { ApplyBrakeInput(0.f); }
	void HandleHandbrakeKeyPressed() { ApplyHandbrakeInput(true); }
	void HandleHandbrakeKeyReleased() { ApplyHandbrakeInput(false); }
	void HandleResetKey() { BeginRecover(true); }
	/** [A-078] E (ou X/quadrado no controle) desce do carro: freia até parar e o herói sai do lado. */
	void HandleExitKey();
	void ZeroInputs(bool bApplyHandbrake);

	UFUNCTION()
	void HandleVehicleDisabled();

	/** Fumaça (<50%), fogo (<25%) conforme a integridade. */
	UFUNCTION()
	void HandleIntegrityChanged(float Integrity);

	/** Posiciona pontos de agarre, fumaça e fogo pelos limites da malha do chassi. */
	void PlaceBodyPointsFromChassis();

	/** Sacudir os zumbis agarrados (curva forte, velocidade alta) e frear o carro com o peso deles. */
	void TickGrabbers(float DeltaSeconds);

	void EndExplosionFlash();

	/** Fogo queimando o motor (1 vez por segundo). */
	void TickBurn();

	void SleepPhysics();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<USpringArmComponent> SpringArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<UJRVehicleDamageComponent> DamageComponent;

	/** Carroceria visual (estática), presa ao esqueleto da suspensão. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> ChassisMesh;

	/** Pneus visuais nos sockets VisWheel_* (FL, FR, BL, BR). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireFL;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireFR;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireBL;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireBR;

	/** Onde o personagem aparece ao sair do carro (lado do motorista). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<USceneComponent> ExitPoint;

	/** Banco do motorista. Ajuste no BP se a animação de sair não começar sentada no banco. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<USceneComponent> SeatPoint;

	/** Quadril do motorista (preso à carroceria, coordenadas da malha SM_Car_AlienBuggy). Inclina nas curvas. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Driver")
	TObjectPtr<USceneComponent> DriverPivot;

	/** Motorista visual (sem colisão), escala de mundo 1. Ajuste o DriverPivot no BP se ficar fora do banco. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Driver")
	TObjectPtr<USkeletalMeshComponent> DriverMesh;

	/** Volante separado (SM_Car_AlienBuggy_SteeringWheel); o eixo local X é o eixo do volante. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> SteeringWheelMesh;

	/** Ossos escondidos no motorista (canelas/pés atravessariam o assoalho do buggy). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Driver")
	TArray<FName> DriverHiddenBones = { TEXT("calf_l"), TEXT("calf_r") };

	/** Inclinação lateral do motorista com volante todo virado. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Driver", meta = (Units = "Degrees"))
	float DriverLeanDegrees = 8.f;

	/** Giro do tronco/cabeça do motorista para dentro da curva. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Driver", meta = (Units = "Degrees"))
	float DriverYawDegrees = 6.f;

	/** Osso da cabeça do motorista seguido pela câmera em primeira pessoa. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson")
	FName FPHeadBone = TEXT("head");

	/** Olhos em relação à cabeça do motorista (cm, no sentido do carro): X = frente, Y = lado, Z = cima. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson")
	FVector FPEyeOffset = FVector(10.f, 0.f, 8.f);

	/** 0 = presa na cabeça (balança com o motorista); 1 = ponto estável. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (ClampMin = "0", ClampMax = "1"))
	float FPStabilizeAlpha = 0.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (ClampMin = "0.1"))
	float FPStabilizeSpeed = 6.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "Degrees", ClampMin = "60", ClampMax = "120"))
	float FPFov = 90.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "s"))
	float FPBlendTime = 0.25f;

	/** Quanto a câmera acompanha a inclinação lateral do carro (0 = horizonte sempre reto). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (ClampMin = "0", ClampMax = "1"))
	float FPRollFollow = 0.5f;

	/** Olhar livre para os lados/cima/baixo a partir da frente do carro. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "Degrees"))
	float FPMaxLookYaw = 120.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "Degrees"))
	float FPMinLookPitch = -60.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "Degrees"))
	float FPMaxLookPitch = 45.f;

	/** Sem mexer o mouse/analógico por este tempo, o olhar volta para a frente. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "s"))
	float FPRecenterDelay = 1.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson")
	float FPRecenterSpeed = 3.f;

	/** Ossos do motorista escondidos em primeira pessoa (a câmera fica dentro da cabeça). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson")
	TArray<FName> FPHiddenBones = { TEXT("head") };

	// ---- [A-073] Sensação de dirigir (só câmera: nada aqui mexe na física do carro)
	/** FOV extra na velocidade máxima de referência (sensação de velocidade). 0 = desliga. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (Units = "Degrees", ClampMin = "0", ClampMax = "20"))
	float DriveSpeedFOVBonus = 9.f;

	/** Abaixo disto o FOV não muda. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (Units = "km/h", ClampMin = "0"))
	float DriveFOVStartKmh = 35.f;

	/** Nesta velocidade o FOV extra está todo aplicado. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (Units = "km/h", ClampMin = "1"))
	float DriveFOVFullKmh = 120.f;

	/** Rapidez com que o FOV acompanha a velocidade (baixo = sem "respirar" a cada lombada). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (ClampMin = "0.1"))
	float DriveFOVBlendSpeed = 1.8f;

	/** Vibração leve contínua do terreno na velocidade máxima de referência (graus). Baixa para não enjoar. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (Units = "Degrees", ClampMin = "0", ClampMax = "1"))
	float DriveRumbleDegrees = 0.18f;

	/** Desaceleração/solavanco (km/h por segundo) a partir do qual a câmera treme (batida, atropelo, aterrissagem). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (ClampMin = "10"))
	float DriveJoltMinKmhPerSec = 160.f;

	/** Tremor máximo (graus) com trauma 1 na câmera do carro. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (Units = "Degrees", ClampMin = "0"))
	float DriveShakeMaxAngle = 2.2f;

	/** Trauma por atropelamento a 60 km/h (escala com a velocidade do impacto). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|DriveFeel", meta = (ClampMin = "0", ClampMax = "1"))
	float DriveRunOverShake = 0.3f;

	/** Rotação de repouso do volante (inclinação da coluna). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Visual")
	FRotator SteeringWheelBaseRotation = FRotator(-20.25f, 0.f, 0.f);

	/** Quanto o volante gira com o input todo para um lado. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Visual", meta = (Units = "Degrees"))
	float SteeringWheelMaxDegrees = 120.f;

	/** Velocidade com que volante e motorista acompanham o input. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Visual")
	float SteerVisualSpeed = 8.f;

	/** Material físico da carroceria (atrito baixo, combina por mínimo): raspa nas paredes sem "grudar". */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls")
	TObjectPtr<UPhysicalMaterial> ChassisPhysMaterial;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls")
	bool bWallScrapeEnabled = true;

	/** Acima deste ângulo (carro x parede) a batida é "de frente": física normal, o carro para. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls", meta = (Units = "Degrees"))
	float WallScrapeMaxAngle = 35.f;

	/** Fração da velocidade mantida numa batida de raspão a 10 graus. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls", meta = (ClampMin = "0", ClampMax = "1"))
	float WallScrapeKeepShallow = 0.97f;

	/** Fração da velocidade mantida numa batida a WallScrapeMaxAngle. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls", meta = (ClampMin = "0", ClampMax = "1"))
	float WallScrapeKeepSteep = 0.85f;

	/** Perda de velocidade por segundo enquanto continua raspando. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls", meta = (ClampMin = "0"))
	float WallScrapeDragPerSecond = 0.15f;

	/** Força de alinhamento do carro com a parede (graus/s por grau de erro). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls", meta = (ClampMin = "0"))
	float WallAlignStrength = 3.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Walls", meta = (Units = "km/h"))
	float WallScrapeMinSpeedKmh = 15.f;

	/** Pontos onde zumbis se agarram (presos ao chassi). Com bAutoPlaceGrabPoints, posicionados no BeginPlay. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Zombies")
	TObjectPtr<USceneComponent> GrabPointHood;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Zombies")
	TObjectPtr<USceneComponent> GrabPointLeft;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Zombies")
	TObjectPtr<USceneComponent> GrabPointRight;

	/** Desligue para posicionar GrabPoint*, SmokeFX e FireFX à mão no BP. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies")
	bool bAutoPlaceGrabPoints = true;

	/** Meia caixa da carroceria (cm, espaço do carro). Recalculada pela malha do chassi no BeginPlay se houver malha. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies")
	FVector BodyHalfExtent = FVector(230.f, 95.f, 80.f);

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies")
	FVector BodyCenter = FVector(0.f, 0.f, 60.f);

	/** Acima desta velocidade os zumbis agarrados caem. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (Units = "km/h"))
	float ShakeOffSpeedKmh = 60.f;

	/** Aceleração lateral (cm/s², velocidade x giro) que derruba os agarrados: curva forte. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (ClampMin = "0"))
	float ShakeOffLateralAccel = 1000.f;

	/** Batida em algo com impulso acima disto derruba os agarrados (kg·cm/s; ~250000 = batida leve). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (ClampMin = "0"))
	float ShakeOffImpactImpulse = 250000.f;

	/** Tempo agarrado antes de poder ser sacudido (evita cair no mesmo instante). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (Units = "s"))
	float ShakeOffGraceTime = 0.5f;

	/** Freada forte (desaceleração em cm/s²) derruba os agarrados. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (ClampMin = "0"))
	float ShakeOffBrakeDecel = 1100.f;

	/** Puxão no volante (fração do volante) por zumbi agarrado na lateral. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (ClampMin = "0", ClampMax = "0.5"))
	float GrabberSteerPull = 0.08f;

	/** Desaceleração (cm/s²) por zumbi agarrado. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (ClampMin = "0"))
	float GrabberDeceleration = 120.f;

	/** Máximo de velocidade (fração) que atropelamentos seguidos podem tirar de uma vez. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (ClampMin = "0", ClampMax = "1"))
	float ZombieDragMaxBurst = 0.3f;

	/** Quanto do teto de freio por atropelamento volta por segundo. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (ClampMin = "0"))
	float ZombieDragRecoveryPerSecond = 0.25f;

	/** Abaixo desta velocidade atropelar não freia mais (a horda nunca para o carro). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Zombies", meta = (Units = "km/h"))
	float ZombieDragMinSpeedKmh = 30.f;

	/** Fumaça e fogo do motor (presos ao chassi, na frente). Ligados por HandleIntegrityChanged. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Damage FX")
	TObjectPtr<UNiagaraComponent> SmokeFX;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Damage FX")
	TObjectPtr<UNiagaraComponent> FireFX;

	/** Luz laranja do fogo (funciona mesmo sem asset de partícula) e clarão da explosão. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Damage FX")
	TObjectPtr<UPointLightComponent> FireLight;

	/** Partículas (Niagara). Vazias = só a luz; tools/unreal/setup_car_zombies.py procura assets. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX")
	TObjectPtr<UNiagaraSystem> SmokeSystem;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX")
	TObjectPtr<UNiagaraSystem> FireSystem;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX")
	TObjectPtr<UNiagaraSystem> ExplosionSystem;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX")
	TObjectPtr<USoundBase> ExplosionSound;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX", meta = (ClampMin = "0", ClampMax = "1"))
	float SmokeBelowIntegrity = 0.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX", meta = (ClampMin = "0", ClampMax = "1"))
	float FireBelowIntegrity = 0.25f;

	/** Explosão: raio, dano (barris, objetos) e velocidade de arremesso dos zumbis no centro. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX", meta = (Units = "cm"))
	float ExplosionRadius = 900.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX")
	float ExplosionDamage = 400.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX", meta = (Units = "cm/s"))
	float ExplosionLaunchSpeed = 2200.f;

	/** "Bomba": sair do carro pegando fogo arma a explosão em CarBombFuseTime segundos (mata zumbis em volta). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX")
	bool bCarBombOnExitWhileBurning = true;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX", meta = (Units = "s"))
	float CarBombFuseTime = 5.f;

	/** Pegando fogo, o motor queima sozinho (dano por segundo) até explodir. 0 = fogo não piora. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX", meta = (ClampMin = "0"))
	float BurnEngineDamagePerSecond = 1.5f;

	/** No estágio Driving a explosão é falha (volta ao checkpoint). Ligue para sair a pé também nele. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage FX")
	bool bEjectOnExplodeWhileDriving = false;

	/** Usada se o herói não tiver DrivingAnim própria (precisa ser do mesmo esqueleto do herói). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Driver")
	TObjectPtr<UAnimSequenceBase> FallbackDrivingAnim;

	/** Quanto da velocidade lateral é removida por segundo com as rodas no chão (0 = desligado). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Handling", meta = (ClampMin = "0"))
	float LateralGripAssist = 2.5f;

	/** Fração do LateralGripAssist com o freio de mão puxado (deixa derrapar de propósito). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Handling", meta = (ClampMin = "0", ClampMax = "1"))
	float HandbrakeGripScale = 0.2f;

	/** Até esta velocidade o volante gira tudo; acima dela vai reduzindo. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Handling", meta = (Units = "km/h"))
	float SteerFullUntilKmh = 50.f;

	/** Velocidade em que o volante chega ao mínimo (SteerAtHighSpeed). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Handling", meta = (Units = "km/h"))
	float SteerMinAtKmh = 130.f;

	/** Fração do volante em alta velocidade (evita rodar com toque no teclado). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Handling", meta = (ClampMin = "0.1", ClampMax = "1"))
	float SteerAtHighSpeed = 0.65f;

	/** Amortecimento angular do chassi (menos capotagem e pião). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Handling", meta = (ClampMin = "0"))
	float ChassisAngularDamping = 1.f;

	/** Distância do traço para considerar o carro "no chão" (a partir da origem do carro). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Handling", meta = (Units = "cm"))
	float GroundCheckDistance = 140.f;

	/**
	 * Freio arcade (cm/s² com o pedal todo): soma ao freio das rodas do Chaos. Garante que S / seta para baixo /
	 * gatilho esquerdo param o carro mesmo se o torque de freio das rodas estiver fraco. 0 = desligado.
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Brakes", meta = (ClampMin = "0"))
	float BrakeAssistDecel = 450.f;

	/** O freio arcade cresce de 0 (em BrakeAssistMinKmh) até o valor cheio nesta velocidade: não empurra de ré parado. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Brakes", meta = (Units = "km/h"))
	float BrakeAssistFullAtKmh = 15.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Brakes", meta = (Units = "km/h"))
	float BrakeAssistMinKmh = 2.f;

	/** Ajuda para não capotar: torque que puxa o teto para cima quando a inclinação passa do limite. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Stability")
	bool bRollStabilization = true;

	/** Inclinação (rolagem/arfagem) a partir da qual a ajuda age com as rodas no chão. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Stability", meta = (Units = "Degrees"))
	float RollAssistStartDegrees = 35.f;

	/** No ar a ajuda começa antes: o carro cai de rodas para baixo depois dos saltos. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Stability", meta = (Units = "Degrees"))
	float RollAssistAirStartDegrees = 20.f;

	/** Aceleração angular máxima da ajuda (rad/s², independe da massa). Cheia a 90 graus de inclinação. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Stability", meta = (ClampMin = "0"))
	float RollAssistAccel = 8.f;

	/** Amortecimento (1/s) do giro que tomba o carro enquanto a ajuda age (evita passar do ponto). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Stability", meta = (ClampMin = "0"))
	float RollAssistDamping = 2.5f;

	/** Fração da ajuda no ar. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Stability", meta = (ClampMin = "0", ClampMax = "1"))
	float RollAssistAirScale = 0.5f;

	/** Desvira sozinho se ficar capotado/de lado e quase parado por AutoRecoverDelay segundos. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover")
	bool bAutoRecover = true;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover", meta = (Units = "s"))
	float AutoRecoverDelay = 2.5f;

	/** "Quase parado" para o desvirar automático. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover", meta = (Units = "km/h"))
	float AutoRecoverMaxKmh = 10.f;

	/** Capotado/de lado = componente Z do "teto" do carro abaixo disto (0,5 = mais de 60 graus inclinado). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover", meta = (ClampMin = "-1", ClampMax = "1"))
	float FlippedUpThreshold = 0.5f;

	/** Altura acima do chão onde o carro reaparece de pé. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover", meta = (Units = "cm"))
	float RecoverHeight = 150.f;

	/** Duração do movimento suave até a pose de pé. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover", meta = (Units = "s"))
	float RecoverDuration = 0.6f;

	/** A tecla R só desvira abaixo desta velocidade. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover", meta = (Units = "km/h"))
	float ManualRecoverMaxKmh = 25.f;

	/** Intervalo mínimo entre dois desvirar. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Recover", meta = (Units = "s"))
	float RecoverCooldown = 1.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ThrottleAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> BrakeAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> SteerAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> HandbrakeAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> NitroAction;

	/** Desvirar o carro (R / Y no controle). Vazio = tecla R direto pelo C++. */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ResetAction;

	/** Aceleração extra do nitro (cm/s²) e consumo por segundo. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Nitro")
	float NitroAcceleration = 500.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Nitro")
	float NitroDrainPerSecond = 0.22f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Nitro", meta = (Units = "km/h"))
	float NitroMaxSpeedKmh = 160.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Nitro")
	float StartingNitro = 0.5f;

	// ---- [A-075] Combustível
	/** Tanque no começo da fase: já na reserva (roteiro: zona 1 "vá ao posto"). */
	UPROPERTY(EditAnywhere, Category = "Vehicle|Fuel", meta = (ClampMin = "0", ClampMax = "1"))
	float StartingFuel = 0.24f;

	/** Abaixo disto o HUD mostra RESERVA (pisca) e toca o alerta uma vez. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Fuel", meta = (ClampMin = "0", ClampMax = "1"))
	float FuelReserveLevel = 0.25f;

	/** Piso do tanque sem item pendente: aqui o motor engasga (anti trava: nunca deixa o jogador a pé longe do posto). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Fuel", meta = (ClampMin = "0", ClampMax = "0.2"))
	float FuelLimpLevel = 0.03f;

	/** Força do acelerador com o motor engasgando (média; pulsa em FuelSputterHz). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Fuel", meta = (ClampMin = "0", ClampMax = "1"))
	float FuelLimpThrottle = 0.45f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Fuel", meta = (ClampMin = "0.1"))
	float FuelSputterHz = 2.2f;

	/** Quilômetros que um tanque cheio rende andando devagar (sem acelerador no fundo nem nitro). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Fuel", meta = (ClampMin = "0.1"))
	float FuelRangeKm = 6.f;

	/** Gasto extra com o acelerador no fundo (0,6 = +60%). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Fuel", meta = (ClampMin = "0"))
	float FuelThrottleExtra = 0.6f;

	/** Gasto extra com o nitro ligado (1 = dobra). */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Fuel", meta = (ClampMin = "0"))
	float FuelNitroExtra = 1.f;

	// ---- [A-075] Passageiro: sentada na caixa de munição ao lado do banco central (cm no espaço da malha do buggy)
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Passenger")
	TObjectPtr<USceneComponent> PassengerPivot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Passenger")
	TObjectPtr<USkeletalMeshComponent> PassengerMesh;

	/** Quadril acima dos pés na pose sentada (cm de mundo). Mesmo valor do motorista; ajuste se ela flutuar ou afundar. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Passenger", meta = (Units = "cm"))
	float PassengerHipsHeight = 73.8f;

	/** Ossos escondidos na passageira (pernas atravessariam a caixa). Nomes do esqueleto Mixamo. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Passenger")
	TArray<FName> PassengerHiddenBones = { TEXT("mixamorig:LeftLeg"), TEXT("mixamorig:RightLeg") };

	/** Sem animação sentada: esconde as coxas inteiras (pernas somem) para a pose em pé não sair pelo chão. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Passenger")
	TArray<FName> PassengerHiddenBonesStanding = { TEXT("mixamorig:LeftUpLeg"), TEXT("mixamorig:RightUpLeg") };

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> MouseLookAction;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle", meta = (Units = "s"))
	float SleepDelayAfterPark = 2.f;

	/** Velocidade abaixo da qual o jogador pode descer na zona de transição. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle")
	float ExitMaxSpeedKmh = 4.f;

	/** Tempo máximo freando antes de forçar a parada e descer. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle", meta = (Units = "s"))
	float ExitStopTimeout = 3.f;

	/** Item-chave para entrar a pé (None = destrancado). O baú da barraca dá "CarKey". */
	UPROPERTY(EditAnywhere, Category = "Vehicle|Enter")
	FName RequiredKeyItem = TEXT("CarKey");

private:
	void TickStopForExit();

	/** [A-075] Gasta combustível pela distância (e acelerador/nitro) e faz o motor engasgar no fim do tanque. */
	void TickFuel(float DeltaSeconds);

	/** [A-075] Acelerador que vai para o Chaos depois do combustível (motor morto = 0, engasgando = pulsa). */
	float EffectiveThrottle() const;

	float FuelLevel = 1.f;
	bool bEngineDead = false;
	bool bHasPassenger = false;
	float FuelSputterPhase = 0.f;

	/** Esconde/mostra a cabeça do motorista (só age quando muda). */
	void SetDriverHeadHidden(bool bHide);

	bool bFirstPersonWanted = false;
	bool bDriverShown = false;
	bool bDriverHeadHidden = false;
	bool bFPStableValid = false;
	bool bFPLookInit = false;
	float FPBlendAlpha = 0.f;
	float FPLookYaw = 0.f;
	float FPLookPitch = 0.f;
	float FPLookIdleTime = 0.f;
	FRotator FPLastControlRotation = FRotator::ZeroRotator;
	FVector FPStableLocal = FVector::ZeroVector;

	// [A-073] sensação de dirigir (estado da câmera)
	void UpdateDriveFeel(float RealDt);
	void ApplyDriveFeel(FMinimalViewInfo& OutResult, float FirstPersonAlpha) const;
	UFUNCTION()
	void HandleZombieCarFeel(EJRZombieCarEvent Event, AActor* Zombie, FVector Location, float Value);
	FVector DriveFeelLastVel = FVector::ZeroVector;
	float DriveTrauma = 0.f;
	float DriveShakeTime = 0.f;
	float DriveFOVNow = 0.f;
	float DriveRumbleNow = 0.f;
	bool bDriveFeelVelValid = false;
	bool bDriveFeelBound = false;

	bool bDriveEnabled = true;
	FTimerHandle SleepTimer;
	FTimerHandle StopExitTimer;
	FTimerHandle NitroTimer;
	float NitroCharge = 0.f;
	bool bNitroActive = false;
	bool bNitroHeld = false;
	bool bHandbrakeHeld = false;
	float ThrottleInputValue = 0.f;
	float BrakeInputValue = 0.f;
	float FlippedTime = 0.f;
	bool bRecovering = false;
	float RecoverElapsed = 0.f;
	double LastRecoverTime = -100.0;
	double LastRecoverDeniedTime = -100.0;
	FTransform RecoverStart;
	FTransform RecoverTarget;
	float LastSteerInput = 0.f;
	float VisualSteer = 0.f;
	double LastScrapeTime = -1.0;
	FTransform PendingExitFallback;
	float StopExitElapsed = 0.f;
	FName PendingRequiredItem;
	FString PendingRequiredItemLabel;

	static constexpr int32 NumGrabSlots = 3;
	TWeakObjectPtr<AJREnemyCharacter> Grabbers[NumGrabSlots];
	double GrabStartTime[NumGrabSlots] = { 0.0, 0.0, 0.0 };
	float ZombieDragUsed = 0.f;
	double LastZombieDragTime = 0.0;
	bool bExploded = false;
	bool bSmokeOn = false;
	bool bFireOn = false;
	bool bLoggedMissingFX = false;
	FTimerHandle ExplosionFlashTimer;
	FTimerHandle CarBombTimer;
	FTimerHandle BurnTimer;
	EJRVehicleDamageFXState DamageFXState = EJRVehicleDamageFXState::Intact;
	float PrevForwardSpeed = 0.f;
	float FilteredBrakeDecel = 0.f;
	bool bGrabSteerApplied = false;
};

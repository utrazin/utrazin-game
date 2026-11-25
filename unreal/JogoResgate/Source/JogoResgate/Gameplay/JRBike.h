// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRBike.generated.h"

class AJRCharacter;
class UAnimMontage;
class UAnimSequenceBase;
class UCameraComponent;
class USkeletalMesh;
class UStaticMesh;
class UStaticMeshComponent;

/** [A-098] Pedalada de um herói: a animação foi feita no esqueleto dele (tools/blender/gen_bike_rider.py). */
USTRUCT(BlueprintType)
struct FJRBikeRiderAnim
{
	GENERATED_BODY()

	/** Malha do herói que usa esta pedalada (compara a malha; se não bater, compara o esqueleto). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bike")
	TSoftObjectPtr<USkeletalMesh> Mesh;

	/** 1 volta do pedivela (quadro 0 = pedal direito na frente, fase 0). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bike")
	TSoftObjectPtr<UAnimSequenceBase> PedalAnim;
};

/**
 * [A-097/A-098] Bicicleta para andar pela cidade. E perto dela monta; E de novo desce.
 * Não é um veículo de física (duas rodas no Chaos tombam): o herói continua sendo o pawn e a bicicleta vai presa na
 * cápsula dele. A098: a bicicleta manda na velocidade do CharacterMovement (aceleração zerada, atrito zerado) com um
 * modelo arcade de bicicleta:
 *  - pedalada: o empurrão vem em pulsos (2 por volta, mais forte com o pedivela na horizontal) e cai perto da
 *    velocidade máxima; soltar = roda livre (desliza, perde pouco), puxar para trás = freio (derrapa de leve acima de
 *    SkidMinSpeed: roda de trás trava, pega menos de lado);
 *  - direção: guidão esterça pelo ângulo entre a câmera/entrada e a bicicleta, menos quanto mais rápido; a curva sai
 *    do modelo cinemático (taxa de giro = v / entre-eixos x tan(esterço)); velocidade de lado amortecida forte (vai para
 *    onde a roda aponta); parada dá para girar no lugar devagar (empurrando a bicicleta);
 *  - inclinação na curva pela física: lean = atan(v x taxa de giro / g) com mola (atraso e leve sobra);
 *  - suspensão visual: trace em cada roda, arfagem (pitch) pela altura das duas rodas, mola amortecida no quique e
 *    na arfagem, pancada ao cair de degrau, sobe/desce suave em meio-fio (compensa o degrau do CharacterMovement),
 *    tremidinha em terra/grama (material físico ou nome do material);
 *  - ladeira: subida freia, descida empurra (gravidade x seno da rampa do chão);
 *  - pedalada animada: a fase do pedivela anda com a velocidade (cadência = v / DistancePerCrankTurn, entre mínimo e
 *    máximo) e a montagem da pedalada fica parada (rate 0) com a posição = fase, então pernas, pedivela e pedais
 *    andam juntos e sem deriva. Sem pedalar, o pedivela vai para a horizontal e para;
 *  - câmera: FOV e afastamento leves com a velocidade, tremor em terra.
 * O herói e a bicicleta inclinam/arfam juntos em volta do ponto de chão da bicicleta (as mãos e os pés não soltam).
 * Malhas (origem = a do quadro: chão entre as rodas, frente +X), escala BikeScale no LeanPivot:
 *   SM_VEH_BikeQuadroSemPedivela (reserva SM_VEH_BikeQuadro), SM_VEH_BikeSelim (desce SeatDrop),
 *   SM_VEH_BikeGuidao (gira no eixo da caixa de direção, com a roda da frente), SM_VEH_BikePedivela (origem no eixo
 *   central), SM_VEH_BikePedal (x2), SM_VEH_BikeRoda (x2). Colocada por tools/unreal/build_interiors_vila.py.
 */
UCLASS()
class JOGORESGATE_API AJRBike : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRBike();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void Tick(float DeltaSeconds) override;

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	UFUNCTION(BlueprintCallable, Category = "Bike")
	bool Mount(AJRCharacter* Hero);

	UFUNCTION(BlueprintCallable, Category = "Bike")
	void Dismount();

	UFUNCTION(BlueprintPure, Category = "Bike")
	bool IsMounted() const { return Rider.IsValid(); }

	/** Velocidade para a frente (cm/s). */
	UFUNCTION(BlueprintPure, Category = "Bike")
	float GetRideSpeed() const { return Speed; }

	/** Fase do pedivela (graus, 0 = pedal direito na frente). */
	UFUNCTION(BlueprintPure, Category = "Bike")
	float GetCrankPhase() const { return Phase; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	void ApplyMeshes();
	void SetParkedCollision(bool bParked);
	void PlaceParked(const FVector& Near, float Yaw, const AActor* Ignore);
	void RestoreRider(AJRCharacter* Hero);
	UAnimSequenceBase* FindPedalAnim(const AJRCharacter* Hero) const;
	void UpdateCrank();
	void UpdateRiderPose(AJRCharacter* Hero);
	void UpdateSuspension(AJRCharacter* Hero, float Dt);
	void UpdateCamera(float Dt);
	float TraceWheelGround(const FVector& WheelGround, float& OutRoughness) const;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> Root;

	/** Inclinação, arfagem e quique (e a escala da bicicleta). */
	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> LeanPivot;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> Frame;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> Seat;

	/** Eixo da caixa de direção (Z local = eixo inclinado). */
	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> SteerAxis;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> SteerYaw;

	/** Desfaz o SteerAxis: o que fica embaixo usa as mesmas coordenadas do quadro. */
	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> SteerOffset;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> Handlebar;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> CrankPivot;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> Crank;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> PedalRight;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> PedalLeft;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> FrontPivot;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> FrontWheel;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<USceneComponent> RearPivot;

	UPROPERTY(VisibleAnywhere, Category = "Bike")
	TObjectPtr<UStaticMeshComponent> RearWheel;

	// ------------------------------------------------------------------ malhas
	UPROPERTY(EditAnywhere, Category = "Bike|Meshes")
	TSoftObjectPtr<UStaticMesh> FrameMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Veiculos/SM_VEH_BikeQuadroSemPedivela.SM_VEH_BikeQuadroSemPedivela")));

	/** Reserva se FrameMesh não existir (quadro inteiro, com pedivela, selim e guidão fixos). */
	UPROPERTY(EditAnywhere, Category = "Bike|Meshes")
	TSoftObjectPtr<UStaticMesh> LegacyFrameMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Veiculos/SM_VEH_BikeQuadro.SM_VEH_BikeQuadro")));

	UPROPERTY(EditAnywhere, Category = "Bike|Meshes")
	TSoftObjectPtr<UStaticMesh> SeatMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Veiculos/SM_VEH_BikeSelim.SM_VEH_BikeSelim")));

	UPROPERTY(EditAnywhere, Category = "Bike|Meshes")
	TSoftObjectPtr<UStaticMesh> HandlebarMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Veiculos/SM_VEH_BikeGuidao.SM_VEH_BikeGuidao")));

	UPROPERTY(EditAnywhere, Category = "Bike|Meshes")
	TSoftObjectPtr<UStaticMesh> CrankMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Veiculos/SM_VEH_BikePedivela.SM_VEH_BikePedivela")));

	UPROPERTY(EditAnywhere, Category = "Bike|Meshes")
	TSoftObjectPtr<UStaticMesh> PedalMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Veiculos/SM_VEH_BikePedal.SM_VEH_BikePedal")));

	UPROPERTY(EditAnywhere, Category = "Bike|Meshes")
	TSoftObjectPtr<UStaticMesh> WheelMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Veiculos/SM_VEH_BikeRoda.SM_VEH_BikeRoda")));

	// ------------------------------------------------------------------ geometria (cm, bicicleta SEM escala)
	/** Tamanho da bicicleta. As pedaladas foram feitas para 0,89 (bike_rider_info.json): mudou aqui, gere de novo
	 *  com "gerar_bike_anim.bat <escala>", senão pés e mãos saem do lugar. */
	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (ClampMin = "0.5", ClampMax = "2.0"))
	float BikeScale = 0.89f;

	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "cm"))
	float WheelRadius = 34.f;

	/** Altura da origem do quadro (o ponto mais baixo do quadro original, o pedal, fica a 15,8 cm do chão). */
	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "cm"))
	float FrameGroundOffset = 15.8f;

	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "cm"))
	float FrontWheelX = 56.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "cm"))
	float RearWheelX = -56.f;

	/** Eixo do movimento central (pivô do pedivela). */
	UPROPERTY(EditAnywhere, Category = "Bike|Geometry")
	FVector CrankPivotLocation = FVector(-0.4f, 0.f, 30.43f);

	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "cm"))
	float CrankLength = 15.92f;

	/** Distância do meio da bicicleta ao eixo de cada pedal. */
	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "cm"))
	float PedalSpindleY = 9.34f;

	/** Selim mais baixo que no modelo (os heróis têm perna curta para o quadro). */
	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "cm"))
	float SeatDrop = 4.f;

	/** Ponto de baixo da caixa de direção e inclinação do eixo (para trás). */
	UPROPERTY(EditAnywhere, Category = "Bike|Geometry")
	FVector SteerPivotLocation = FVector(46.6f, 0.f, 68.43f);

	UPROPERTY(EditAnywhere, Category = "Bike|Geometry", meta = (Units = "Degrees"))
	float SteerTiltDegrees = 14.53f;

	// ------------------------------------------------------------------ pedalar
	/** Velocidade máxima pedalando (a pé o herói anda a ~350 e corre a ~600). */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride", meta = (Units = "cm/s"))
	float RideSpeed = 1100.f;

	/** Segurando correr: pedala forte. */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride", meta = (Units = "cm/s"))
	float SprintRideSpeed = 1600.f;

	/** Empurrão médio de uma pedalada (cm/s²) parado; cai até zero na velocidade máxima. */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride")
	float PedalAcceleration = 620.f;

	/** Segurando correr. */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride")
	float SprintPedalAcceleration = 820.f;

	/** Quanto o empurrão pulsa com o pedivela (0 = contínuo, 1 = só nas pedaladas). */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride", meta = (ClampMin = "0", ClampMax = "1"))
	float PedalPulse = 0.6f;

	/** Roda livre: perda fixa (rolamento) e pelo ar (x v²). */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride")
	float RollingDecel = 45.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Ride")
	float AirDrag = 0.000025f;

	/** Freio (puxar para trás). */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride")
	float BrakeDecel = 950.f;

	/** Acima disso, frear forte derrapa a roda de trás. */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride", meta = (Units = "cm/s"))
	float SkidMinSpeed = 500.f;

	/** Ladeira: fração da gravidade que vale (1 = física; menos = mais arcade). */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride", meta = (ClampMin = "0", ClampMax = "1.5"))
	float SlopeGravityScale = 0.7f;

	/** Quanto anda por volta do pedivela (marcha). 1100 cm/s = ~2 voltas/s. */
	UPROPERTY(EditAnywhere, Category = "Bike|Ride", meta = (Units = "cm"))
	float DistancePerCrankTurn = 560.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Ride")
	float MinCadence = 0.9f;

	UPROPERTY(EditAnywhere, Category = "Bike|Ride")
	float MaxCadence = 2.6f;

	// ------------------------------------------------------------------ direção
	/** Esterço máximo parado/devagar e na velocidade de corrida. */
	UPROPERTY(EditAnywhere, Category = "Bike|Steer", meta = (Units = "Degrees"))
	float MaxSteerLowSpeed = 30.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Steer", meta = (Units = "Degrees"))
	float MaxSteerHighSpeed = 6.f;

	/** Esterço por grau de diferença entre a entrada e a bicicleta. */
	UPROPERTY(EditAnywhere, Category = "Bike|Steer")
	float SteerResponse = 0.5f;

	UPROPERTY(EditAnywhere, Category = "Bike|Steer")
	float SteerSpeed = 6.f;

	/** Limite de giro (graus/s) para não ficar nervosa. */
	UPROPERTY(EditAnywhere, Category = "Bike|Steer", meta = (Units = "Degrees"))
	float TurnRateDegrees = 140.f;

	/** Parada (empurrando a bicicleta): giro no lugar. */
	UPROPERTY(EditAnywhere, Category = "Bike|Steer", meta = (Units = "Degrees"))
	float StandingTurnRate = 70.f;

	/** Aderência de lado (quanto maior, menos escorrega); derrapando usa SkidGrip. */
	UPROPERTY(EditAnywhere, Category = "Bike|Steer")
	float LateralGrip = 16.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Steer")
	float SkidGrip = 3.5f;

	/** O guidão visual vira no máximo isto (as mãos ficam na pose reta, então pouco). */
	UPROPERTY(EditAnywhere, Category = "Bike|Steer", meta = (Units = "Degrees"))
	float MaxVisualSteer = 18.f;

	// ------------------------------------------------------------------ inclinação e suspensão
	/** 1 = inclinação física atan(v²/(g R)); menos fica mais contido. */
	UPROPERTY(EditAnywhere, Category = "Bike|Lean", meta = (ClampMin = "0", ClampMax = "1.5"))
	float LeanScale = 0.65f;

	UPROPERTY(EditAnywhere, Category = "Bike|Lean", meta = (Units = "Degrees"))
	float MaxLeanDegrees = 26.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Lean")
	float LeanStiffness = 55.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Lean", meta = (ClampMin = "0", ClampMax = "2"))
	float LeanDamping = 0.75f;

	UPROPERTY(EditAnywhere, Category = "Bike|Suspension")
	float SuspensionStiffness = 220.f;

	/** Fração do amortecimento crítico (menos de 1 = quica um pouco). */
	UPROPERTY(EditAnywhere, Category = "Bike|Suspension", meta = (ClampMin = "0", ClampMax = "2"))
	float SuspensionDamping = 0.45f;

	UPROPERTY(EditAnywhere, Category = "Bike|Suspension", meta = (Units = "cm"))
	float SuspensionTravel = 22.f;

	/** Quique ao cair: fração da velocidade de queda que vira compressão. */
	UPROPERTY(EditAnywhere, Category = "Bike|Suspension")
	float LandingBounce = 0.3f;

	/** Tremidinha (cm) em terra/grama/areia e em Landscape sem material físico. */
	UPROPERTY(EditAnywhere, Category = "Bike|Suspension", meta = (Units = "cm"))
	float RoughBump = 1.6f;

	UPROPERTY(EditAnywhere, Category = "Bike|Suspension", meta = (ClampMin = "0", ClampMax = "1"))
	float LandscapeRoughness = 0.35f;

	/** Nomes (material físico ou material) que contam como chão de terra. */
	UPROPERTY(EditAnywhere, Category = "Bike|Suspension")
	TArray<FString> RoughSurfaceKeywords = {TEXT("Terra"), TEXT("Dirt"), TEXT("Grama"), TEXT("Grass"), TEXT("Areia"), TEXT("Sand"), TEXT("Lama"), TEXT("Mud"), TEXT("Cascalho"), TEXT("Gravel")};

	// ------------------------------------------------------------------ câmera
	UPROPERTY(EditAnywhere, Category = "Bike|Camera", meta = (Units = "Degrees"))
	float SpeedFOVBonus = 7.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Camera", meta = (Units = "cm"))
	float SpeedCameraPullBack = 45.f;

	UPROPERTY(EditAnywhere, Category = "Bike|Camera", meta = (Units = "cm"))
	float RoughCameraShake = 0.9f;

	// ------------------------------------------------------------------ estacionada / pose
	UPROPERTY(EditAnywhere, Category = "Bike", meta = (Units = "Degrees"))
	float ParkedLeanDegrees = 8.f;

	/** Pedaladas por herói (a primeira cuja malha/esqueleto bate com o herói). */
	UPROPERTY(EditAnywhere, Category = "Bike|Rider")
	TArray<FJRBikeRiderAnim> RiderAnims;

	/** Ajuste fino da malha do herói montado (a pedalada já põe o quadril no selim: normalmente zero). */
	UPROPERTY(EditAnywhere, Category = "Bike|Rider")
	FVector RiderMeshOffset = FVector::ZeroVector;

	/** Pose montada forçada; vazio = RiderAnims (e, sem pedalada, a DrivingAnim do herói). */
	UPROPERTY(EditAnywhere, Category = "Bike|Rider")
	TObjectPtr<UAnimSequenceBase> RideAnimOverride;

	/** Só para a reserva DrivingAnim (pose de banco de carro, mais baixa que o selim). */
	UPROPERTY(EditAnywhere, Category = "Bike|Rider")
	FVector DrivingAnimMeshOffset = FVector(-8.f, 0.f, 32.f);

private:
	TWeakObjectPtr<AJRCharacter> Rider;
	/** Controle do herói: a bicicleta roda depois dele (a entrada do quadro já chegou) e antes do CharacterMovement. */
	TWeakObjectPtr<AActor> InputTickSource;
	TWeakObjectPtr<UCameraComponent> RiderCamera;
	TWeakObjectPtr<UAnimMontage> PedalMontage;
	float PedalAnimLength = 0.f;
	bool bPedalAnimSynced = false;
	bool bHasCrank = false;
	bool bHasSteer = false;
	FVector ActiveMeshOffset = FVector::ZeroVector;

	float SavedMaxWalkSpeed = 0.f;
	float SavedMaxAcceleration = 0.f;
	float SavedBraking = 0.f;
	float SavedGroundFriction = 0.f;
	float SavedBrakingFrictionFactor = 2.f;
	FRotator SavedRotationRate = FRotator::ZeroRotator;
	bool bSavedOrientToMovement = true;
	bool bSavedUseControllerDesiredRotation = false;
	bool bSavedUseControllerYaw = false;
	FVector SavedMeshLocation = FVector::ZeroVector;
	FRotator SavedMeshRotation = FRotator::ZeroRotator;
	float SavedFOV = 90.f;
	FVector SavedCameraLocation = FVector::ZeroVector;
	FRotator SavedCameraRotation = FRotator::ZeroRotator;

	float Speed = 0.f;
	float Heading = 0.f;
	float Steer = 0.f;
	float LateralVel = 0.f;
	float Phase = 0.f;
	bool bPedaling = false;
	bool bSkidding = false;
	float FrontWheelAngle = 0.f;
	float RearWheelAngle = 0.f;
	float Lean = 0.f;
	float LeanVel = 0.f;
	float Heave = 0.f;
	float HeaveVel = 0.f;
	float Pitch = 0.f;
	float PitchVel = 0.f;
	float Roughness = 0.f;
	float Distance = 0.f;
	float LastActorZ = 0.f;
	float LastFallSpeed = 0.f;
	bool bWasFalling = false;
	float CamSpeedAlpha = 0.f;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "AI/JREnemyStateLogic.h"
#include "Gameplay/JRPickup.h"
#include "GameFramework/Character.h"
#include "JREnemyCharacter.generated.h"

class UJREnemyArchetype;
class AJRVehiclePawn;
class AAIController;
class UJRHealthComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UJRDamageFXComponent;
class UStaticMesh;
class UAnimMontage;
class AController;      // [A-073]
class UDamageType;      // [A-073]
class UPrimitiveComponent; // [A-073]

/** O que o zumbi calmo está fazendo (só C++; o estado público continua Idle/Patrol). */
enum class EJRCalmActivity : uint8
{
	Pause,   // parado (às vezes vira para o lado ou toca uma variação)
	Walk,    // andando arrastado até um ponto aleatório perto de casa
	Follow,  // seguindo um zumbi vizinho (manada)
	Feed,    // "comendo" perto de um corpo/destroço
	Bang     // batendo numa parede/destroço
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnEnemyDied, AJREnemyCharacter*, Enemy);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnEnemyStateChanged, EJREnemyState, OldState, EJREnemyState, NewState);

/**
 * Inimigo genérico parametrizado por UJREnemyArchetype (ADR-002).
 * Decisão de estado: FJREnemyStateLogic. Execução: este ator, por timer (não Tick), com
 * frequência definida pelo UJREnemyBudgetSubsystem. Um StateTree no AIController pode assumir
 * a decisão (bUseBuiltInBrain = false) chamando as funções BlueprintCallable abaixo.
 */
UCLASS()
class JOGORESGATE_API AJREnemyCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AJREnemyCharacter();

	UFUNCTION(BlueprintCallable, Category = "Enemy")
	void SetFullUpdate(bool bFull);

	UFUNCTION(BlueprintPure, Category = "Enemy")
	bool IsFullUpdate() const { return bFullUpdate; }

	UFUNCTION(BlueprintPure, Category = "Enemy")
	EJREnemyState GetEnemyState() const { return CurrentState; }

	UFUNCTION(BlueprintPure, Category = "Enemy")
	bool IsDead() const { return CurrentState == EJREnemyState::Dead; }

	UFUNCTION(BlueprintPure, Category = "Enemy")
	UJREnemyArchetype* GetArchetype() const { return Archetype; }

	/** Uma iteração de percepção + decisão + ação. Chamado pelo timer ou por task de StateTree. */
	UFUNCTION(BlueprintCallable, Category = "Enemy")
	void UpdateBrain();

	/** Executa o ataque do arquétipo contra o alvo atual, respeitando o intervalo. */
	UFUNCTION(BlueprintCallable, Category = "Enemy")
	bool TryAttack();

	/** Atropelado: arremessa (ragdoll) ou derruba, e danifica o carro. */
	void HitByVehicle(AActor* Vehicle);

	/** Faz o zumbi caçar o jogador mesmo longe/sem visão (zumbis que "chegam" pelo mapa). */
	UFUNCTION(BlueprintCallable, Category = "Enemy")
	void SetForceAggro(bool bForce) { bForceAggro = bForce; }

	/** Barricada: fica parado no lugar enquanto o jogador estiver no carro longe (vira obstáculo na estrada). */
	UFUNCTION(BlueprintCallable, Category = "Enemy")
	void SetHoldPosition(bool bHold) { bHoldPosition = bHold; }

	/**
	 * Ouviu um barulho (UJRNoise::ReportNoise). Calmo e dentro do raio (x HearingScale): vai ver o local.
	 * Retorna true se vai investigar.
	 */
	UFUNCTION(BlueprintCallable, Category = "Enemy|Life")
	bool HearNoise(FVector NoiseLocation, float InLoudness);

	/** Liga/desliga o vagar quando calmo (desligado = fica parado no lugar, como antes). */
	UFUNCTION(BlueprintCallable, Category = "Enemy|Life")
	void SetWanderEnabled(bool bEnabled) { bWanderEnabled = bEnabled; }

	/** Novo "ponto de casa" do vagar (padrão: onde nasceu). */
	UFUNCTION(BlueprintCallable, Category = "Enemy|Life")
	void SetHomeLocation(FVector NewHome) { HomeLocation = NewHome; }

	/** Calmo (Idle/Patrol), sem alvo nem barulho. */
	UFUNCTION(BlueprintPure, Category = "Enemy|Life")
	bool IsCalm() const { return CurrentState == EJREnemyState::Idle || CurrentState == EJREnemyState::Patrol; }

	/** Viu o alvo (Alert/Chase/Attack). */
	UFUNCTION(BlueprintPure, Category = "Enemy|Life")
	bool IsEngaged() const
	{
		return CurrentState == EJREnemyState::Alert || CurrentState == EJREnemyState::Chase || CurrentState == EJREnemyState::Attack;
	}

	/** Morre arremessado (ragdoll) com esta velocidade (cm/s). Usado pela explosão do carro e ao cair do carro. */
	void KillWithLaunch(const FVector& LaunchVelocity, AController* InstigatorController, AActor* Causer);

	/** Agarrado no carro (capô ou lateral)? */
	UFUNCTION(BlueprintPure, Category = "Enemy")
	bool IsGrabbingVehicle() const { return GrabbedVehicle.IsValid(); }

	/** Tenta pular/agarrar no carro (ponto livre mais próximo). */
	bool TryGrabVehicle(AJRVehiclePawn* Car);

	/** Solta do carro. bKill = arremessado e morto (sacudida/batida); senão cai ao lado e volta a perseguir. */
	void ReleaseFromVehicle(bool bKill, const FVector& LaunchVelocity);

	/** Teto de ragdolls ativos: congela o corpo e encurta o tempo até sumir. */
	void FreezeRagdoll();

	UPROPERTY(BlueprintAssignable, Category = "Enemy")
	FJROnEnemyDied OnEnemyDied;

	UPROPERTY(BlueprintAssignable, Category = "Enemy")
	FJROnEnemyStateChanged OnEnemyStateChanged;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UFUNCTION()
	void HandleDeath(UJRHealthComponent* Health, AActor* Killer);

	UFUNCTION()
	void HandleHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta);

	void ResolveMeleeHit();

	UFUNCTION()
	void HandleCapsuleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	void DropLoot();

	/** Chance (0..1) de deixar um item ao morrer. */
	UPROPERTY(EditAnywhere, Category = "Enemy|Loot")
	float DropChance = 0.45f;

	/** Zumbi especial (elite): sempre deixa este item (ex.: escopeta alien). */
	UPROPERTY(EditAnywhere, Category = "Enemy|Loot")
	bool bHasGuaranteedDrop = false;

	UPROPERTY(EditAnywhere, Category = "Enemy|Loot")
	EJRPickupType GuaranteedDrop = EJRPickupType::WeaponShotgun;

	UPROPERTY(EditAnywhere, Category = "Enemy|Loot")
	TObjectPtr<UStaticMesh> GuaranteedDropMesh;

	/** Tempo entre começar o golpe e o dano (o jogador pode desviar). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Combat", meta = (Units = "s"))
	float MeleeWindup = 0.45f;

	/** Cada zumbi chega por um ângulo diferente (cerca o jogador) até esta distância. */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Combat", meta = (Units = "cm"))
	float FlankDistance = 450.f;

	/** Persegue o carro do jogador até esta distância da lataria (carro faz barulho: não precisa de visão). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "cm"))
	float VehicleChaseRadius = 4000.f;

	/** Corre para onde o carro VAI estar daqui a até este tempo (intercepta em vez de correr atrás). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "s"))
	float VehicleInterceptMaxTime = 1.5f;

	/** Grupo correndo para o carro se espalha até esta distância para cada lado da estrada (cerca a pista). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "cm"))
	float VehicleRoadSpread = 250.f;

	/** Fração do AttackDamage aplicada à lataria por soco (o carro aguenta mais que o herói). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (ClampMin = "0"))
	float VehicleAttackDamageScale = 0.3f;

	/** Distância da lataria em que o zumbi consegue agarrar o carro. */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "cm"))
	float GrabReach = 120.f;

	/** Chance por decisão (a cada 0,1 a 0,5 s) de agarrar quando está colado no carro devagar. */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (ClampMin = "0", ClampMax = "1"))
	float GrabChance = 0.15f;

	/** Chance de agarrar quando o carro devagar esbarra nele (em vez de só empurrar). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (ClampMin = "0", ClampMax = "1"))
	float GrabWhenBumpedChance = 0.35f;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "s"))
	float GrabCooldown = 3.f;

	/** Intervalo dos golpes enquanto agarrado (toca a montage de ataque em loop). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "s"))
	float GrabAttackInterval = 1.f;

	/** Dano na zona do carro por segundo, por zumbi agarrado (no capô, metade vai também para o motor). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (ClampMin = "0"))
	float GrabDamagePerSecond = 4.f;

	/** Fração da velocidade que o carro perde a cada zumbi arremessado (o carro limita o total). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (ClampMin = "0", ClampMax = "1"))
	float RunOverDragFraction = 0.06f;

	/** Abaixo desta velocidade o carro encostando não empurra nem machuca (zumbi andando até o carro parado). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "km/h"))
	float BumpMinSpeedKmh = 8.f;

	/** Barricada: solta o zumbi quando o carro chega a esta distância (ou se o jogador estiver a pé). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "cm"))
	float HoldReleaseDistance = 500.f;

	/** Cambaleia ao levar tiro (para de andar por este tempo). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Combat", meta = (Units = "s"))
	float StaggerTime = 0.3f;

	/** Velocidade do carro (km/h) NA DIREÇÃO do zumbi a partir da qual ele é arremessado (ragdoll). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle", meta = (Units = "km/h"))
	float RunOverSpeedKmh = 18.f;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Vehicle")
	float RunOverCarDamage = 3.f;

	void SetEnemyState(EJREnemyState NewState);
	/** Persegue o carro: intercepta a posição prevista; perto ou devagar, vai até a lataria. */
	void MoveTowardVehicle(AAIController* AI, AJRVehiclePawn* Car, float BodyDistance, const FVector& ContactPoint);
	/** Golpe periódico enquanto agarrado no carro. */
	void TickGrab();
	void RestartBrainTimer();
	void FireRangedShot();
	FVector GetMuzzleLocation() const;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Enemy")
	TObjectPtr<UJRHealthComponent> HealthComponent;

	/** [Sensação de combate, A-057] sangue azul brilhante, ferimentos no corpo e flash ao levar tiro. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Enemy")
	TObjectPtr<UJRDamageFXComponent> DamageFXComponent;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Enemy")
	TObjectPtr<UJREnemyArchetype> Archetype;

	UPROPERTY(EditAnywhere, Category = "Enemy")
	bool bUseBuiltInBrain = true;

	UPROPERTY(EditAnywhere, Category = "Enemy")
	bool bHasPatrol = false;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Performance", meta = (Units = "s"))
	float FullUpdateInterval = 0.1f;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Performance", meta = (Units = "s"))
	float ReducedUpdateInterval = 0.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy")
	FName MuzzleSocket = TEXT("hand_r");

	/** [Remap F1] Arma na mão do atirador (Burst). */
	UPROPERTY(VisibleAnywhere, Category = "Enemy|Combat")
	TObjectPtr<UStaticMeshComponent> GunMesh;

	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Combat")
	TSoftObjectPtr<UStaticMesh> GunStaticMesh;

	/** Encaixe da arma no osso da mão (MuzzleSocket). Ajustar no BP se ficar torta. */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Combat")
	FTransform GunGripOffset = FTransform(FRotator(0.f, 90.f, 0.f), FVector(0.f, 4.f, 0.f));

	/** Vagar quando calmo (A-048). Barricada (SetHoldPosition) continua parada. */
	UPROPERTY(EditAnywhere, Category = "Enemy|Life")
	bool bWanderEnabled = true;

	/** Longe do jogador além disto o zumbi calmo não decide nada novo (ninguém vê; economiza navmesh). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Life", meta = (Units = "cm"))
	float WanderMaxPlayerDistance = 15000.f;

	/** Raio em que procura parede/destroço/corpo para bater ou "comer". */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Life", meta = (Units = "cm"))
	float CalmSpotSearchRadius = 260.f;

	/** Raio em que procura um zumbi para seguir (manada). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Life", meta = (Units = "cm"))
	float HerdSearchRadius = 1500.f;

	/** Giro (graus/s) ao vagar: devagar, arrastado. Perseguindo usa o giro do BP. */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Life")
	float ShambleTurnRate = 150.f;

	/** Aceleração máxima ao vagar (arranca e para devagar; a animação acompanha a velocidade). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Life")
	float ShambleMaxAcceleration = 450.f;

	/** Ao ver o jogador, o rosnado chama zumbis calmos até esta distância (0 desliga). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Perception", meta = (Units = "cm"))
	float AlertGroanLoudness = 900.f;

	/** Tag (ator ou componente) de algo que o zumbi "come" (além de corpos e malhas com Wreck/Corpse/Body no nome). */
	UPROPERTY(EditDefaultsOnly, Category = "Enemy|Life")
	FName FeedTag = TEXT("JR_ZombieFeed");

	/** Escreve no log cada atividade calma (debug do vagar). */
	UPROPERTY(EditAnywhere, Category = "Enemy|Life")
	bool bLogLife = false;

	/** Visão: alvo dentro do cone do arquétipo (ou bem perto). */
	bool IsInSightCone(const FVector& Point) const;
	/** Ajusta velocidade, giro e aceleração: arrastado (calmo) ou perseguição. */
	void ApplyMovementStyle(bool bShamble, float NewMaxSpeed);
	/** true: gira para o foco do AIController (parado); false: gira para onde anda. */
	void SetFaceFocus(bool bFace);
	void BeginInvestigate(const FVector& Where, double Now);
	void UpdateInvestigate(AAIController* AI, double Now);
	void UpdateCalm(AAIController* AI, APawn* PlayerPawn, double Now);
	void StartCalmPause(AAIController* AI, double Now);
	void ChooseNextCalmActivity(AAIController* AI, double Now);
	bool StartWalk(AAIController* AI, double Now);
	bool StartFollow(AAIController* AI, double Now);
	/** Parede/destroço/corpo encostado (ou quase). bOutFeed = corpo/destroço para "comer". */
	bool FindCalmSpot(bool& bOutFeed, FVector& OutPoint) const;
	/** Toca uma montage se nenhuma estiver tocando. */
	bool PlayLifeMontage(UAnimMontage* Montage, float PlayRate);
	void PlayIdleVariation();
	void LogLife(const TCHAR* What) const;

	/** [A-073] Guarda direção/osso/força do último acerto pontual: na morte o corpo cai PARA LONGE do golpe. */
	UFUNCTION()
	void HandlePointDamageFeel(AActor* DamagedActor, float Damage, AController* InstigatedBy, FVector HitLocation,
		UPrimitiveComponent* FHitComponent, FName BoneName, FVector ShotFromDirection, const UDamageType* DamageType,
		AActor* DamageCauser);

	/** [A-073] Na morte por tiro/golpe: velocidade dada ao corpo inteiro na direção do golpe. 0 = desliga. */
	UPROPERTY(EditAnywhere, Category = "Enemy|Feel", meta = (Units = "cm/s", ClampMin = "0"))
	float DeathPushSpeed = 160.f;

	/** [A-073] Tranco extra só no osso atingido (cabeça vai para trás, perna "sai"). */
	UPROPERTY(EditAnywhere, Category = "Enemy|Feel", meta = (Units = "cm/s", ClampMin = "0"))
	float DeathBoneKick = 420.f;

private:
	TWeakObjectPtr<AActor> Target;
	FTimerHandle BrainTimer;
	FTimerHandle BurstTimer;
	FRandomStream Random;
	EJREnemyState CurrentState = EJREnemyState::Idle;
	double StateEnterTime = 0.0;
	double LastAttackTime = -1000.0;
	int32 BurstShotsRemaining = 0;
	bool bFullUpdate = false;
	bool bLoggedMoveFailure = false;
	/** [Remap F1] Persegue em linha reta quando não há caminho na navmesh. */
	void ChaseWithoutNavmesh(class AAIController* AI, AActor* ChaseTarget);
	bool bStateInitialized = false;
	bool bForceAggro = false;
	bool bKilledByVehicle = false;
	float FlankAngle = 0.f;
	double StaggerUntil = 0.0;
	FTimerHandle MeleeHitTimer;
	double LastVehicleHitTime = -10.0;
	FVector PendingLaunch = FVector::ZeroVector;
	// [A-073] último acerto pontual (para a queda do corpo)
	FVector LastFeelHitDir = FVector::ZeroVector;
	FName LastFeelHitBone = NAME_None;
	float LastFeelHitDamage = 0.f;
	double LastFeelHitTime = -10.0;
	int32 BrainDebugLogsLeft = 3;
	bool bHoldPosition = false;
	TWeakObjectPtr<AJRVehiclePawn> GrabbedVehicle;
	int32 GrabSlot = INDEX_NONE;
	double NextGrabTime = 0.0;
	FTimerHandle GrabTimer;

	// Vida própria (A-048)
	EJRCalmActivity CalmActivity = EJRCalmActivity::Pause;
	double CalmActivityEnd = 0.0;
	double NextCalmActionTime = 0.0;
	FVector HomeLocation = FVector::ZeroVector;
	FVector CalmFocusPoint = FVector::ZeroVector;
	TWeakObjectPtr<AJREnemyCharacter> FollowLeader;
	float WanderSpeed = 110.f;
	float ChaseSpeed = 380.f;
	float InvestigateMoveSpeed = 230.f;
	FRotator BaseRotationRate = FRotator(0.f, 360.f, 0.f);
	float BaseMaxAcceleration = 2048.f;
	bool bFacingFocus = false;
	bool bHasPendingNoise = false;
	FVector PendingNoiseLocation = FVector::ZeroVector;
	FVector InvestigateLocation = FVector::ZeroVector;
	double InvestigateUntil = 0.0;
	bool bInvestigateArrived = false;
	bool bNeedsInvestigateMove = false;
	FVector LastKnownTargetLocation = FVector::ZeroVector;
	bool bHasLastKnownTarget = false;
};

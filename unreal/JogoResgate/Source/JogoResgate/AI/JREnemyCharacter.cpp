// Copyright utrazin. All Rights Reserved.

#include "AI/JREnemyCharacter.h"
#include "AI/JRAIDirector.h"
#include "AI/JRAimPrediction.h"
#include "AI/JREnemyArchetype.h"
#include "AI/JREnemyBudgetSubsystem.h"
#include "AI/JRNoise.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "Combat/JRHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "FX/JRDamageFXComponent.h"
#include "FX/JRFXSubsystem.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "JogoResgate.h"
#include "TimerManager.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehiclePawn.h"

AJREnemyCharacter::AJREnemyCharacter()
{
	PrimaryActorTick.bCanEverTick = false;
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
	HealthComponent = CreateDefaultSubobject<UJRHealthComponent>(TEXT("HealthComponent"));
	// [Sensação de combate] sangue azul de zumbi (A-057).
	DamageFXComponent = CreateDefaultSubobject<UJRDamageFXComponent>(TEXT("DamageFXComponent"));
	DamageFXComponent->SetBloodType(EJRBloodType::Zombie);
	GetCharacterMovement()->bOrientRotationToMovement = true;
	bUseControllerRotationYaw = false;
}

void AJREnemyCharacter::BeginPlay()
{
	Super::BeginPlay();
	Random.GenerateNewSeed();
	if (Archetype)
	{
		HealthComponent->SetMaxHealth(Archetype->MaxHealth, true);
		GetCharacterMovement()->MaxWalkSpeed = Archetype->MoveSpeed;
	}
	HealthComponent->OnDeath.AddDynamic(this, &AJREnemyCharacter::HandleDeath);
	// [A-073] o evento pontual chega ANTES do dano genérico (que mata): a direção já está guardada na morte
	OnTakePointDamage.AddDynamic(this, &AJREnemyCharacter::HandlePointDamageFeel);
	// O carro atravessa o zumbi (sobreposição) em vez de bater num "poste": nada de atolar.
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Vehicle, ECR_Overlap);
	GetCapsuleComponent()->SetGenerateOverlapEvents(true);
	GetMesh()->SetCollisionResponseToChannel(ECC_Vehicle, ECR_Ignore);
	GetCapsuleComponent()->OnComponentBeginOverlap.AddDynamic(this, &AJREnemyCharacter::HandleCapsuleOverlap);
	FlankAngle = Random.FRandRange(-75.f, 75.f);

	// Vida própria (A-048): cada zumbi com seu ritmo, para ninguém andar sincronizado.
	UCharacterMovementComponent* Move = GetCharacterMovement();
	HomeLocation = GetActorLocation();
	BaseRotationRate = Move->RotationRate;
	BaseMaxAcceleration = Move->MaxAcceleration;
	ChaseSpeed = Move->MaxWalkSpeed * Random.FRandRange(0.85f, 1.2f); // grupos menos "robóticos"
	if (Archetype)
	{
		const bool bRunner = Random.FRand() < Archetype->RunnerChance;
		ChaseSpeed = Archetype->MoveSpeed * (bRunner ? Random.FRandRange(0.9f, 1.2f)
			: Archetype->WalkerChaseSpeedScale * Random.FRandRange(0.9f, 1.05f));
		WanderSpeed = Random.FRandRange(FMath::Min(Archetype->WanderSpeedMin, Archetype->WanderSpeedMax),
			FMath::Max(Archetype->WanderSpeedMin, Archetype->WanderSpeedMax));
		InvestigateMoveSpeed = FMath::Min(Archetype->InvestigateSpeed, ChaseSpeed) * Random.FRandRange(0.9f, 1.1f);
		if (Archetype->AnimRateJitter > 0.f)
		{
			GetMesh()->GlobalAnimRateScale = 1.f + Random.FRandRange(-Archetype->AnimRateJitter, Archetype->AnimRateJitter);
		}
	}
	Move->MaxWalkSpeed = bForceAggro ? ChaseSpeed : WanderSpeed;
	CalmActivity = EJRCalmActivity::Pause;
	CalmActivityEnd = GetWorld()->GetTimeSeconds() + Random.FRandRange(0.3f, 4.f); // começa desfasado
	NextCalmActionTime = CalmActivityEnd + 1.0;
	HealthComponent->OnHealthChanged.AddDynamic(this, &AJREnemyCharacter::HandleHealthChanged);
	SetEnemyState(bHasPatrol ? EJREnemyState::Patrol : EJREnemyState::Idle);

	if (UJREnemyBudgetSubsystem* Budget = GetWorld()->GetSubsystem<UJREnemyBudgetSubsystem>())
	{
		Budget->RegisterEnemy(this); // define full/reduced e inicia o timer
	}
	else
	{
		SetFullUpdate(true);
	}
}

void AJREnemyCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UJREnemyBudgetSubsystem* Budget = GetWorld()->GetSubsystem<UJREnemyBudgetSubsystem>())
	{
		Budget->UnregisterEnemy(this);
	}
	if (AJRVehiclePawn* Car = GrabbedVehicle.Get())
	{
		Car->ReleaseGrabSlot(this);
	}
	GrabbedVehicle.Reset();
	GetWorldTimerManager().ClearTimer(BrainTimer);
	GetWorldTimerManager().ClearTimer(BurstTimer);
	GetWorldTimerManager().ClearTimer(GrabTimer);
	Super::EndPlay(EndPlayReason);
}

void AJREnemyCharacter::SetFullUpdate(bool bFull)
{
	if (bFull == bFullUpdate && BrainTimer.IsValid())
	{
		return;
	}
	bFullUpdate = bFull;
	RestartBrainTimer();
}

void AJREnemyCharacter::RestartBrainTimer()
{
	if (IsDead() || !bUseBuiltInBrain)
	{
		return;
	}
	const float Interval = bFullUpdate ? FullUpdateInterval : ReducedUpdateInterval;
	UE_LOG(LogJR, Log, TEXT("IA %s: cérebro ligado (%s, a cada %.2fs)"), *GetName(), bFullUpdate ? TEXT("completo") : TEXT("reduzido"), Interval);
	// Desfasa inimigos para não decidirem todos no mesmo frame.
	GetWorldTimerManager().SetTimer(BrainTimer, this, &AJREnemyCharacter::UpdateBrain, Interval, true, Random.FRandRange(0.f, Interval));
}

void AJREnemyCharacter::SetEnemyState(EJREnemyState NewState)
{
	if (NewState == CurrentState && bStateInitialized)
	{
		return;
	}
	bStateInitialized = true;
	const EJREnemyState Old = CurrentState;
	CurrentState = NewState;
	StateEnterTime = GetWorld()->GetTimeSeconds();
	if (NewState == EJREnemyState::Alert && Archetype && Archetype->AlertSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, Archetype->AlertSound, GetActorLocation());
	}
	if (IsEngaged() || NewState == EJREnemyState::Dead)
	{
		// Viu o alvo (ou morreu): esquece barulho e atividade calma.
		InvestigateUntil = 0.0;
		bHasPendingNoise = false;
		FollowLeader.Reset();
	}
	if (NewState == EJREnemyState::Alert && AlertGroanLoudness > 0.f && !bForceAggro)
	{
		// Rosnado: zumbis calmos por perto vêm ver (e atacam se enxergarem o jogador).
		UJRNoise::ReportNoise(this, GetActorLocation(), AlertGroanLoudness);
	}
	UE_LOG(LogJR, Log, TEXT("IA %s: %s -> %s (controller=%s)"), *GetName(), *UEnum::GetValueAsString(Old),
		*UEnum::GetValueAsString(NewState), *GetNameSafe(GetController()));
	OnEnemyStateChanged.Broadcast(Old, NewState);
}

void AJREnemyCharacter::UpdateBrain()
{
	if (IsDead() || !Archetype)
	{
		UE_LOG(LogJR, Warning, TEXT("IA %s: sem Archetype ou morto, cérebro parado"), *GetName());
		GetWorldTimerManager().ClearTimer(BrainTimer);
		return;
	}
	if (GrabbedVehicle.IsValid())
	{
		return; // agarrado no carro: TickGrab cuida
	}
	// O alvo é o pawn atual do jogador: veículo ou personagem (perseguição de ambos).
	APawn* PlayerPawn = UGameplayStatics::GetPlayerPawn(this, 0);
	Target = PlayerPawn;
	AAIController* AI = Cast<AAIController>(GetController());
	AJRVehiclePawn* Car = Cast<AJRVehiclePawn>(PlayerPawn);
	if (Car && Car->IsWrecked())
	{
		Car = nullptr;
	}
	FVector CarContact = FVector::ZeroVector;

	const double Now = GetWorld()->GetTimeSeconds();
	const bool bWasEngaged = IsEngaged();
	if (bHasPendingNoise)
	{
		bHasPendingNoise = false;
		if (!bWasEngaged && !bHoldPosition)
		{
			BeginInvestigate(PendingNoiseLocation, Now);
		}
	}

	FJREnemyDecisionInput In;
	In.Current = CurrentState;
	In.TimeInState = static_cast<float>(Now - StateEnterTime);
	In.bInvestigating = Now < InvestigateUntil;
	if (Car)
	{
		// Carro: distância até a lataria (o centro do carro fica a mais de 2 m de quem está encostado).
		In.DistanceToTarget = Car->GetDistanceToBody(GetActorLocation(), &CarContact);
		// Carro faz barulho: dentro do raio de perseguição o zumbi sempre "sabe" onde ele está.
		In.bHasLineOfSight = In.DistanceToTarget <= VehicleChaseRadius;
	}
	else if (PlayerPawn)
	{
		In.DistanceToTarget = static_cast<float>(FVector::Dist(GetActorLocation(), PlayerPawn->GetActorLocation()));
		// Traço de visão só quando o alvo está perto o bastante para importar (custo).
		// Calmo: só enxerga dentro do cone (ou bem perto). Já perseguindo: sem cone.
		bool bWorthTracing = In.DistanceToTarget <= (bWasEngaged ? Archetype->LoseAggroRadius : Archetype->AggroRadius);
		if (bWorthTracing && !bWasEngaged && In.DistanceToTarget > Archetype->CloseSenseRadius)
		{
			bWorthTracing = IsInSightCone(PlayerPawn->GetActorLocation());
		}
		In.bHasLineOfSight = bWorthTracing && AI && AI->LineOfSightTo(PlayerPawn);
		if (In.bHasLineOfSight)
		{
			LastKnownTargetLocation = PlayerPawn->GetActorLocation();
			bHasLastKnownTarget = true;
		}
	}
	if (PlayerPawn && bForceAggro)
	{
		In.bHasLineOfSight = true;
		In.DistanceToTarget = FMath::Min(In.DistanceToTarget, Archetype->AggroRadius * 0.9f);
	}

	// Barricada: parado no meio da estrada até o carro chegar perto (ou o jogador descer).
	if (bHoldPosition)
	{
		if (Car && In.DistanceToTarget > HoldReleaseDistance)
		{
			if (AI)
			{
				AI->StopMovement();
				if (In.DistanceToTarget < VehicleChaseRadius)
				{
					AI->SetFocus(Car);
				}
			}
			return;
		}
		bHoldPosition = false;
	}

	FJREnemyDecisionParams P;
	P.AggroRadius = Archetype->AggroRadius;
	P.LoseAggroRadius = Archetype->LoseAggroRadius;
	P.AttackRange = Archetype->AttackRange;
	P.AlertDuration = Archetype->AlertDuration;
	P.bHasPatrol = bHasPatrol;

	if (Car)
	{
		// Carro: aggro e desistência maiores (o zumbi corre atrás do carro de longe).
		P.AggroRadius = FMath::Max(P.AggroRadius, VehicleChaseRadius);
		P.LoseAggroRadius = FMath::Max(P.LoseAggroRadius, VehicleChaseRadius * 1.25f);
	}
	EJREnemyState Next = FJREnemyStateLogic::Decide(In, P);
	const bool bNextCalm = Next == EJREnemyState::Idle || Next == EJREnemyState::Patrol;
	if (bWasEngaged && bNextCalm && bHasLastKnownTarget && !Car)
	{
		// Perdeu o jogador de vista: vai procurar onde o viu por último antes de voltar a vagar.
		bHasLastKnownTarget = false;
		BeginInvestigate(LastKnownTargetLocation, Now);
		Next = EJREnemyState::Investigate;
	}
	if (Now < StaggerUntil && Next != EJREnemyState::Dead)
	{
		if (AI)
		{
			AI->StopMovement();
		}
		return; // cambaleando
	}
	if (BrainDebugLogsLeft > 0 && PlayerPawn && In.DistanceToTarget < P.LoseAggroRadius)
	{
		--BrainDebugLogsLeft;
		UE_LOG(LogJR, Log, TEXT("IA %s: alvo=%s dist=%.0f visão=%d estado=%s -> %s"), *GetName(), *PlayerPawn->GetName(),
			In.DistanceToTarget, In.bHasLineOfSight ? 1 : 0, *UEnum::GetValueAsString(CurrentState), *UEnum::GetValueAsString(Next));
	}
	SetEnemyState(Next);

	// Colado no carro devagar: às vezes pula no capô/lateral e se agarra.
	if (Car && (Next == EJREnemyState::Chase || Next == EJREnemyState::Attack) && In.DistanceToTarget <= GrabReach
		&& Archetype->AttackType == EJREnemyAttackType::Melee && GetWorld()->GetTimeSeconds() >= NextGrabTime
		&& Random.FRand() < GrabChance && TryGrabVehicle(Car))
	{
		return;
	}

	if (!AI)
	{
		return;
	}
	switch (Next)
	{
	case EJREnemyState::Chase:
		SetFaceFocus(false);
		ApplyMovementStyle(false, ChaseSpeed);
		if (Car)
		{
			MoveTowardVehicle(AI, Car, In.DistanceToTarget, CarContact);
		}
		else if (PlayerPawn && In.DistanceToTarget > FlankDistance)
		{
			// Longe: vai para um ponto ao lado do jogador (cada zumbi com seu ângulo) e cerca.
			const FVector ToMe = (GetActorLocation() - PlayerPawn->GetActorLocation()).GetSafeNormal2D();
			const FVector Side = ToMe.RotateAngleAxis(FlankAngle, FVector::UpVector);
			const FVector Goal = PlayerPawn->GetActorLocation() + Side * (FlankDistance * 0.6f);
			const EPathFollowingRequestResult::Type Result = AI->MoveToLocation(Goal, 80.f, true, true, true, true);
			if (Result == EPathFollowingRequestResult::Failed)
			{
				AI->MoveToActor(PlayerPawn, Archetype->AttackRange * 0.8f, true, true, true);
			}
		}
		else if (PlayerPawn)
		{
			const EPathFollowingRequestResult::Type Result = AI->MoveToActor(PlayerPawn, Archetype->AttackRange * 0.8f, true, true, true);
			if (Result == EPathFollowingRequestResult::Failed && !bLoggedMoveFailure)
			{
				bLoggedMoveFailure = true;
				UE_LOG(LogJR, Warning, TEXT("IA %s: MoveToActor falhou (sem navmesh ou alvo fora da navmesh?)"), *GetName());
			}
		}
		break;
	case EJREnemyState::Attack:
		AI->StopMovement();
		ApplyMovementStyle(false, ChaseSpeed);
		SetFaceFocus(true); // parado, vira para o jogador antes do golpe
		if (PlayerPawn)
		{
			AI->SetFocus(PlayerPawn);
		}
		TryAttack();
		break;
	case EJREnemyState::Alert:
		AI->StopMovement();
		ApplyMovementStyle(false, ChaseSpeed);
		SetFaceFocus(true);
		if (PlayerPawn)
		{
			AI->SetFocus(PlayerPawn);
		}
		break;
	case EJREnemyState::Investigate:
		UpdateInvestigate(AI, Now);
		break;
	case EJREnemyState::Dead:
		break;
	default:
		UpdateCalm(AI, PlayerPawn, Now);
		break;
	}
}

void AJREnemyCharacter::MoveTowardVehicle(AAIController* AI, AJRVehiclePawn* Car, float BodyDistance, const FVector& ContactPoint)
{
	const FVector CarVelocity = Car->GetVelocity();
	FVector Goal;
	if (CarVelocity.Size2D() < 300.f || BodyDistance < 400.f)
	{
		// Devagar ou perto: vai até o ponto mais próximo da lataria e para encostado nela.
		const float Radius = GetCapsuleComponent()->GetScaledCapsuleRadius();
		Goal = ContactPoint + (GetActorLocation() - ContactPoint).GetSafeNormal2D() * (Radius + 30.f);
	}
	else
	{
		// Andando: corre para onde o carro vai estar (intercepta).
		const float MySpeed = FMath::Max(GetCharacterMovement()->MaxWalkSpeed, 100.f);
		const float LeadTime = FMath::Min(BodyDistance / MySpeed, VehicleInterceptMaxTime);
		Goal = Car->GetActorLocation() + CarVelocity * LeadTime;
		// Cada zumbi mira um pouco para um lado da pista: o grupo "fecha" a estrada em vez de fazer fila.
		const FVector Side = FVector::CrossProduct(FVector::UpVector, CarVelocity.GetSafeNormal2D());
		Goal += Side * ((FlankAngle / 75.f) * VehicleRoadSpread);
	}
	const EPathFollowingRequestResult::Type Result = AI->MoveToLocation(Goal, 30.f, false, true, true, true);
	if (Result == EPathFollowingRequestResult::Failed)
	{
		AI->MoveToActor(Car, 50.f, false, true, true);
	}
}

bool AJREnemyCharacter::TryGrabVehicle(AJRVehiclePawn* Car)
{
	if (!Car || IsDead() || GrabbedVehicle.IsValid() || Car->IsWrecked())
	{
		return false;
	}
	const int32 Slot = Car->TryReserveGrabSlot(this);
	USceneComponent* Point = Slot != INDEX_NONE ? Car->GetGrabPoint(Slot) : nullptr;
	if (!Point)
	{
		if (Slot != INDEX_NONE)
		{
			Car->ReleaseGrabSlot(this);
		}
		return false;
	}
	GrabbedVehicle = Car;
	GrabSlot = Slot;
	GetWorldTimerManager().ClearTimer(MeleeHitTimer);
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
		AI->ClearFocus(EAIFocusPriority::Gameplay);
	}
	// Sem física e sem colisão: vai "de carona" preso ao ponto do carro.
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AttachToComponent(Point, FAttachmentTransformRules(EAttachmentRule::SnapToTarget, EAttachmentRule::SnapToTarget,
		EAttachmentRule::KeepWorld, false));
	SetEnemyState(EJREnemyState::Attack);
	GetWorldTimerManager().SetTimer(GrabTimer, this, &AJREnemyCharacter::TickGrab, GrabAttackInterval, true, 0.2f);
	UE_LOG(LogJR, Log, TEXT("IA %s: agarrou o carro (ponto %d)"), *GetName(), Slot);
	Car->NotifyZombieCarEvent(EJRZombieCarEvent::ZombieGrabbed, this, GetActorLocation(), static_cast<float>(Slot));
	return true;
}

void AJREnemyCharacter::TickGrab()
{
	AJRVehiclePawn* Car = GrabbedVehicle.Get();
	if (!Car || IsDead() || Car->IsWrecked())
	{
		ReleaseFromVehicle(false, FVector::ZeroVector);
		return;
	}
	if (Archetype && Archetype->AttackMontage)
	{
		PlayAnimMontage(Archetype->AttackMontage);
	}
	if (UJRVehicleDamageComponent* Damage = Car->GetDamageComponent())
	{
		const float Amount = GrabDamagePerSecond * GrabAttackInterval;
		const EJRVehicleZone Zone = Car->GetGrabZone(GrabSlot);
		Damage->ApplyZoneDamage(Zone, Amount);
		if (Zone == EJRVehicleZone::Front && !Car->IsWrecked())
		{
			Damage->ApplyZoneDamage(EJRVehicleZone::Engine, Amount * 0.5f); // arranca peças do motor
		}
		Car->NotifyZombieCarEvent(EJRZombieCarEvent::ZombieHitCar, this, GetActorLocation(), Amount);
	}
}

void AJREnemyCharacter::ReleaseFromVehicle(bool bKill, const FVector& LaunchVelocity)
{
	AJRVehiclePawn* Car = GrabbedVehicle.Get();
	const bool bWasGrabbing = GrabbedVehicle.IsValid() || GrabSlot != INDEX_NONE;
	GetWorldTimerManager().ClearTimer(GrabTimer);
	GrabbedVehicle.Reset();
	GrabSlot = INDEX_NONE;
	if (Car)
	{
		Car->ReleaseGrabSlot(this);
	}
	if (!bWasGrabbing)
	{
		return;
	}
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	SetActorRotation(FRotator(0.f, GetActorRotation().Yaw, 0.f));
	NextGrabTime = GetWorld()->GetTimeSeconds() + GrabCooldown;
	if (IsDead())
	{
		return;
	}
	if (bKill)
	{
		if (Car)
		{
			Car->NotifyZombieCarEvent(EJRZombieCarEvent::ZombieThrownOff, this, GetActorLocation(), static_cast<float>(Car->GetVelocity().Size()) * 0.036f);
		}
		KillWithLaunch(LaunchVelocity, Car ? Car->GetController() : nullptr, Car);
		return;
	}
	// Desceu vivo (jogador saiu do carro): cai ao lado e volta a perseguir.
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	GetCharacterMovement()->SetMovementMode(MOVE_Falling);
	SetEnemyState(EJREnemyState::Chase);
}

void AJREnemyCharacter::KillWithLaunch(const FVector& LaunchVelocity, AController* InstigatorController, AActor* Causer)
{
	if (IsDead())
	{
		return;
	}
	PendingLaunch = LaunchVelocity;
	bKilledByVehicle = true;
	UGameplayStatics::ApplyDamage(this, 9999.f, InstigatorController, Causer, nullptr);
}

void AJREnemyCharacter::FreezeRagdoll()
{
	if (!IsDead())
	{
		return;
	}
	// Dorme em vez de desligar a física (desligar faria o corpo "levantar" na pose da animação).
	GetMesh()->PutAllRigidBodiesToSleep();
	SetLifeSpan(3.f);
}

bool AJREnemyCharacter::TryAttack()
{
	AActor* TargetActor = Target.Get();
	if (!Archetype || !TargetActor || IsDead())
	{
		return false;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	if (Now - LastAttackTime < Archetype->AttackInterval)
	{
		return false;
	}
	LastAttackTime = Now;
	if (Archetype->AttackMontage)
	{
		PlayAnimMontage(Archetype->AttackMontage);
	}

	if (Archetype->AttackType == EJREnemyAttackType::Melee)
	{
		// Golpe com preparação: o dano só sai se o alvo ainda estiver ao alcance (dá para desviar).
		GetWorldTimerManager().SetTimer(MeleeHitTimer, this, &AJREnemyCharacter::ResolveMeleeHit, MeleeWindup, false);
		return true;
	}

	BurstShotsRemaining = FMath::Max(1, Archetype->BurstCount);
	FireRangedShot();
	return true;
}

FVector AJREnemyCharacter::GetMuzzleLocation() const
{
	return GetMesh() && GetMesh()->DoesSocketExist(MuzzleSocket) ? GetMesh()->GetSocketLocation(MuzzleSocket)
		: GetActorLocation() + FVector(0.f, 0.f, BaseEyeHeight);
}

void AJREnemyCharacter::FireRangedShot()
{
	AActor* TargetActor = Target.Get();
	if (!Archetype || !TargetActor || IsDead() || BurstShotsRemaining <= 0)
	{
		return;
	}
	--BurstShotsRemaining;

	const FVector Muzzle = GetMuzzleLocation();
	FVector AimPoint;
	double TimeToHit = 0.0;
	FJRAimPrediction::PredictInterceptPoint(Muzzle, TargetActor->GetActorLocation(), TargetActor->GetVelocity(),
		Archetype->ProjectileSpeed, AimPoint, TimeToHit);
	const FVector Dir = FJRAimPrediction::ApplySpread(AimPoint - Muzzle, Archetype->SpreadHalfAngleDegrees, Random);

	if (Archetype->AttackType == EJREnemyAttackType::Projectile && Archetype->ProjectileClass)
	{
		FActorSpawnParameters Params;
		Params.Owner = this;
		Params.Instigator = this;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (AActor* Projectile = GetWorld()->SpawnActor<AActor>(Archetype->ProjectileClass, Muzzle, Dir.Rotation(), Params))
		{
			if (UProjectileMovementComponent* Move = Projectile->FindComponentByClass<UProjectileMovementComponent>())
			{
				Move->Velocity = Dir * Archetype->ProjectileSpeed;
			}
		}
	}
	else
	{
		FHitResult Hit;
		FCollisionQueryParams Query(SCENE_QUERY_STAT(JREnemyShot), true, this);
		const FVector End = Muzzle + Dir * (Archetype->AttackRange * 1.5f);
		const bool bShotHit = GetWorld()->LineTraceSingleByChannel(Hit, Muzzle, End, ECC_Visibility, Query);
		if (bShotHit && Hit.GetActor())
		{
			UGameplayStatics::ApplyPointDamage(Hit.GetActor(), Archetype->AttackDamage, Dir, Hit, GetController(), this, nullptr);
		}
		// [Sensação de combate] tiro do zumbi visível (plasma verde-tóxico).
		if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
		{
			const FLinearColor Toxic(0.35f, 1.f, 0.12f, 1.f);
			FX->SpawnPlasmaBolt(Muzzle, bShotHit ? FVector(Hit.ImpactPoint) : End, Toxic, 18.f, 7000.f, 60.f, 5.f, 300.f, false);
			FX->SpawnFlash(Muzzle, Toxic, 18.f, 5.f, 18.f, 0.06f, 0.f, 0.f);
		}
	}

	if (BurstShotsRemaining > 0)
	{
		GetWorldTimerManager().SetTimer(BurstTimer, this, &AJREnemyCharacter::FireRangedShot, Archetype->BurstShotInterval, false);
	}
}

void AJREnemyCharacter::HandleDeath(UJRHealthComponent* Health, AActor* Killer)
{
	SetEnemyState(EJREnemyState::Dead);
	if (GrabbedVehicle.IsValid() || GrabSlot != INDEX_NONE)
	{
		ReleaseFromVehicle(false, FVector::ZeroVector); // morto: só solta do carro
	}
	GetWorldTimerManager().ClearTimer(BrainTimer);
	GetWorldTimerManager().ClearTimer(BurstTimer);
	GetWorldTimerManager().ClearTimer(MeleeHitTimer);
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
		AI->ClearFocus(EAIFocusPriority::Gameplay);
	}
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
	GetMesh()->SetSimulatePhysics(true);
	SetLifeSpan(Archetype ? Archetype->CorpseLifetime : 10.f);
	if (!PendingLaunch.IsZero())
	{
		GetMesh()->SetAllPhysicsLinearVelocity(PendingLaunch, false); // atropelado/explosão: o corpo todo voa longe
		PendingLaunch = FVector::ZeroVector;
	}
	else if (GetWorld()->GetTimeSeconds() - LastFeelHitTime < 0.25 && !LastFeelHitDir.IsNearlyZero())
	{
		// [A-073] morte por tiro/golpe: o corpo cede PARA LONGE do golpe (antes desabava no lugar).
		// Só velocidade no ragdoll recém-ligado deste zumbi (não mexe em mais nada).
		const float KickScale = FMath::Clamp(LastFeelHitDamage / 40.f, 0.6f, 1.6f);
		const FVector PushDir = (LastFeelHitDir.GetSafeNormal2D() + FVector(0.f, 0.f, 0.15f)).GetSafeNormal();
		GetMesh()->SetAllPhysicsLinearVelocity(PushDir * (DeathPushSpeed * KickScale), true);
		if (!LastFeelHitBone.IsNone() && GetMesh()->GetBoneIndex(LastFeelHitBone) != INDEX_NONE)
		{
			GetMesh()->AddImpulse(LastFeelHitDir * (DeathBoneKick * KickScale), LastFeelHitBone, true);
		}
	}
	if (UJREnemyBudgetSubsystem* Budget = GetWorld()->GetSubsystem<UJREnemyBudgetSubsystem>())
	{
		Budget->RegisterRagdoll(this); // teto de ragdolls ativos (os mais antigos congelam)
	}
	if (AJRAIDirector* Director = AJRAIDirector::Find(this))
	{
		Director->NotifyEnemyKilled(this);
	}
	DropLoot();
	UE_LOG(LogJR, Log, TEXT("IA %s morreu"), *GetName());
	OnEnemyDied.Broadcast(this);
}

void AJREnemyCharacter::HandlePointDamageFeel(AActor* DamagedActor, float Damage, AController* InstigatedBy, FVector HitLocation,
	UPrimitiveComponent* FHitComponent, FName BoneName, FVector ShotFromDirection, const UDamageType* DamageType,
	AActor* DamageCauser)
{
	// [A-073] ShotFromDirection = direção do tiro/golpe (do atirador para o alvo)
	FVector HitDir = ShotFromDirection;
	if (HitDir.IsNearlyZero() && DamageCauser)
	{
		HitDir = GetActorLocation() - DamageCauser->GetActorLocation();
	}
	LastFeelHitDir = HitDir.GetSafeNormal();
	LastFeelHitBone = BoneName;
	LastFeelHitDamage = Damage;
	LastFeelHitTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
}

void AJREnemyCharacter::HandleCapsuleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (OtherActor && OtherActor->IsA<AJRVehiclePawn>())
	{
		HitByVehicle(OtherActor);
	}
}

void AJREnemyCharacter::HitByVehicle(AActor* Vehicle)
{
	AJRVehiclePawn* Car = Cast<AJRVehiclePawn>(Vehicle);
	const double Now = GetWorld()->GetTimeSeconds();
	if (!Car || IsDead() || GrabbedVehicle.IsValid() || Now - LastVehicleHitTime < 0.5)
	{
		return;
	}
	const FVector Vel = Car->GetVelocity();
	const float Kmh = static_cast<float>(Vel.Size()) * 0.036f;
	if (Kmh < BumpMinSpeedKmh)
	{
		return; // carro parado/quase parado: zumbi encostando não é atropelamento
	}
	LastVehicleHitTime = Now;
	const FVector Away = (GetActorLocation() - Car->GetActorLocation()).GetSafeNormal2D();
	// Só conta a velocidade do carro NA DIREÇÃO do zumbi (raspão de lado só empurra).
	const float ImpactKmh = FMath::Max(0.f, static_cast<float>(FVector::DotProduct(Vel, Away))) * 0.036f;
	if (ImpactKmh >= RunOverSpeedKmh)
	{
		// Arremesso (ragdoll): herda a velocidade do carro, para cima e para o lado.
		const FVector Launch = Vel * 0.9f + Away * 300.f + FVector(0.f, 0.f, 350.f + ImpactKmh * 9.f);
		if (UJRVehicleDamageComponent* Damage = Car->GetDamageComponent())
		{
			Damage->ApplyZoneDamage(EJRVehicleZone::Front, RunOverCarDamage + ImpactKmh * 0.03f);
		}
		Car->ApplyZombieDrag(RunOverDragFraction); // cada zumbi freia um pouco (o carro limita o total)
		Car->NotifyZombieCarEvent(EJRZombieCarEvent::RunOver, this, GetActorLocation(), ImpactKmh);
		KillWithLaunch(Launch, Car->GetController(), Car);
		return;
	}
	// Devagar: às vezes pula no carro e se agarra.
	if (Kmh < Car->GrabMaxSpeedKmh && Archetype && Archetype->AttackType == EJREnemyAttackType::Melee
		&& Now >= NextGrabTime && Random.FRand() < GrabWhenBumpedChance && TryGrabVehicle(Car))
	{
		return;
	}
	// Senão é empurrado e cambaleia, mas continua vindo.
	LaunchCharacter(Away * (300.f + Kmh * 20.f) + FVector(0.f, 0.f, 200.f), true, true);
	UGameplayStatics::ApplyDamage(this, 5.f, Car->GetController(), Car, nullptr);
	StaggerUntil = Now + StaggerTime * 2.f;
	Car->NotifyZombieCarEvent(EJRZombieCarEvent::ZombiePushed, this, GetActorLocation(), Kmh);
}

void AJREnemyCharacter::ResolveMeleeHit()
{
	AActor* TargetActor = Target.Get();
	if (!Archetype || !TargetActor || IsDead())
	{
		return;
	}
	if (AJRVehiclePawn* Car = Cast<AJRVehiclePawn>(TargetActor))
	{
		// Carro: soco na lataria mais próxima (dano na zona, sem furar pneu).
		FVector Contact;
		if (Car->GetDistanceToBody(GetActorLocation(), &Contact) > Archetype->AttackRange * 1.35f + 60.f)
		{
			return; // o carro saiu
		}
		const float Amount = Archetype->AttackDamage * VehicleAttackDamageScale;
		if (UJRVehicleDamageComponent* Damage = Car->GetDamageComponent())
		{
			Damage->ApplyDamageAtLocation(Contact, Amount, false);
		}
		Car->NotifyZombieCarEvent(EJRZombieCarEvent::ZombieHitCar, this, Contact, Amount);
		return;
	}
	const float Dist = static_cast<float>(FVector::Dist2D(TargetActor->GetActorLocation(), GetActorLocation()));
	if (Dist > Archetype->AttackRange * 1.35f + 60.f)
	{
		return; // desviou
	}
	// Dano pontual: no veículo vira dano por zona (UJRVehicleDamageComponent).
	FHitResult Hit;
	// [Sensação de combate] o golpe acerta um ponto do corpo (coxa, braço, tronco) virado para o zumbi:
	// o sangue e a ferida aparecem ali no herói (A-057).
	if (!UJRDamageFXComponent::FindBodyHit(TargetActor, GetActorLocation(), -0.55f, 0.75f, Hit))
	{
		Hit.ImpactPoint = TargetActor->GetActorLocation();
		Hit.Location = Hit.ImpactPoint;
	}
	const FVector Dir = (TargetActor->GetActorLocation() - GetActorLocation()).GetSafeNormal();
	UGameplayStatics::ApplyPointDamage(TargetActor, Archetype->AttackDamage, Dir, Hit, GetController(), this, nullptr);
}

void AJREnemyCharacter::HandleHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta)
{
	if (Delta >= 0.f || NewHealth <= 0.f || IsDead())
	{
		return;
	}
	StaggerUntil = GetWorld()->GetTimeSeconds() + StaggerTime;
	GetWorldTimerManager().ClearTimer(MeleeHitTimer); // apanhou: perde o golpe
	if (Archetype && Archetype->HitReactMontage)
	{
		PlayAnimMontage(Archetype->HitReactMontage);
	}
	// Levou tiro de longe: agora sabe onde o jogador está.
	bForceAggro = true;
	bHoldPosition = false;
}

void AJREnemyCharacter::DropLoot()
{
	if (bHasGuaranteedDrop)
	{
		if (AJRPickup* Drop = AJRPickup::SpawnPickup(GetWorld(), GuaranteedDrop, 1.f, GetActorLocation() - FVector(0.f, 0.f, 70.f)))
		{
			Drop->SetDisplayMesh(GuaranteedDropMesh, 1.3f);
		}
		return;
	}
	if (Random.FRand() > DropChance)
	{
		return;
	}
	if (bKilledByVehicle)
	{
		// Atropelou: às vezes solta um pouco de nitro (o carro pega passando por cima).
		if (Random.FRand() < 0.5f)
		{
			AJRPickup::SpawnPickup(GetWorld(), EJRPickupType::Nitro, 0.12f, GetActorLocation() - FVector(0.f, 0.f, 40.f), 20.f);
		}
		return;
	}
	// Mais munição; vida e Fúria são mais raros.
	const float Roll = Random.FRand();
	EJRPickupType Type = EJRPickupType::Ammo;
	float Amount = 12.f;
	if (Roll > 0.92f)
	{
		Type = EJRPickupType::Fury;
		Amount = 10.f;
	}
	else if (Roll > 0.8f)
	{
		Type = EJRPickupType::Health;
		Amount = 25.f;
	}
	// [Roda de itens, A-055] parte das antigas curas (0,70..0,80) vira 1 bandagem para a bolsa.
	else if (Roll > 0.7f)
	{
		Type = EJRPickupType::Bandage;
		Amount = 1.f;
	}
	AJRPickup::SpawnPickup(GetWorld(), Type, Amount, GetActorLocation() - FVector(0.f, 0.f, 40.f), 30.f);
}

// ============================================================================================
// Vida própria (A-048): vagar, manada, comer/bater, audição e investigação. Tudo dentro do
// UpdateBrain (timer desfasado de 0,1 s perto / 0,5 s longe), sem Tick.
// ============================================================================================

bool AJREnemyCharacter::HearNoise(FVector NoiseLocation, float InLoudness)
{
	if (IsDead() || !Archetype || GrabbedVehicle.IsValid() || bHoldPosition || bForceAggro || IsEngaged())
	{
		return false; // já caçando (ou preso na barricada/carro): barulho não muda nada
	}
	const float Radius = InLoudness * Archetype->HearingScale;
	if (Radius <= 0.f || FVector::DistSquared(GetActorLocation(), NoiseLocation) > FMath::Square(Radius))
	{
		return false;
	}
	// Reage no próximo "pensamento" (0,1 a 0,5 s): atraso natural e diferente para cada um.
	bHasPendingNoise = true;
	PendingNoiseLocation = NoiseLocation;
	return true;
}

bool AJREnemyCharacter::IsInSightCone(const FVector& Point) const
{
	const FVector ToPoint = (Point - GetActorLocation()).GetSafeNormal2D();
	if (ToPoint.IsNearlyZero())
	{
		return true;
	}
	const float HalfAngle = Archetype ? Archetype->SightHalfAngleDegrees : 55.f;
	const double CosHalf = FMath::Cos(FMath::DegreesToRadians(static_cast<double>(HalfAngle)));
	return FVector::DotProduct(GetActorForwardVector().GetSafeNormal2D(), ToPoint) >= CosHalf;
}

void AJREnemyCharacter::ApplyMovementStyle(bool bShamble, float NewMaxSpeed)
{
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->MaxWalkSpeed = NewMaxSpeed;
	Move->RotationRate = bShamble ? FRotator(0.f, ShambleTurnRate, 0.f) : BaseRotationRate;
	Move->MaxAcceleration = bShamble ? FMath::Min(BaseMaxAcceleration, ShambleMaxAcceleration) : BaseMaxAcceleration;
}

void AJREnemyCharacter::SetFaceFocus(bool bFace)
{
	if (bFacingFocus == bFace)
	{
		return;
	}
	bFacingFocus = bFace;
	// Andando: gira para onde anda. Parado: gira (no RotationRate) para o foco do AIController.
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = !bFace;
	Move->bUseControllerDesiredRotation = bFace;
}

void AJREnemyCharacter::BeginInvestigate(const FVector& Where, double Now)
{
	if (!Archetype)
	{
		return;
	}
	// Cada um mira um ponto um pouco diferente: o grupo se espalha em volta do barulho.
	const FVector Jitter = FVector(Random.FRandRange(-1.f, 1.f), Random.FRandRange(-1.f, 1.f), 0.f).GetSafeNormal()
		* Random.FRandRange(100.f, 350.f);
	InvestigateLocation = Where + Jitter;
	InvestigateUntil = Now + Archetype->InvestigateTime;
	bInvestigateArrived = false;
	bNeedsInvestigateMove = true;
	FollowLeader.Reset();
	// Quando terminar de procurar, começa com uma pausa.
	CalmActivity = EJRCalmActivity::Pause;
	CalmActivityEnd = InvestigateUntil + Random.FRandRange(0.5f, 2.f);
	NextCalmActionTime = CalmActivityEnd + 1.0;
	LogLife(TEXT("ouviu barulho, vai ver"));
}

void AJREnemyCharacter::UpdateInvestigate(AAIController* AI, double Now)
{
	ApplyMovementStyle(true, InvestigateMoveSpeed);
	if (!bInvestigateArrived)
	{
		SetFaceFocus(false);
		AI->ClearFocus(EAIFocusPriority::Gameplay);
		if (FVector::Dist2D(GetActorLocation(), InvestigateLocation) < 220.0)
		{
			bInvestigateArrived = true;
		}
		else if (bNeedsInvestigateMove || AI->GetMoveStatus() == EPathFollowingStatus::Idle)
		{
			bNeedsInvestigateMove = false;
			const EPathFollowingRequestResult::Type Result = AI->MoveToLocation(InvestigateLocation, 120.f, true, true, true, false);
			if (Result == EPathFollowingRequestResult::Failed)
			{
				bInvestigateArrived = true; // sem caminho: olha em volta daqui mesmo
			}
		}
		if (bInvestigateArrived)
		{
			// Chegou: fica alguns segundos olhando em volta e depois desiste.
			AI->StopMovement();
			InvestigateUntil = FMath::Min(InvestigateUntil, Now + static_cast<double>(Random.FRandRange(3.f, 6.f)));
			CalmActivityEnd = InvestigateUntil + Random.FRandRange(0.5f, 2.f);
			NextCalmActionTime = Now;
		}
		return;
	}
	SetFaceFocus(true);
	if (Now >= NextCalmActionTime)
	{
		const FVector Look = FVector::ForwardVector.RotateAngleAxis(Random.FRandRange(0.f, 360.f), FVector::UpVector);
		AI->SetFocalPoint(GetActorLocation() + Look * 500.f, EAIFocusPriority::Gameplay);
		NextCalmActionTime = Now + Random.FRandRange(1.2f, 2.4f);
	}
}

void AJREnemyCharacter::UpdateCalm(AAIController* AI, APawn* PlayerPawn, double Now)
{
	if (!Archetype || !bWanderEnabled)
	{
		AI->ClearFocus(EAIFocusPriority::Gameplay);
		return;
	}
	// Muito longe do jogador: não começa nada novo (ninguém vê; poupa caminhos na navmesh).
	if (PlayerPawn && FVector::DistSquared(GetActorLocation(), PlayerPawn->GetActorLocation()) > FMath::Square(WanderMaxPlayerDistance)
		&& CalmActivity == EJRCalmActivity::Pause)
	{
		return;
	}

	switch (CalmActivity)
	{
	case EJRCalmActivity::Walk:
		if (AI->GetMoveStatus() == EPathFollowingStatus::Idle || Now >= CalmActivityEnd)
		{
			StartCalmPause(AI, Now);
		}
		break;

	case EJRCalmActivity::Follow:
	{
		AJREnemyCharacter* Leader = FollowLeader.Get();
		if (!Leader || Leader->IsDead() || Now >= CalmActivityEnd)
		{
			StartCalmPause(AI, Now);
		}
		else if (Leader->IsEngaged() || Leader->GetEnemyState() == EJREnemyState::Investigate)
		{
			// O líder viu/ouviu algo: a manada vai junto.
			BeginInvestigate(Leader->GetActorLocation(), Now);
		}
		else if (AI->GetMoveStatus() == EPathFollowingStatus::Idle
			&& FVector::Dist2D(GetActorLocation(), Leader->GetActorLocation()) > 450.0)
		{
			AI->MoveToActor(Leader, Random.FRandRange(180.f, 380.f), true, true, false);
		}
		break;
	}

	case EJRCalmActivity::Feed:
	case EJRCalmActivity::Bang:
		if (Now >= CalmActivityEnd)
		{
			StartCalmPause(AI, Now);
		}
		else if (AI->GetMoveStatus() != EPathFollowingStatus::Moving)
		{
			// Chegou encostado: vira para o alvo e bate/come de tempos em tempos.
			SetFaceFocus(true);
			AI->SetFocalPoint(CalmFocusPoint, EAIFocusPriority::Gameplay);
			if (Now >= NextCalmActionTime)
			{
				const bool bFeed = CalmActivity == EJRCalmActivity::Feed;
				UAnimMontage* Montage = bFeed && Archetype->FeedMontage ? Archetype->FeedMontage.Get() : Archetype->AttackMontage.Get();
				const float Rate = bFeed && !Archetype->FeedMontage ? Random.FRandRange(0.5f, 0.7f) : Random.FRandRange(0.8f, 1.05f);
				PlayLifeMontage(Montage, Rate);
				NextCalmActionTime = Now + (bFeed ? Random.FRandRange(2.f, 4.f) : Random.FRandRange(1.1f, 2.2f));
			}
		}
		break;

	case EJRCalmActivity::Pause:
	default:
		if (Now >= CalmActivityEnd)
		{
			ChooseNextCalmActivity(AI, Now);
		}
		else if (Now >= NextCalmActionTime)
		{
			PlayIdleVariation();
			NextCalmActionTime = CalmActivityEnd + 1.0; // no máximo uma variação por pausa
		}
		break;
	}
}

void AJREnemyCharacter::StartCalmPause(AAIController* AI, double Now)
{
	CalmActivity = EJRCalmActivity::Pause;
	FollowLeader.Reset();
	AI->StopMovement();
	SetFaceFocus(true);
	const float PauseMin = Archetype ? Archetype->WanderPauseMin : 2.f;
	const float PauseMax = Archetype ? FMath::Max(Archetype->WanderPauseMax, PauseMin) : 6.f;
	const float PauseTime = Random.FRandRange(PauseMin, PauseMax);
	CalmActivityEnd = Now + PauseTime;
	NextCalmActionTime = Now + Random.FRandRange(0.4f, FMath::Max(0.5f, PauseTime * 0.7f));
	if (Archetype && Random.FRand() < Archetype->TurnChance)
	{
		// Vira devagar para outro lado (giro arrastado).
		const float Yaw = Random.FRandRange(60.f, 160.f) * (Random.FRand() < 0.5f ? -1.f : 1.f);
		const FVector Look = GetActorForwardVector().GetSafeNormal2D().RotateAngleAxis(Yaw, FVector::UpVector);
		AI->SetFocalPoint(GetActorLocation() + Look * 500.f, EAIFocusPriority::Gameplay);
	}
	else
	{
		AI->ClearFocus(EAIFocusPriority::Gameplay);
	}
	LogLife(TEXT("pausa"));
}

void AJREnemyCharacter::ChooseNextCalmActivity(AAIController* AI, double Now)
{
	AI->ClearFocus(EAIFocusPriority::Gameplay);
	SetFaceFocus(false);

	// 1) Encostado (ou quase) em parede/destroço/corpo: bate ou "come".
	bool bFeedSpot = false;
	FVector SpotPoint = FVector::ZeroVector;
	if (Random.FRand() < 0.6f && FindCalmSpot(bFeedSpot, SpotPoint))
	{
		const float Chance = bFeedSpot ? Archetype->FeedChance : Archetype->BangChance;
		if (Random.FRand() < Chance)
		{
			CalmActivity = bFeedSpot ? EJRCalmActivity::Feed : EJRCalmActivity::Bang;
			CalmFocusPoint = SpotPoint;
			CalmActivityEnd = Now + (bFeedSpot ? Random.FRandRange(8.f, 16.f) : Random.FRandRange(5.f, 10.f));
			NextCalmActionTime = Now + Random.FRandRange(0.3f, 1.2f);
			ApplyMovementStyle(true, WanderSpeed);
			const float Reach = GetCapsuleComponent()->GetScaledCapsuleRadius() + 55.f;
			if (FVector::Dist2D(GetActorLocation(), SpotPoint) > Reach + 30.f)
			{
				// Chega pertinho antes (o ponto fica na parede, fora da navmesh: projeta).
				const FVector Approach = SpotPoint + (GetActorLocation() - SpotPoint).GetSafeNormal2D() * Reach;
				AI->MoveToLocation(Approach, 30.f, true, true, true, false);
			}
			LogLife(bFeedSpot ? TEXT("comendo") : TEXT("batendo"));
			return;
		}
	}

	// 2) Manada: segue um vizinho calmo.
	if (Random.FRand() < Archetype->HerdChance && StartFollow(AI, Now))
	{
		return;
	}

	// 3) Anda até um ponto aleatório perto de casa.
	if (!StartWalk(AI, Now))
	{
		StartCalmPause(AI, Now); // sem navmesh/caminho: tenta de novo depois
	}
}

bool AJREnemyCharacter::StartWalk(AAIController* AI, double Now)
{
	UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!NavSys || !Archetype)
	{
		return false;
	}
	const float RadiusMin = FMath::Min(Archetype->WanderRadiusMin, Archetype->WanderRadiusMax);
	const float RadiusMax = FMath::Max(Archetype->WanderRadiusMin, Archetype->WanderRadiusMax);
	FVector Origin = HomeLocation;
	float Distance = Random.FRandRange(RadiusMin, RadiusMax);
	const double FromHome = FVector::Dist2D(GetActorLocation(), HomeLocation);
	if (FromHome <= RadiusMax * 1.5)
	{
		// Perto de casa: o próximo ponto sai de onde ele está (passeio contínuo), mas sem fugir de casa.
		const FVector Dir = FVector::ForwardVector.RotateAngleAxis(Random.FRandRange(0.f, 360.f), FVector::UpVector);
		FVector Candidate = GetActorLocation() + Dir * Distance;
		if (FVector::Dist2D(Candidate, HomeLocation) > RadiusMax)
		{
			Candidate = HomeLocation + (Candidate - HomeLocation).GetSafeNormal2D() * Random.FRandRange(RadiusMin * 0.5f, RadiusMax);
		}
		Origin = Candidate;
		Distance = 0.f;
	}
	FNavLocation Goal;
	bool bFound = false;
	if (Distance <= 0.f)
	{
		bFound = NavSys->ProjectPointToNavigation(Origin, Goal, FVector(250.f, 250.f, 400.f));
	}
	if (!bFound)
	{
		// Longe de casa (empurrado, investigou) ou ponto fora da navmesh: volta para perto de casa.
		bFound = NavSys->GetRandomReachablePointInRadius(HomeLocation, FMath::Max(RadiusMax, 300.f), Goal);
	}
	if (!bFound)
	{
		return false;
	}
	ApplyMovementStyle(true, WanderSpeed * Random.FRandRange(0.9f, 1.1f));
	const EPathFollowingRequestResult::Type Result = AI->MoveToLocation(Goal.Location, 60.f, true, true, false, false);
	if (Result == EPathFollowingRequestResult::Failed)
	{
		return false;
	}
	CalmActivity = EJRCalmActivity::Walk;
	CalmActivityEnd = Now + 30.0; // trava de segurança (preso em algo)
	LogLife(TEXT("vagando"));
	return true;
}

bool AJREnemyCharacter::StartFollow(AAIController* AI, double Now)
{
	AJREnemyCharacter* Best = nullptr;
	double BestDistSq = FMath::Square(static_cast<double>(HerdSearchRadius));
	const FVector Me = GetActorLocation();
	for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
	{
		AJREnemyCharacter* Other = *It;
		if (!Other || Other == this || Other->IsDead() || !Other->IsCalm() || Other->FollowLeader.Get() == this
			|| Other->IsGrabbingVehicle())
		{
			continue;
		}
		const double DistSq = FVector::DistSquared(Me, Other->GetActorLocation());
		if (DistSq < BestDistSq && DistSq > FMath::Square(250.0))
		{
			BestDistSq = DistSq;
			Best = Other;
		}
	}
	if (!Best)
	{
		return false;
	}
	ApplyMovementStyle(true, WanderSpeed * Random.FRandRange(1.f, 1.15f));
	const EPathFollowingRequestResult::Type Result = AI->MoveToActor(Best, Random.FRandRange(180.f, 380.f), true, true, false);
	if (Result == EPathFollowingRequestResult::Failed)
	{
		return false;
	}
	FollowLeader = Best;
	CalmActivity = EJRCalmActivity::Follow;
	CalmActivityEnd = Now + Random.FRandRange(8.f, 16.f);
	LogLife(TEXT("seguindo a manada"));
	return true;
}

bool AJREnemyCharacter::FindCalmSpot(bool& bOutFeed, FVector& OutPoint) const
{
	TArray<FOverlapResult> Overlaps;
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRZombieCalmSpot), false, this);
	const FVector Me = GetActorLocation();
	GetWorld()->OverlapMultiByObjectType(Overlaps, Me, FQuat::Identity, Objects, FCollisionShape::MakeSphere(CalmSpotSearchRadius), Query);

	double BestDist = TNumericLimits<double>::Max();
	bool bFound = false;
	for (const FOverlapResult& Overlap : Overlaps)
	{
		UPrimitiveComponent* Comp = Overlap.GetComponent();
		AActor* HitActor = Overlap.GetActor();
		if (!Comp || !HitActor || HitActor == this)
		{
			continue;
		}
		bool bFeedy = false;
		FVector Point = FVector::ZeroVector;
		if (const AJREnemyCharacter* Other = Cast<AJREnemyCharacter>(HitActor))
		{
			if (!Other->IsDead())
			{
				continue;
			}
			bFeedy = true; // corpo de outro zumbi
			Point = Comp->Bounds.Origin;
		}
		else
		{
			// Só malhas estáticas de verdade (paredes, destroços, barricadas). Sem pawns, folhagem e itens pequenos.
			const UStaticMeshComponent* MeshComp = Cast<UStaticMeshComponent>(Comp);
			if (!MeshComp || HitActor->IsA<APawn>() || Comp->IsA<UInstancedStaticMeshComponent>() || Comp->Bounds.BoxExtent.Z < 45.0)
			{
				continue;
			}
			if (Comp->GetClosestPointOnCollision(Me, Point) < 0.f)
			{
				Point = Comp->Bounds.GetBox().GetClosestPointTo(Me);
			}
			if (FMath::Abs(Point.Z - Me.Z) > 60.0)
			{
				continue; // chão embaixo ou teto: não é parede ao lado
			}
			const UStaticMesh* StaticMesh = MeshComp->GetStaticMesh();
			const FString MeshName = StaticMesh ? StaticMesh->GetName() : FString();
			bFeedy = HitActor->ActorHasTag(FeedTag) || Comp->ComponentHasTag(FeedTag) || MeshName.Contains(TEXT("Wreck"))
				|| MeshName.Contains(TEXT("Corpse")) || MeshName.Contains(TEXT("Body")) || MeshName.Contains(TEXT("Carcass"));
		}
		const double Dist = FVector::Dist2D(Me, Point);
		if (Dist < 20.0 || Dist > CalmSpotSearchRadius || Dist >= BestDist)
		{
			continue;
		}
		BestDist = Dist;
		bOutFeed = bFeedy;
		OutPoint = Point;
		bFound = true;
	}
	return bFound;
}

bool AJREnemyCharacter::PlayLifeMontage(UAnimMontage* Montage, float PlayRate)
{
	UAnimInstance* Anim = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (!Montage || !Anim || Anim->Montage_IsPlaying(nullptr))
	{
		return false;
	}
	return PlayAnimMontage(Montage, PlayRate) > 0.f;
}

void AJREnemyCharacter::PlayIdleVariation()
{
	if (!Archetype)
	{
		return;
	}
	const int32 Count = Archetype->IdleVariationMontages.Num();
	if (Count > 0)
	{
		if (Random.FRand() < 0.5f)
		{
			PlayLifeMontage(Archetype->IdleVariationMontages[Random.RandRange(0, Count - 1)], Random.FRandRange(0.85f, 1.1f));
		}
		return;
	}
	// Sem variações próprias: de vez em quando um "espasmo" (reação a golpe bem lenta).
	if (Archetype->HitReactMontage && Random.FRand() < Archetype->IdleTwitchChance)
	{
		PlayLifeMontage(Archetype->HitReactMontage, Random.FRandRange(0.45f, 0.65f));
	}
}

void AJREnemyCharacter::LogLife(const TCHAR* What) const
{
	if (bLogLife)
	{
		UE_LOG(LogJR, Log, TEXT("IA %s: %s"), *GetName(), What);
	}
}

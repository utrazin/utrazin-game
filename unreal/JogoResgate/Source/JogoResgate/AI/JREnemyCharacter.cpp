// Copyright utrazin. All Rights Reserved.

#include "AI/JREnemyCharacter.h"
#include "AI/JRAimPrediction.h"
#include "AI/JREnemyArchetype.h"
#include "AI/JREnemyBudgetSubsystem.h"
#include "AIController.h"
#include "Navigation/PathFollowingComponent.h"
#include "Combat/JRHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "JogoResgate.h"
#include "TimerManager.h"

AJREnemyCharacter::AJREnemyCharacter()
{
	PrimaryActorTick.bCanEverTick = false;
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
	HealthComponent = CreateDefaultSubobject<UJRHealthComponent>(TEXT("HealthComponent"));
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
	GetWorldTimerManager().ClearTimer(BrainTimer);
	GetWorldTimerManager().ClearTimer(BurstTimer);
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
	// O alvo é o pawn atual do jogador: veículo ou personagem (perseguição de ambos).
	APawn* PlayerPawn = UGameplayStatics::GetPlayerPawn(this, 0);
	Target = PlayerPawn;
	AAIController* AI = Cast<AAIController>(GetController());

	FJREnemyDecisionInput In;
	In.Current = CurrentState;
	In.TimeInState = static_cast<float>(GetWorld()->GetTimeSeconds() - StateEnterTime);
	if (PlayerPawn)
	{
		In.DistanceToTarget = static_cast<float>(FVector::Dist(GetActorLocation(), PlayerPawn->GetActorLocation()));
		// Traço de visão só quando o alvo está perto o bastante para importar (custo).
		const bool bWorthTracing = In.DistanceToTarget <= Archetype->LoseAggroRadius;
		In.bHasLineOfSight = bWorthTracing && AI && AI->LineOfSightTo(PlayerPawn);
	}

	FJREnemyDecisionParams P;
	P.AggroRadius = Archetype->AggroRadius;
	P.LoseAggroRadius = Archetype->LoseAggroRadius;
	P.AttackRange = Archetype->AttackRange;
	P.AlertDuration = Archetype->AlertDuration;
	P.bHasPatrol = bHasPatrol;

	const EJREnemyState Next = FJREnemyStateLogic::Decide(In, P);
	if (BrainDebugLogsLeft > 0 && PlayerPawn && In.DistanceToTarget < P.LoseAggroRadius)
	{
		--BrainDebugLogsLeft;
		UE_LOG(LogJR, Log, TEXT("IA %s: alvo=%s dist=%.0f visão=%d estado=%s -> %s"), *GetName(), *PlayerPawn->GetName(),
			In.DistanceToTarget, In.bHasLineOfSight ? 1 : 0, *UEnum::GetValueAsString(CurrentState), *UEnum::GetValueAsString(Next));
	}
	SetEnemyState(Next);

	if (!AI)
	{
		return;
	}
	switch (Next)
	{
	case EJREnemyState::Chase:
		if (PlayerPawn)
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
		if (PlayerPawn)
		{
			AI->SetFocus(PlayerPawn);
		}
		TryAttack();
		break;
	case EJREnemyState::Alert:
		AI->StopMovement();
		if (PlayerPawn)
		{
			AI->SetFocus(PlayerPawn);
		}
		break;
	default:
		AI->ClearFocus(EAIFocusPriority::Gameplay);
		break;
	}
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
		// Dano pontual: no veículo vira dano por zona (UJRVehicleDamageComponent).
		FHitResult Hit;
		Hit.ImpactPoint = TargetActor->GetActorLocation();
		Hit.Location = Hit.ImpactPoint;
		const FVector Dir = (TargetActor->GetActorLocation() - GetActorLocation()).GetSafeNormal();
		UGameplayStatics::ApplyPointDamage(TargetActor, Archetype->AttackDamage, Dir, Hit, GetController(), this, nullptr);
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
		if (GetWorld()->LineTraceSingleByChannel(Hit, Muzzle, End, ECC_Visibility, Query) && Hit.GetActor())
		{
			UGameplayStatics::ApplyPointDamage(Hit.GetActor(), Archetype->AttackDamage, Dir, Hit, GetController(), this, nullptr);
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
	GetWorldTimerManager().ClearTimer(BrainTimer);
	GetWorldTimerManager().ClearTimer(BurstTimer);
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
	UE_LOG(LogJR, Log, TEXT("IA %s morreu"), *GetName());
	OnEnemyDied.Broadcast(this);
}

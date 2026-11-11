// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "JRObjectiveSubsystem.generated.h"

class AJRCheckpoint;
class UJRLevelDefinition;

/** Estágios do fluxo de uma fase (GDD 4.1). */
UENUM(BlueprintType)
enum class EJRLevelStage : uint8
{
	NotStarted,
	Driving,
	OnFoot,
	FinalHorde,
	Rescue,
	Completed,
	Failed
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnStageChanged, EJRLevelStage, OldStage, EJRLevelStage, NewStage);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnCheckpointReached, AJRCheckpoint*, Checkpoint);

/**
 * Estado da fase atual. Widgets apenas observam os delegates (nunca guardam estado de fase).
 */
UCLASS()
class JOGORESGATE_API UJRObjectiveSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

	UFUNCTION(BlueprintCallable, Category = "Objective")
	void InitializeLevel(UJRLevelDefinition* Definition, EJRLevelStage StartStage);

	UFUNCTION(BlueprintCallable, Category = "Objective")
	void SetStage(EJRLevelStage NewStage);

	UFUNCTION(BlueprintPure, Category = "Objective")
	EJRLevelStage GetStage() const { return Stage; }

	UFUNCTION(BlueprintPure, Category = "Objective")
	UJRLevelDefinition* GetLevelDefinition() const { return LevelDefinition; }

	UFUNCTION(BlueprintPure, Category = "Objective")
	FName GetLevelId() const;

	/** Registra checkpoint, salva progresso e avança o estágio quando aplicável. */
	UFUNCTION(BlueprintCallable, Category = "Objective")
	void ReachCheckpoint(AJRCheckpoint* Checkpoint);

	UFUNCTION(BlueprintCallable, Category = "Objective")
	void CompleteLevel();

	UFUNCTION(BlueprintCallable, Category = "Objective")
	void FailLevel();

	UPROPERTY(BlueprintAssignable, Category = "Objective")
	FJROnStageChanged OnStageChanged;

	UPROPERTY(BlueprintAssignable, Category = "Objective")
	FJROnCheckpointReached OnCheckpointReached;

private:
	UPROPERTY()
	TObjectPtr<UJRLevelDefinition> LevelDefinition;

	EJRLevelStage Stage = EJRLevelStage::NotStarted;
};

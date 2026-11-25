// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Remap/JRRemapTypes.h"
#include "JRRunSubsystem.generated.h"

class AJRCharacter;

/**
 * [Remap F1] Estado de uma corrida na arena (REMAP 6.5, 6.6, 7.5). Vive no GameInstance para atravessar
 * a troca de mapa cidade -> arena -> cidade. Tudo daqui some no fim da corrida; o permanente é o UJREconomySubsystem.
 */
UCLASS()
class JOGORESGATE_API UJRRunSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	/** [A-087] Tela de título da cidade: aparece uma vez por sessão do jogo (não volta ao sair da arena). */
	bool bTitleShown = false;

	/** Começa uma corrida nova (zera cartas, energia, ganhos). */
	UFUNCTION(BlueprintCallable, Category = "Run")
	void StartRun(int32 InSectorLevel);

	/**
	 * Fim da corrida. Extraiu: créditos x multiplicador. Morreu: fica com DeathKeepCredits.
	 * Põe os créditos na carteira, salva e guarda o relatório para a cidade mostrar.
	 */
	UFUNCTION(BlueprintCallable, Category = "Run")
	void EndRun(bool bExtracted, float Multiplier);

	UFUNCTION(BlueprintPure, Category = "Run")
	bool IsRunActive() const { return bActive; }

	// ---------------- progresso da corrida (chamado pelo AJRArenaDirector)
	void SetWave(int32 InWave) { Wave = InWave; }
	void MarkWaveCleared(int32 InWave) { WavesCleared = FMath::Max(WavesCleared, InWave); }

	/** Abate: soma créditos e energia (já com as cartas). Retorna os créditos ganhos. */
	int64 RegisterKill(int32 EnemyCost, float EffectiveLevel);

	/** Energia extra (ex.: fim de onda). Pode subir de nível e guardar escolhas de carta. */
	void AddEnergy(float Amount);

	/** [Remap F2] Créditos extras da corrida (objetivo, baú). Entram no multiplicador e no contrato de morte. */
	void AddBonusCredits(int64 Amount);
	/** [Remap F2] Objetivo da arena cumprido (vai para o relatório). */
	void MarkObjectiveCompleted() { ++ObjectivesCompleted; }
	/** [Remap F2] O herói levou dano: o combo zera. */
	void NotifyHeroDamaged() { Combo = 0; }

	// ---------------- cartas
	/** Tem escolha guardada e nenhuma aberta. */
	bool WantsCardChoice() const { return PendingChoices > 0 && !bChoosing; }
	/** Sorteia 3 cartas diferentes e abre a escolha. */
	void BeginCardChoice();
	/** Escolhe a carta Index (0..2). Retorna a carta escolhida (Count se inválido). */
	EJRRunCard PickCard(int32 Index);

	bool IsChoosingCard() const { return bChoosing; }
	const TArray<EJRRunCard>& GetOfferedCards() const { return Offered; }
	int32 GetPendingChoices() const { return PendingChoices; }

	/** Aplica Bancada x cartas no herói (dano, cadência, velocidade, vida máxima, couraça). */
	void ApplyStatsToHero(AJRCharacter* Hero, bool bRefillHealth) const;

	// ---------------- leitura (HUD)
	int32 GetSectorLevel() const { return SectorLevel; }
	int32 GetWave() const { return Wave; }
	int32 GetWavesCleared() const { return WavesCleared; }
	int32 GetKills() const { return Kills; }
	int32 GetRunLevel() const { return RunLevel; }
	float GetEnergy() const { return Energy; }
	float GetEnergyNeeded() const { return FJRRemapRules::EnergyForLevel(RunLevel); }
	int64 GetRunCredits() const { return RunCredits; }
	int32 GetCombo() const { return Combo; }
	int32 GetMaxCombo() const { return MaxCombo; }
	int32 GetObjectivesCompleted() const { return ObjectivesCompleted; }
	int64 GetCreditsIfDie() const { return FMath::FloorToInt64(RunCredits * FJRRemapRules::DeathKeepCredits); }
	const FJRRunStats& GetStats() const { return Stats; }
	const TArray<EJRRunCard>& GetPickedCards() const { return Picked; }

	/** Relatório da última corrida (a cidade mostra uma vez e chama ConsumeReport). */
	bool HasReport() const { return bHasReport; }
	const FJRRunReport& GetReport() const { return Report; }
	void ConsumeReport() { bHasReport = false; }

private:
	bool bActive = false;
	int32 SectorLevel = 1;
	int32 Wave = 0;
	int32 WavesCleared = 0;
	int32 Kills = 0;
	int32 RunLevel = 1;
	float Energy = 0.f;
	int64 RunCredits = 0;
	int32 Combo = 0;
	int32 MaxCombo = 0;
	int32 ObjectivesCompleted = 0;
	FJRRunStats Stats;
	TArray<EJRRunCard> Picked;

	int32 PendingChoices = 0;
	bool bChoosing = false;
	TArray<EJRRunCard> Offered;
	FRandomStream Rng;

	bool bHasReport = false;
	FJRRunReport Report;
};

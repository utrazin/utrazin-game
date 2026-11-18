// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "JRInventoryComponent.generated.h"

/** Consumíveis guardados na bolsa do herói (usados pela roda de itens / tecla H). */
UENUM(BlueprintType)
enum class EJRConsumable : uint8
{
	Bandage,  // cura pequena
	Medkit,   // cura grande
	Fury      // carga de Fúria guardada
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FJROnInventoryChanged, EJRConsumable, Item, int32, NewCount);

/**
 * Bolsa pequena do herói (A-055): bandagens, kits médicos e cargas de Fúria, com limite de cada.
 * Só guarda números; quem cura/anima é o AJRCharacter. Sem Tick.
 */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRInventoryComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRInventoryComponent();

	/** Adiciona até o limite. Retorna quantos entraram (0 = bolsa cheia desse item). */
	UFUNCTION(BlueprintCallable, Category = "Inventory")
	int32 AddItem(EJRConsumable Item, int32 Count = 1);

	/** Gasta um. Retorna false se não tinha. */
	UFUNCTION(BlueprintCallable, Category = "Inventory")
	bool ConsumeItem(EJRConsumable Item);

	UFUNCTION(BlueprintPure, Category = "Inventory")
	int32 GetCount(EJRConsumable Item) const;

	UFUNCTION(BlueprintPure, Category = "Inventory")
	int32 GetMaxCount(EJRConsumable Item) const;

	UFUNCTION(BlueprintPure, Category = "Inventory")
	bool IsFull(EJRConsumable Item) const { return GetCount(Item) >= GetMaxCount(Item); }

	/** Vida curada por uma bandagem / um kit (0 para Fúria). */
	UFUNCTION(BlueprintPure, Category = "Inventory")
	float GetHealAmount(EJRConsumable Item) const;

	/** Segundos de Fúria de uma carga guardada. */
	UFUNCTION(BlueprintPure, Category = "Inventory")
	float GetFurySeconds() const { return FurySeconds; }

	UPROPERTY(BlueprintAssignable, Category = "Inventory")
	FJROnInventoryChanged OnInventoryChanged;

protected:
	UPROPERTY(EditDefaultsOnly, Category = "Inventory|Bandage", meta = (ClampMin = "0"))
	int32 MaxBandages = 5;

	UPROPERTY(EditDefaultsOnly, Category = "Inventory|Bandage", meta = (ClampMin = "0"))
	float BandageHeal = 25.f;

	UPROPERTY(EditDefaultsOnly, Category = "Inventory|Medkit", meta = (ClampMin = "0"))
	int32 MaxMedkits = 3;

	UPROPERTY(EditDefaultsOnly, Category = "Inventory|Medkit", meta = (ClampMin = "0"))
	float MedkitHeal = 60.f;

	UPROPERTY(EditDefaultsOnly, Category = "Inventory|Fury", meta = (ClampMin = "0"))
	int32 MaxFuryCharges = 2;

	UPROPERTY(EditDefaultsOnly, Category = "Inventory|Fury", meta = (ClampMin = "1", Units = "s"))
	float FurySeconds = 10.f;

	/** Começa a fase com isto na bolsa (teste/ajuste). */
	UPROPERTY(EditDefaultsOnly, Category = "Inventory", meta = (ClampMin = "0"))
	int32 StartBandages = 0;

	UPROPERTY(EditDefaultsOnly, Category = "Inventory", meta = (ClampMin = "0"))
	int32 StartMedkits = 0;

	virtual void BeginPlay() override;

private:
	int32* CountPtr(EJRConsumable Item);

	UPROPERTY(VisibleInstanceOnly, Category = "Inventory")
	int32 Bandages = 0;

	UPROPERTY(VisibleInstanceOnly, Category = "Inventory")
	int32 Medkits = 0;

	UPROPERTY(VisibleInstanceOnly, Category = "Inventory")
	int32 FuryCharges = 0;
};

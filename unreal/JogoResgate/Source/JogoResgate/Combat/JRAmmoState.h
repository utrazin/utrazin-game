// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "JRAmmoState.generated.h"

/** Estado de munição de uma arma. Lógica pura (JR.Combat.Ammo.*). */
USTRUCT(BlueprintType)
struct JOGORESGATE_API FJRAmmoState
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ammo")
	int32 MagazineSize = 12;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ammo")
	int32 Magazine = 12;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ammo")
	int32 Reserve = 48;

	void Initialize(int32 InMagazineSize, int32 InReserve)
	{
		MagazineSize = FMath::Max(1, InMagazineSize);
		Magazine = MagazineSize;
		Reserve = FMath::Max(0, InReserve);
	}

	bool CanFire() const { return Magazine > 0; }

	/** Consome um tiro. Retorna false se o pente estiver vazio. */
	bool ConsumeShot()
	{
		if (Magazine <= 0)
		{
			return false;
		}
		--Magazine;
		return true;
	}

	bool CanReload() const { return Magazine < MagazineSize && Reserve > 0; }

	/** Move munição da reserva para o pente. Retorna quantas balas foram carregadas. */
	int32 Reload()
	{
		const int32 Needed = MagazineSize - Magazine;
		const int32 Loaded = FMath::Clamp(Needed, 0, Reserve);
		Magazine += Loaded;
		Reserve -= Loaded;
		return Loaded;
	}

	void AddReserve(int32 Amount) { Reserve = FMath::Max(0, Reserve + Amount); }

	bool IsCompletelyEmpty() const { return Magazine == 0 && Reserve == 0; }
};

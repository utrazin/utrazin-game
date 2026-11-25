// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Remap/JRShopkeeper.h"
#include "JRTreeShrine.generated.h"

class UPointLightComponent;

/**
 * [A-098] Santuário da Árvore-Mãe (praça noroeste da Villa Star): E abre a árvore de melhorias permanentes
 * (FJRSkillTree, paga com cristais da arena) na mesma janela das lojas. Não tem corpo: a árvore é a malha
 * SM_MRC_ArvoreMae posta pelo dress_city_v6.py; aqui fica só a área do E e uma luz que pulsa (mais forte quando
 * dá para comprar algum nó).
 */
UCLASS()
class JOGORESGATE_API AJRTreeShrine : public AJRShopkeeper
{
	GENERATED_BODY()

public:
	AJRTreeShrine();
	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;
	void HideBody();

	UPROPERTY(VisibleAnywhere, Category = "Shrine")
	TObjectPtr<UPointLightComponent> Glow;

	UPROPERTY(EditAnywhere, Category = "Shrine")
	float GlowCandelas = 40.f;

private:
	float CheckAccum = 0.f;
	bool bCanBuy = false;
};

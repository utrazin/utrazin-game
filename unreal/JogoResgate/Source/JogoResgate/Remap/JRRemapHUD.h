// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UI/JRHUD.h"
#include "JRRemapHUD.generated.h"

class AJRShopkeeper;
class UFont;

/**
 * [Remap F1] HUD da cidade e da arena: por cima da HUD de sempre desenha a carteira, o painel da corrida
 * (onda, energia, créditos e "se morrer fica com"), a nave de extração, as 3 cartas, a loja dos vendedores
 * e o relatório da corrida. Cinza de propósito (F1 testa o loop; a arte da HUD vem no F5).
 * Teclas: 1/2/3/4 escolhem; setas + Enter (ou controle: direcional + A) também; Q/Backspace/B fecham a loja.
 */
UCLASS()
class JOGORESGATE_API AJRRemapHUD : public AJRHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

	void OpenShop(AJRShopkeeper* Shopkeeper);
	void CloseShop();
	bool IsShopOpen() const { return Shop.IsValid(); }

	/** Console: JRCreditos 5000 (teste do protótipo). */
	UFUNCTION(Exec)
	void JRCreditos(int32 Amount);

	/** Console: JRArena 2 (começa uma corrida no nível 2 sem passar pelo portão). */
	UFUNCTION(Exec)
	void JRArena(int32 Level);

protected:
	virtual void BeginPlay() override;

private:
	struct FShopEntry
	{
		FString Label;
		FString Detail;
		int64 Price = 0;
		bool bAvailable = true;   // não comprado/liberado
		TFunction<bool()> Buy;    // retorna true se deu certo
	};

	void BuildShopEntries(TArray<FShopEntry>& Out) const;
	void DrawShop();
	void DrawWallet();
	void DrawRunPanel();
	void DrawShipMarker();
	void DrawCards();
	void DrawReport();

	/** Tecla 1..N, setas e confirmar. Retorna o índice escolhido ou INDEX_NONE. */
	int32 PollChoice(int32 NumOptions, int32& InOutSelected);
	bool Pressed(const FKey& Key) const;
	bool PressedClose() const;

	void SetPawnInput(bool bEnable);

	void Box(float X, float Y, float W, float H, const FLinearColor& Color);
	void Text(const FString& Str, float X, float Y, const FLinearColor& Color, bool bBig = false, float Scale = 1.f);
	FVector2D Measure(const FString& Str, bool bBig = false, float Scale = 1.f);
	static FString Num(int64 Value);

	float U = 1.f; // escala (1 = 1080p)

	TWeakObjectPtr<AJRShopkeeper> Shop;
	FString ShopGreeting;
	FString ShopFeedback;
	FLinearColor ShopFeedbackColor = FLinearColor::White;
	double ShopFeedbackUntil = 0.0;
	double ShopOpenedAt = 0.0;
	int32 ShopSelected = 0;

	int32 CardSelected = 1;
	bool bReportOpen = false;
	double ReportOpenedAt = 0.0;
};

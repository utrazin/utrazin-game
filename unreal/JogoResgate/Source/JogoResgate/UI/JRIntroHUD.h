// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UI/JRHUD.h"
#include "JRIntroHUD.generated.h"

class AJRIntroDirector;
class UFont;
class UFontFace;
class UTexture2D;
struct FJRIntroOverlay;

/**
 * HUD do jogo + tela de start e abertura (A-074). É o AJRHUD de sempre; enquanto o AJRIntroDirector roda,
 * esconde o HUD do jogo e desenha por cima: título e menu (Jogar / Ver abertura / Sair), faixas de cinema,
 * legendas, aviso "segure para pular", tela preta e clarão branco. Mesmas fontes e pílulas do HUD v2.
 * O AJRGameMode usa esta classe como HUD (o setup_intro.py também põe no BP_GameMode_L01).
 */
UCLASS()
class JOGORESGATE_API AJRIntroHUD : public AJRHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

	/** Índice do item do menu embaixo do ponto da tela (INDEX_NONE se nenhum). Usa o último quadro desenhado. */
	int32 HitTestMenu(const FVector2D& ScreenPos) const;

	/** Console (teste): "JRAbertura" apaga o IntroSeen do save e recomeça a fase (a abertura volta a rodar inteira). */
	UFUNCTION(Exec)
	void JRAbertura();

private:
	void DrawIntroOverlay(const FJRIntroOverlay& Ov);
	void DrawStartMenu(const FJRIntroOverlay& Ov, float Ui);
	void IntroRect(float X, float Y, float W, float H, const FLinearColor& Color);
	void IntroPill(bool bTeal, float X, float Y, float W, float H, const FLinearColor& Color);
	/** Texto com sombra. AlignX: 0 = esquerda, 0.5 = centro, 1 = direita. */
	void IntroText(const FString& Text, float X, float Y, float PixelSize, const FLinearColor& Color, bool bBold, float AlignX);
	FVector2D IntroMeasure(const FString& Text, float PixelSize, bool bBold);
	UFont* IntroFont(bool bBold, float PixelSize, float& OutScale);
	UTexture2D* IntroTex(const TCHAR* Name);

	TWeakObjectPtr<AJRIntroDirector> CachedDirector;
	bool bSearchedDirector = false;
	TArray<FBox2D> MenuRects;

	UPROPERTY(Transient)
	TMap<int32, TObjectPtr<UFont>> IntroFonts;

	UPROPERTY(Transient)
	TObjectPtr<UFontFace> IntroFaceBold;

	UPROPERTY(Transient)
	TObjectPtr<UFontFace> IntroFaceSemiBold;

	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<UTexture2D>> IntroTextures;

	bool bSearchedIntroFonts = false;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UI/JRHUD.h"
#include "Remap/JRRemapTypes.h"
#include "JRRemapHUD.generated.h"

class AJRShopkeeper;
class AJRExtractionShip;
class AJREnemyCharacter;
class UJRRunSubsystem;
class UJREconomySubsystem;

/**
 * [Remap F1 / A-083] HUD da cidade e da arena, no mesmo estilo v2 da HUD do herói ("argila alienígena":
 * painéis azul-marinho com aro lilás, pílulas, fonte Fredoka, ícones de massinha T_HUD2_R_*).
 * Por cima da HUD de sempre desenha: carteira (cidade), painel da corrida, onda, barra de energia, nave de
 * extração, escolha de 3 cartas, loja com balão de fala do vendedor e relatório da corrida.
 * Game feel: números que sobem contando, "+N" saindo de cada abate, moedas voando para o painel, barra de
 * energia que brilha, cartas entrando deslizando, compra com flash e "sem dinheiro" com tremida vermelha,
 * relatório linha a linha. Tudo em tempo real (nas cartas o jogo fica com dilatação 0,0001).
 * Teclas: 1/2/3/4 escolhem; setas + Enter (ou controle: direcional + A); Q/Backspace/B fecham a loja.
 */
UCLASS()
class JOGORESGATE_API AJRRemapHUD : public AJRHUD
{
	GENERATED_BODY()

public:
	/** [A-098] Faixa no meio da tela para atores da cidade (bairro liberado, portão fechado). */
	void ShowCityBanner(const FString& Title, const FString& Sub, const FString& Icon, float Duration = 2.6f) { ShowBanner(Title, Sub, Icon, Duration); }

	virtual void DrawHUD() override;

	void OpenShop(AJRShopkeeper* Shopkeeper);
	void CloseShop();
	bool IsShopOpen() const { return ShopKeeper.IsValid(); }

	/** Console: JRCreditos 5000 (teste do protótipo). */
	UFUNCTION(Exec)
	void JRCreditos(int32 Amount);

	/** [A-098] Console: JRCristais 50 (moeda da Árvore-Mãe). */
	UFUNCTION(Exec)
	void JRCristais(int32 Amount);

	/** [A-098] Console: JRRecorde 12 (recorde de ondas: libera arena e bairros; os postos liberados abrem na hora). */
	UFUNCTION(Exec)
	void JRRecorde(int32 Waves);

	/** Console: JRArena 2 (começa uma corrida no nível 2 sem passar pelo portão). */
	UFUNCTION(Exec)
	void JRArena(int32 InLevel);

protected:
	virtual void BeginPlay() override;

	// Ganchos da AJRHUD (A-083)
	virtual bool UseLevelMinimapImage() const override { return false; }
	virtual void CollectRadarBlips(TArray<FJRHudBlip>& OutBlips) const override;
	virtual bool IsHudModalOpen() const override;
	virtual FString MarkerIconFor(const AActor* Target) const override;

	/** Distância (m) em que o nome do vendedor aparece em cima dele. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Remap", meta = (Units = "m"))
	float NpcNameRange = 14.f;

	/** Letras por segundo do balão de fala da loja. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Remap", meta = (ClampMin = "5"))
	float TypewriterSpeed = 48.f;

private:
	struct FShopEntry
	{
		FString Label;
		FString Detail;
		FString Icon;             // T_HUD2_<Icon>
		int64 Price = 0;
		bool bAvailable = true;   // não comprado/liberado
		bool bOwned = false;      // já comprado (mostra "COMPRADO")
		bool bCrystals = false;   // [A-098] preço em cristais (Árvore-Mãe), não em créditos
		FString DenyLine;         // [A-098] fala quando não dá (vazio = a padrão)
		TFunction<bool()> Buy;    // retorna true se deu certo
	};

	/** "+N", "-N", "NÍVEL 4!" subindo e sumindo (preso a um ponto do mundo ou da tela). */
	struct FFloater
	{
		FString Label;
		FString Icon;
		FLinearColor Tint = FLinearColor::White;
		FVector WorldPos = FVector::ZeroVector;
		FVector2D ScreenPos = FVector2D::ZeroVector;
		bool bInWorld = false;
		double Born = 0.0;
		float Life = 1.1f;
		float SizePx = 30.f;
	};

	/** Moedinha voando de um ponto da tela até o painel (créditos ganhos/gastos). */
	struct FFlyCoin
	{
		FVector2D From = FVector2D::ZeroVector;
		FVector2D To = FVector2D::ZeroVector;
		double Born = 0.0;
		float Dur = 0.6f;
	};

	// ---------------- partes
	void BuildShopEntries(TArray<FShopEntry>& Out) const;
	void DrawShop();
	void DrawShopBubble(AJRShopkeeper* Keeper);
	void DrawWallet();
	void DrawRunPanel();
	void DrawWaveAndEnergy(const UJRRunSubsystem* Run, const class AJRArenaDirector* Director);
	void DrawObjectiveProgress(const class AJRArenaDirector* Director);
	void DrawShipMarker();
	void DrawCards();
	void DrawCardFace(EJRRunCard Card, float CX, float CY, float CardW, float CardH, float Alpha, bool bSelected, int32 KeyIndex);
	void DrawReport();
	void DrawNpcNames();
	/** [A-086] Nome do item no chão quando o herói chega perto (lê o que caiu). */
	void DrawPickupLabels();
	void DrawFloaters();
	void DrawCenterBanner();

	/** Lê a corrida e dispara os efeitos (abate, energia, nível, onda, nave). */
	void WatchRun();

	// ---------------- peças do estilo
	/** Textura em 9 fatias (cantos de 80 px de 256). */
	void NineSlice(UTexture2D* Tex, float X, float Y, float W, float H, float Corner, const FLinearColor& Tint);
	/** Painel v2: miolo azul-marinho, aro tingido (lilás, raridade...), brilho opcional e luzinhas ciano. */
	void PanelBox(float X, float Y, float W, float H, const FLinearColor& RimTint, float Alpha, float GlowAlpha = 0.f,
		const FLinearColor& GlowTint = FLinearColor::White);
	/** Ícone T_HUD2_<Name> centrado (Angle em graus). */
	void IconAt(const FString& Name, float CX, float CY, float SizePx, float Alpha = 1.f, float AngleDeg = 0.f);
	/** Ícone dentro do selo redondo (T_HUD2_Badge). */
	void IconBadge(const FString& Name, float CX, float CY, float SizePx, float Alpha = 1.f, const FLinearColor& RingTint = FLinearColor::White);
	/** Texto centrado na vertical em CY. Retorna a largura. */
	float TextMid(const FString& Str, float X, float CY, float Px, const FLinearColor& Color, int32 Align = 0, bool bBold = true);
	/** Barra arredondada (contorno tinta, trilho azul, preenchimento com brilho). */
	void BarAt(float X, float Y, float W, float H, float Frac, const FLinearColor& FillColor, float Alpha, float Flash = 0.f);
	/** [A-087] Textura em 9 fatias: os cantos (CapU/CapV = fração da textura) não esticam; Cap = tamanho do canto na tela. */
	void DrawNine(UTexture2D* Tex, float X, float Y, float W, float H, float CapU, float CapV, float CapX, float CapY, const FLinearColor& Color);
	/** Pílula com ícone + texto centrada em CX. Retorna a largura. */
	float IconPill(const FString& PillTex, const FString& Icon, const FString& Str, float CX, float Y, float PillH, float Px,
		const FLinearColor& LabelColor, float Alpha = 1.f, float Scale = 1.f);

	// ---------------- efeitos
	void SpawnFloater(const FString& Label, const FString& Icon, const FLinearColor& Tint, const FVector2D& ScreenPos, float SizePx, float Life = 1.1f);
	void SpawnWorldFloater(const FString& Label, const FString& Icon, const FLinearColor& Tint, const FVector& WorldPos, float SizePx);
	void SpawnCoins(const FVector2D& From, const FVector2D& To, int32 Count);
	void ShowBanner(const FString& Title, const FString& Sub, const FString& Icon, float Duration = 1.8f);
	/** Número mostrado que corre até o valor real (contando). */
	int64 TweenNumber(FName Key, int64 Target, float Speed = 6.f);
	void TweenSnap(FName Key, int64 Value);
	/** 1 logo depois que o número mudou, cai até 0 em Dur segundos. */
	float PopOf(FName Key, float Dur = 0.35f) const;
	float Since(double When) const { return static_cast<float>(RNow - When); }

	/** Tecla 1..N, setas e confirmar. Retorna o índice escolhido ou INDEX_NONE. */
	int32 PollChoice(int32 NumOptions, int32& InOutSelected);
	bool Pressed(const FKey& Key) const;
	bool PressedClose() const;

	void SetPawnInput(bool bEnable);
	/** [A-087] Tela de título (fundo pintado + botões). true = está na tela (o resto da HUD não desenha). */
	bool DrawTitleScreen();
	void PlayUi(const TCHAR* SoundId, float Volume = 1.f, float Pitch = 1.f);

	static FString Fmt(int64 Value);
	static FString CardIcon(EJRRunCard Card);
	static FString ShopIconFor(const AJRShopkeeper* Keeper);
	static FLinearColor RarityColor(int32 Rarity);

	// ---------------- relógio real e escala
	double RNow = 0.0;
	double RLast = -1.0;
	float RDelta = 0.f;
	float RU = 1.f; // altura / 1080
	float RK = 1.f; // RU x HudScale (painéis)

	// ---------------- loja
	TWeakObjectPtr<AJRShopkeeper> ShopKeeper;
	FString ShopLine;
	double ShopLineAt = 0.0;
	double ShopOpenedAt = 0.0;
	int32 ShopSelected = 0;
	int32 ShopFlashRow = -1;
	double ShopFlashAt = -100.0;
	int32 ShopDenyRow = -1;
	double ShopDenyAt = -100.0;
	FVector2D WalletCoinPos = FVector2D::ZeroVector;

	// ---------------- cartas
	int32 CardSelected = 1;
	bool bCardsWereOpen = false;
	double CardsOpenedAt = -100.0;
	double CardMovedAt = -100.0;
	FVector2D LastCardMouse = FVector2D(-1.f, -1.f); // [A-087] só troca a carta quando o mouse mexe
	EJRRunCard CardPicked = EJRRunCard::Count;
	double CardPickedAt = -100.0;
	FVector2D CardPickedPos = FVector2D::ZeroVector;
	float CardScales[3] = { 1.f, 1.f, 1.f };

	// ---------------- relatório
	bool bReportOpen = false;
	double ReportOpenedAt = 0.0;
	int32 ReportRowsShown = 0;
	bool bWalletHeld = false; // segura a carteira até a última linha do relatório
	// [A-087] tela de título
	bool bTitleActive = false;
	double TitleOpenedAt = -100.0;
	double TitleClosingAt = -100.0;
	double TitlePressedAt = -100.0;
	int32 TitleSelected = 0;
	int32 TitlePressedIndex = INDEX_NONE;
	FVector2D TitleLastMouse = FVector2D(-1.f, -1.f);
	int64 WalletHeldValue = 0;

	// ---------------- corrida
	int32 SeenKills = -1;
	int64 SeenRunCredits = -1;
	int32 SeenRunLevel = -1;
	float SeenEnergyFrac = -1.f;
	float EnergyShown = 0.f;
	double EnergyGainAt = -100.0;
	double LevelUpAt = -100.0;
	int32 SeenWave = -1;
	double WaveStartAt = -100.0;
	TWeakObjectPtr<AJRExtractionShip> SeenShip;
	float ShipTotalSeconds = 30.f;
	FString LastObjectiveLine;
	double ObjectiveChangedAt = -100.0;
	float ObjectiveShown = 0.f;
	FVector2D RunCoinPos = FVector2D::ZeroVector;
	TSet<TWeakObjectPtr<AJREnemyCharacter>> CountedDead;

	// ---------------- efeitos
	TArray<FFloater> Floaters;
	TArray<FFlyCoin> FlyCoins;
	TMap<FName, double> TweenShown;
	TMap<FName, int64> TweenGoal;
	TMap<FName, double> TweenPopAt;
	FString BannerTitle;
	FString BannerSub;
	FString BannerIcon;
	double BannerAt = -100.0;
	float BannerDur = 1.8f;
};

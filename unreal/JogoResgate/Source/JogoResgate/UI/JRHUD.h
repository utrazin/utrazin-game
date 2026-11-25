// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "JRHUD.generated.h"

class AJRHordeDirector;
class UJRWeaponComponent;
class UTexture2D;
class UFont;
class UFontFace;
struct FJRWheelEntryInfo;

/** [A-083] Pino extra no minimapa/radar (nave de extração, vendedores da cidade...). */
struct FJRHudBlip
{
	FVector World = FVector::ZeroVector;
	/** Textura T_HUD2_<Icon> no meio do pino (vazio = losango). */
	FString Icon;
	FLinearColor Tint = FLinearColor::White;
};

/**
 * HUD do jogo (GDD 10): vida, munição, mira, objetivo, carro, interação e avisos.
 * Desenhado em C++ (Canvas) para funcionar sem montar widgets no editor.
 * Estilo v2 (A-059): "argila alienígena" das referências do usuário (painéis azul-marinho com moldura
 * de pedra lilás, luzes ciano e cristais roxos), texturas em /Game/UI/HUD/V2 e fonte Fredoka.
 * Os números das peças (onde fica cada barra, texto e furo) vêm de UI/JRHudArt.h (gerado).
 */
UCLASS()
class JOGORESGATE_API AJRHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

	/** Mapa grande na tela (tecla M). */
	UFUNCTION(BlueprintCallable, Category = "HUD")
	void ToggleBigMap() { bBigMap = !bBigMap; }

	/** Aviso curto no centro-baixo da tela ("Pegou: pistola", "+12 células"...). */
	UFUNCTION(BlueprintCallable, Category = "HUD")
	void ShowToast(const FString& Text, FLinearColor Color = FLinearColor::White);

	/** Dica do que fazer agora (aparece embaixo do objetivo). */
	UFUNCTION(BlueprintCallable, Category = "HUD")
	void SetObjectiveHint(const FString& Hint) { ObjectiveHint = Hint; }

	/**
	 * [A-064] Tarefa atual (texto principal do OBJETIVO; marcador, minimapa e distância apontam para Target).
	 * Se a tarefa de agora ainda não terminou, a nova entra numa fila e aparece quando ela terminar.
	 */
	void SetCurrentTask(const FString& Text, AActor* Target, float ReachRadius);

	/** Atalho para qualquer código mostrar aviso no HUD do jogador 1. */
	static void Toast(const UObject* WorldContext, const FString& Text, FLinearColor Color = FLinearColor::White);

protected:
	/** Tamanho dos painéis (1 = pixel da referência em 1080p). Diminua se achar o HUD grande. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD", meta = (ClampMin = "0.5", ClampMax = "1.5"))
	float HudScale = 0.86f;

	/** Margem das bordas da tela em pixels a 1080p. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD", meta = (ClampMin = "0"))
	float SafeMargin = 22.f;

	/** Cor de destaque (ciano das luzes dos painéis). */
	UPROPERTY(EditDefaultsOnly, Category = "HUD")
	FLinearColor AccentColor = FLinearColor(FColor(64, 232, 240));

	UPROPERTY(EditDefaultsOnly, Category = "HUD")
	FLinearColor HealthColor = FLinearColor(FColor(255, 96, 84));

	/** Amarelo do objetivo (losango no mapa e no mundo). */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Minimap")
	FLinearColor ObjectiveColor = FLinearColor(FColor(255, 196, 40));

	/** Área mostrada no minimapa (largura em metros) a pé e no carro. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Minimap", meta = (Units = "m"))
	float MinimapSpanOnFoot = 260.f;

	UPROPERTY(EditDefaultsOnly, Category = "HUD|Minimap", meta = (Units = "m"))
	float MinimapSpanDriving = 520.f;

	/** Véu azul por cima da imagem do mapa. 0 = imagem pura ([A-067] a imagem v4 já vem no tom do HUD). */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Minimap", meta = (ClampMin = "0", ClampMax = "1"))
	float MinimapTint = 0.f;

	/** [A-067] Alcance dos pontos ciano de itens e baús no minimapa. [A-083] Pinos flutuando no mundo em cima de itens foram removidos. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Marcadores", meta = (Units = "m", ClampMin = "0"))
	float NearbyMarkerRange = 35.f;

	/** [A-067] Não usado desde a A-083 (sem pinos de item no mundo). */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Marcadores", meta = (ClampMin = "0"))
	int32 NearbyMarkerMax = 6;

	/** Duração do flash vermelho ao levar dano. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD", meta = (Units = "s"))
	float DamageFlashDuration = 0.45f;

	/** Altura da roda de itens como fração da altura da tela. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|ItemWheel", meta = (ClampMin = "0.4", ClampMax = "0.95"))
	float WheelScreenFraction = 0.80f;

	/** Velocidade (km/h) que enche o arco do velocímetro. */
	UPROPERTY(EditDefaultsOnly, Category = "HUD|Vehicle", meta = (ClampMin = "10"))
	float SpeedometerMaxKmh = 160.f;

	// ------------------------------------------------------------ ganchos para subclasses (A-083)
	/** false = o minimapa vira radar sem imagem (cidade/arena do Remap: a imagem do L01 não vale lá) e a tecla M não abre o mapa. */
	virtual bool UseLevelMinimapImage() const { return true; }
	/** Pinos extras no minimapa/radar. Chamado a cada quadro com a lista vazia. */
	virtual void CollectRadarBlips(TArray<FJRHudBlip>& OutBlips) const {}
	/** Tela cheia aberta (loja, cartas, relatório): esconde aviso "E", marcador no mundo, minimapa e objetivo. */
	virtual bool IsHudModalOpen() const { return false; }

	// ------------------------------------------------------------ peças básicas (v2), protegidas para a AJRRemapHUD (A-083)
	/** /Game/UI/HUD/V2/T_HUD2_<Name> (nulo se o setup_hud_v2.py ainda não importou). */
	UTexture2D* HudTex(const FString& Name);
	/** Desenha uma textura (ou parte dela, por UV) num retângulo da tela. */
	void DrawTex(UTexture2D* Tex, float X, float Y, float W, float H, const FLinearColor& Color,
		const FVector2D& UV0 = FVector2D(0.f, 0.f), const FVector2D& UV1 = FVector2D(1.f, 1.f), bool bAdditive = false);
	/** Pílula de 3 fatias (pontas fixas, meio esticado) na altura H. */
	void DrawPill(const FString& TexName, float X, float Y, float W, float H, const FLinearColor& Color);
	/** Largura que a pílula precisa para um texto (pontas + texto + folga). */
	float PillWidthFor(const FString& TexName, float H, float TextW) const;
	/** Fonte Fredoka no tamanho pedido (pixels na tela); cai na fonte da Unreal se não existir. */
	UFont* HudFont(bool bBold, float PixelSize);
	/** Mede um texto na fonte da HUD. */
	FVector2D MeasureText(const FString& Text, bool bBold, float PixelSize);
	/**
	 * Texto da HUD: preenchido com contorno escuro e sombra embaixo (como nas referências).
	 * Align: 0 = esquerda, 1 = centro, 2 = direita (em X). Y = topo da linha. Retorna a largura.
	 */
	float DrawHudText(const FString& Text, float X, float Y, float PixelSize, const FLinearColor& Color, int32 Align = 0,
		bool bBold = true, float Outline = -1.f);
	/** Igual a DrawHudText, mas encolhe para caber em MaxW. Retorna o tamanho usado. */
	float DrawHudTextFit(const FString& Text, float X, float Y, float PixelSize, float MaxW, const FLinearColor& Color, int32 Align = 0,
		bool bBold = true);
	/** Quebra em linhas que cabem em MaxW. */
	TArray<FString> WrapText(const FString& Text, bool bBold, float PixelSize, float MaxW);
	/** Tecla desenhada (E, M, Q, TAB...). Retorna a largura. */
	float DrawKeyCap(const FString& Key, float X, float Y, float H);
	/** Aproxima um valor mostrado do valor real (barras suaves). */
	float Smooth(FName Key, float Target, float Speed, float DeltaTime);

	// ------------------------------------------------------------ partes do HUD
	void DrawHeroHud(class AJRCharacter* Hero);
	void DrawWeaponCard(class AJRCharacter* Hero, float DeltaTime);
	void DrawVehicleHud(class AJRVehiclePawn* Vehicle);
	void DrawToasts();
	void DrawInteractionPrompt(class AJRCharacter* Hero);
	void DrawShotgunCrosshair(bool bAiming);
	/** Barra de segmentos do painel a pé (VIDA / FÚRIA): segmentos acesos pela porcentagem, rastro branco do dano. */
	void DrawSegmentBar(const FString& FillTex, const FVector2D& Origin, float K, int32 Which, float Pct, float TrailPct,
		const FLinearColor& Tint);
	/** Barra contínua do painel do carro (recorte suave na ponta). */
	void DrawContinuousBar(const FString& FillTex, const FVector2D& Origin, float K, int32 Which, float Pct, float TrailPct,
		const FLinearColor& Tint);
	/** Mantido para a luneta (A-058): texto simples centralizável. Scale 1 = 18 px a 1080p. */
	void DrawLabel(const FString& Text, float X, float Y, float Scale, const FLinearColor& Color, bool bCenterX = false);
	void DrawRounded(float X, float Y, float W, float H, float R, const FLinearColor& Color);
	void DrawCrosshair(bool bAiming, bool bReloading);
	/** [Sensação de combate, A-057] "X" de acerto (branco) e de abate (vermelho, maior) na mira. */
	void DrawHitMarker(const UJRWeaponComponent* Weapon);
	/** [A-057] Arcos vermelhos em volta da mira apontando de onde veio o golpe. */
	void DrawDamageIndicators(class AJRCharacter* Hero);
	/**
	 * [A-058] Luneta do rifle: escurece fora do círculo, retícula fina com marcas, zoom e fôlego.
	 * Gancho isolado para o restyle do HUD (o agente de UI pode trocar o desenho sem mexer no resto).
	 * ScopeAlpha 0..1 = transição de entrada.
	 */
	void DrawSniperScope(class AJRCharacter* Hero, float ScopeAlpha);
	void DrawObjective(EJRLevelStage Stage, bool bDriving);
	void DrawBigBanner(const FString& Title, const FString& Sub, const FLinearColor& Color);
	FString ObjectiveFor(EJRLevelStage Stage) const;
	AJRHordeDirector* FindHorde();
	void DrawMinimap(const APawn* Pawn, bool bDriving, const AActor* Target);
	void DrawBigMapView(const APawn* Pawn, const AActor* Target);
	void DrawWorldMarker(const AActor* Target, const APawn* Pawn);
	AActor* FindObjectiveTarget(EJRLevelStage Stage);
	UTexture2D* GetMinimapTexture();
	/** [A-067] Imagem do mapa grande (com nomes); sem ela, a mesma do minimapa. */
	UTexture2D* GetBigMapTexture();
	FVector2D WorldToUV(const FVector& L) const;
	void DrawDiamond(const FVector2D& C, float R, const FLinearColor& Color);
	void DrawArrow(const FVector2D& C, float Yaw, float R, const FLinearColor& Color);
	/** Mapa recortado numa elipse (leque de triângulos com UV): o Canvas não tem máscara. */
	void DrawMapEllipse(UTexture2D* Tex, const FVector2D& Center, float RX, float RY, const FVector2D& UVCenter, const FVector2D& UVHalf,
		const FLinearColor& Color);

	// ------------------------------------------------------------ roda de itens e cura (A-055 / A-059)
	/** Roda de itens (Tab): abas ARMAS / CONSUMÍVEIS, 8 setores, centro com nome, munição e atributos. */
	void DrawItemWheel(class AJRCharacter* Hero);
	void DrawWheelCenter(const FJRWheelEntryInfo& Info, const FVector2D& Mid, float K, float Alpha);
	/** Bandagens e kits acima do painel de vida. */
	void DrawHealItems(class AJRCharacter* Hero, float X, float Y, float K);
	/** Anel de progresso no centro da tela enquanto se cura. */
	void DrawHealProgress(class AJRCharacter* Hero);
	/** Textura quadrada girada (graus, sentido horário) em torno do centro. */
	void DrawRotatedTex(UTexture2D* Tex, const FVector2D& Center, float Size, float AngleDeg, const FLinearColor& Color);
	/** Pedaço de anel sem textura (graus a partir do topo, sentido horário). */
	void DrawArc(const FVector2D& Center, float RIn, float ROut, float Deg0, float Deg1, const FLinearColor& Color, int32 Segments = 24);

private:
	TWeakObjectPtr<AActor> CachedTransition;
	TWeakObjectPtr<AActor> CachedRescue;
	TWeakObjectPtr<UTexture2D> CachedMinimap;
	TWeakObjectPtr<UTexture2D> CachedBigMap; // [A-067]
	bool bSearchedTargets = false;
	bool bSearchedMinimap = false;
	bool bBigMap = false;
	FVector2D MapMin = FVector2D(-100000.f, -100000.f);
	FVector2D MapMax = FVector2D(100000.f, 100000.f);

	TWeakObjectPtr<AJRHordeDirector> CachedHorde;
	bool bSearchedHorde = false;
	float LastHealth = -1.f;
	float LastIntegrity = -1.f;
	double DamageFlashStart = -100.0;
	double LastHudRealTime = -1.0;
	float S = 1.f; // escala da tela (base 1080p)
	float CrosshairBloomNow = 0.f; // abertura da mira pelos tiros (0..1, A-057)

	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<UTexture2D>> HudTextures;

	/** Fontes criadas em tempo de execução a partir das FontFace importadas (uma por tamanho). */
	UPROPERTY(Transient)
	TMap<int32, TObjectPtr<UFont>> FontCache;

	UPROPERTY(Transient)
	TObjectPtr<UFontFace> FaceBold;

	UPROPERTY(Transient)
	TObjectPtr<UFontFace> FaceSemiBold;

	bool bSearchedFonts = false;

	/** Valores mostrados (barras suaves e rastro de dano). */
	TMap<FName, float> SmoothValues;
	/** Quando cada rastro de dano começou a cair. */
	TMap<FName, double> TrailHold;

	struct FToast
	{
		FString Text;
		FLinearColor Color;
		double Start = 0.0;
	};
	TArray<FToast> Toasts;
	FString ObjectiveHint;
	EJRLevelStage LastStage = EJRLevelStage::NotStarted;

	// ------------------------------------------------------------ tarefa atual (A-064)
	struct FJRTask
	{
		FString Text;
		TWeakObjectPtr<AActor> Target;
		float Reach = 1500.f;
		bool bHasTarget = false;
	};
	FJRTask CurrentTask;
	TArray<FJRTask> PendingTasks;
	/** Item pego, baú aberto, portão aberto, sobrevivente solta, carro com o jogador ou jogador perto do alvo. */
	bool IsTaskDone(const FJRTask& Task, const APawn* Pawn) const;
	/** Tira as tarefas terminadas e puxa a próxima da fila. */
	void UpdateTasks(const APawn* Pawn, EJRLevelStage Stage);
	/** Alvo do marcador: a tarefa atual ou, sem ela, o objetivo geral do estágio. */
	AActor* GuideTarget(EJRLevelStage Stage);

protected:
	// ------------------------------------------------------------ marcadores (A-067)
	/** Textura do ícone para um alvo ("Icon_Stick", "Icon_CarKey", "Stat_Ammo"...). Vazio = sem ícone. */
	virtual FString MarkerIconFor(const AActor* Target) const; // [A-083] virtual: a AJRRemapHUD dá ícone aos vendedores
	/** Pino: halo, ponta para baixo em Tip, disco escuro, anel colorido e o ícone no meio. */
	void DrawMarkerPin(const FVector2D& Tip, float Size, const FString& Icon, const FLinearColor& RingColor, float Alpha, bool bPulse);
	/** Triângulo liso (Canvas), para a ponta do pino e a seta da borda. */
	void DrawSolidTri(const FVector2D& A, const FVector2D& B, const FVector2D& C, const FLinearColor& Color);
	/** Itens não pegos e baús fechados até RadiusCm, do mais perto ao mais longe (sem Skip). */
	void CollectNearbyInteractables(const APawn* Pawn, float RadiusCm, int32 MaxCount, const AActor* Skip, TArray<AActor*>& Out) const;
	/** Altura (mundo) onde o pino aparece em cima do alvo. */
	static FVector MarkerAnchor(const AActor* Target);
};

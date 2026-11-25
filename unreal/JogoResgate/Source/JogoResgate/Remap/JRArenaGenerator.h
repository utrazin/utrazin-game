// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Remap/JRArenaLayout.h"
#include "JRArenaGenerator.generated.h"

class AJRArenaChest;
class UBoxComponent;
class UInstancedStaticMeshComponent;
class UPointLightComponent;
class UPrimitiveComponent;
class UStaticMesh;

/** Papel de uma peça do kit do tema. */
UENUM()
enum class EJRArenaPieceUse : uint8
{
	Wall,   // muro/limite em volta (fica fora da área jogável)
	High,   // cobertura alta (bloqueia passagem e visão)
	Low,    // cobertura baixa (bloqueia passagem, dá para atirar por cima)
	Decor   // enfeite sem colisão nas células livres
};

/** Uma peça do kit (malha que já existe no Content). */
USTRUCT()
struct FJRArenaKitPiece
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Kit")
	TSoftObjectPtr<UStaticMesh> Mesh;

	UPROPERTY(EditAnywhere, Category = "Kit")
	EJRArenaPieceUse Use = EJRArenaPieceUse::Low;

	UPROPERTY(EditAnywhere, Category = "Kit", meta = (ClampMin = "0"))
	float Weight = 1.f;

	/** Peça pequena (barril, caixa, pneus): vão 2 a 4 juntas na mesma célula. */
	UPROPERTY(EditAnywhere, Category = "Kit")
	bool bCluster = false;

	/**
	 * [A-089] Onde a peça pode aparecer (lista separada por vírgula): Geral (cobertura comum), Natureza (pilares no
	 * meio da arena), Patio, FerroVelho, Acampamento (conjuntos temáticos na borda).
	 */
	UPROPERTY(EditAnywhere, Category = "Kit")
	FString Groups = TEXT("Geral");
};

/**
 * [Remap F2] Gerador da arena procedural (REMAP 6.2). No BeginPlay (ou quando o diretor pede) monta a planta
 * (FJRArenaLayout) a partir de uma semente e troca cada célula por peças do kit do tema "Posto abandonado".
 * Visual: uma malha instanciada por peça, sem colisão. Colisão: caixas simples invisíveis do tamanho de cada peça
 * (entram na navmesh dinâmica). Muro em volta: caixas altas na borda + peças grandes do lado de fora.
 * O mapa só precisa de chão, luz, NavMeshBoundsVolume grande, RecastNavMesh, PlayerStart no mesmo lugar deste ator
 * e o AJRArenaDirector (tools/unreal/build_remap_f2.py).
 * Semente para teste: console "jr.Arena.Seed 1234" (0 = sorteia) e "jr.Arena.Shape 0..4" (-1 = sorteia), depois RestartLevel.
 */
UCLASS()
class JOGORESGATE_API AJRArenaGenerator : public AActor
{
	GENERATED_BODY()

public:
	AJRArenaGenerator();

	static AJRArenaGenerator* FindInWorld(const UObject* WorldContext);

	/** Monta a arena uma vez (seguro chamar várias vezes; o diretor chama antes de ler os pontos). */
	void EnsureBuilt();

	bool IsBuilt() const { return bBuilt; }
	const FJRArenaLayout& GetLayout() const { return Layout; }
	const TArray<FVector>& GetSpawnPoints() const { return SpawnPoints; }
	const TArray<FVector>& GetExtractionPoints() const { return ExtractionPoints; }
	/** Pontos livres e espalhados para objetivos (ninhos, elite marcado). */
	const TArray<FVector>& GetObjectivePoints() const { return ObjectivePoints; }
	/** Centro do 3 x 3 livre: sempre na posição deste ator. */
	FVector GetPlayerStartPoint() const { return GetActorLocation(); }
	int32 GetSeed() const { return Layout.Seed; }
	FString GetShapeName() const { return FJRArenaLayout::ShapeName(Layout.Shape); }
	FString GetThemeName() const { return ThemeName; }
	int32 GetArenaMeters() const { return FMath::RoundToInt(Layout.Size * CellSize / 100.f); }
	FVector CellToWorld(const FIntPoint& Cell) const;

protected:
	virtual void BeginPlay() override;

	UPROPERTY(EditAnywhere, Category = "Arena")
	FString ThemeName = TEXT("Posto abandonado");

	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "cm", ClampMin = "400"))
	float CellSize = 800.f;

	/** Nível do setor quando se dá Play direto na arena (sem corrida ativa). */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 DefaultSectorLevel = 1;

	/** Sementes tentadas até a conferência automática passar. */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (ClampMin = "1"))
	int32 MaxAttempts = 12;

	/** Altura da colisão invisível do muro em volta. */
	UPROPERTY(EditAnywhere, Category = "Arena", meta = (Units = "cm"))
	float WallHeight = 600.f;

	UPROPERTY(EditAnywhere, Category = "Arena|Kit")
	TArray<FJRArenaKitPiece> Kit;

	UPROPERTY(EditAnywhere, Category = "Arena|Kit")
	TSoftObjectPtr<UStaticMesh> CanopyMesh;

	UPROPERTY(EditAnywhere, Category = "Arena|Kit")
	TSoftObjectPtr<UStaticMesh> PumpMesh;

	UPROPERTY(EditAnywhere, Category = "Arena|Kit")
	TSoftObjectPtr<UStaticMesh> StoreMesh;

	UPROPERTY(EditAnywhere, Category = "Arena|Kit")
	TSoftObjectPtr<UStaticMesh> LampMesh;

	/** Cubo da engine: plano B quando a peça do kit não cabe ou não carregou. */
	UPROPERTY(EditAnywhere, Category = "Arena|Kit")
	TObjectPtr<UStaticMesh> FallbackCube;

	UPROPERTY(EditAnywhere, Category = "Arena|Kit", meta = (ClampMin = "0", ClampMax = "1"))
	float DecorChance = 0.15f;

	/** Um poste com luz a cada N células do muro (no máximo MaxLamps). */
	UPROPERTY(EditAnywhere, Category = "Arena|Kit", meta = (ClampMin = "1"))
	int32 LampEvery = 7;

	UPROPERTY(EditAnywhere, Category = "Arena|Kit", meta = (ClampMin = "0"))
	int32 MaxLamps = 10;

	UPROPERTY(EditAnywhere, Category = "Arena")
	TSubclassOf<AJRArenaChest> ChestClass;

	/** [A-086] Muralha da vila em volta da arena (colisão da própria malha). */
	UPROPERTY(EditAnywhere, Category = "Arena|Muralha")
	TSoftObjectPtr<UStaticMesh> WallMesh;

	UPROPERTY(EditAnywhere, Category = "Arena|Muralha")
	TSoftObjectPtr<UStaticMesh> TowerMesh;

	UPROPERTY(EditAnywhere, Category = "Arena|Muralha")
	TSoftObjectPtr<UStaticMesh> GateMesh;

	/** Espessura do muro (o modelo tem 7,5 m; afinado aqui até o conserto da arte). */
	UPROPERTY(EditAnywhere, Category = "Arena|Muralha", meta = (Units = "cm"))
	float WallThickness = 260.f;

	/** Altura do muro: mais alto que um pulo de cima de qualquer cobertura. */
	UPROPERTY(EditAnywhere, Category = "Arena|Muralha", meta = (Units = "cm"))
	float WallVisualHeight = 720.f;

	/** Cenário de fundo, fora da muralha (sem colisão). */
	UPROPERTY(EditAnywhere, Category = "Arena|Muralha")
	TArray<TSoftObjectPtr<UStaticMesh>> BackdropMeshes;

private:
	bool BuildOnce(int32 BaseSeed, int32 SectorLevel, int32 ForcedShape, FString& OutProblem);
	void ClearArena();
	void LoadKit();
	/**
	 * Sorteia uma malha do papel pedido. ClusterMode: -1 qualquer, 0 só inteiras, 1 só pequenas. Group: só peças desse
	 * grupo (se nenhuma servir, qualquer uma do papel). -1 = nenhuma.
	 */
	int32 PickMesh(EJRArenaPieceUse PieceUse, int32 ClusterMode, const TCHAR* Group = nullptr) const;
	int32 PickMeshStrict(EJRArenaPieceUse PieceUse, int32 ClusterMode, const TCHAR* Group) const;
	/** 2 a 4 peças pequenas em volta de Center (barris, gerador, pedras). Retorna quantas entraram. */
	int32 PlaceCluster(const FVector& Center, float Spread, int32 Count, const TCHAR* Group);
	/** Yaw (graus) olhando para dentro da arena, para um conjunto com o muro na direção OutDir. */
	static float YawFacingIn(const FIntPoint& OutDir);
	UInstancedStaticMeshComponent* GetMeshComponent(UStaticMesh* InMesh, bool bCollide = false);
	/** Malha com origem no centro de baixo, escala livre por eixo (muralha). */
	void PlaceScaled(UStaticMesh* InMesh, const FVector& BottomCenter, float Yaw, const FVector& Scale, bool bCollide);
	void BuildBackdrop();
	void AddBlocker(const FVector& Center, const FVector& HalfExtent, float Yaw);
	/** Coloca a malha cabendo em Fit (comprido, largura, altura), centrada em Center, apoiada no chão. */
	bool PlacePiece(UStaticMesh* InMesh, const FVector& Center, float Yaw, const FVector& Fit, float MaxScale,
		float MinCollisionHeight, bool bCollision, bool bTrackOverlap);
	/** Bloco de cubo com tamanho exato (plano B). */
	void PlaceBlock(const FVector& Center, const FVector& BlockSize, float Yaw, bool bTrackOverlap);
	void AddLight(const FVector& Location, const FLinearColor& Color, float Intensity, float Radius);
	void TrackArea(const FVector& Center, const FVector& HalfExtent, float Yaw);

	void BuildCover();
	/** [A-089] Conjuntos temáticos da planta (posto, pátio, ferro-velho, acampamento). */
	void BuildAssemblies();
	void BuildLandmark(const FJRArenaAssembly& Asm);
	void BuildBorder();
	void BuildDecor();
	void SpawnChests();
	bool CheckOverlaps(FString& OutProblem) const;

	FJRArenaLayout Layout;
	FRandomStream DressRng;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> LoadedMeshes;
	TArray<EJRArenaPieceUse> LoadedUse;
	TArray<float> LoadedWeight;
	TArray<bool> LoadedCluster;
	TArray<FString> LoadedGroups;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> LoadedSpecial; // 0 cobertura, 1 bomba, 2 loja, 3 poste, 4 muro, 5 torre, 6 portão

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> LoadedBackdrop;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> MeshComponents;
	TArray<bool> MeshComponentCollides;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UPrimitiveComponent>> Blockers;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UPointLightComponent>> ArenaLights;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> SpawnedActors;

	TArray<FBox2D> PieceAreas;
	TArray<FVector> SpawnPoints;
	TArray<FVector> ExtractionPoints;
	TArray<FVector> ObjectivePoints;
	int32 PlacedPieces = 0;
	bool bBuilt = false;
	bool bBuilding = false;
};

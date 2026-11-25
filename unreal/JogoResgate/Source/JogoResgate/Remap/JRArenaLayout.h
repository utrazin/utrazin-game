// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * [Remap F2] Planta da arena procedural em grade (docs/design/REMAP_CIDADE_ARENA.md, seção 6.2).
 * Lógica pura (sem mundo, sem UObject): dá para testar com Automation Tests e repetir a mesma semente.
 *
 * Camadas:
 * 1. Molde (círculo, cruz, U, dois pátios, rua com becos) numa grade de células de 8 m, com uma borda de fora.
 * 2. Bloqueio: livre, cobertura baixa, cobertura alta. Regras: tudo alcançável a partir do centro (flood fill),
 *    nenhuma área fechada, nenhuma linha de visão reta maior que MaxSightRun células e pelo menos 3 saídas do centro.
 * 3. Pontos: surgimento (longe do centro, de preferência colados no muro), nave (um por quadrante),
 *    objetivos (ninhos, elite) e baús.
 * [A-089] Regras de posicionamento por item (docs/design/ARENA_PROCEDURAL_REGRAS.md):
 *    - conjuntos temáticos (posto, pátio, ferro-velho, acampamento) sempre na borda, de costas para a muralha,
 *      separados por ângulo (vistos do centro) e com a frente livre;
 *    - zona central (raio 2) sempre aberta; cobertura alta comum só perto do muro; no meio, cobertura baixa e
 *      pilares naturais (quebra de visão);
 *    - baú nas vagas dos conjuntos (protegido, 2 acessos) ou colado no muro; ninho sem nada escalável em volta;
 *    - no mínimo 60% de área livre.
 * A troca de cada célula por peças do kit é do AJRArenaGenerator.
 */

/** O que tem em cada célula. Out = fora da arena (muro/limite). */
enum class EJRArenaCell : uint8
{
	Out,
	Free,
	Low,   // cobertura baixa: dá para atirar por cima, não dá para passar
	High   // cobertura alta: bloqueia passagem e visão
};

/**
 * [A-089] Conjuntos temáticos ("assemblies"): grupos de peças com lógica, sempre encostados na muralha.
 * Cada um tem um molde pequeno (largura ao longo do muro x profundidade para dentro) com células sólidas,
 * baixas e de pátio, e uma vaga de baú protegida com pelo menos 2 acessos.
 */
enum class EJRArenaAssemblyKind : uint8
{
	Posto,        // loja (de costas para o muro) + cobertura com bombas
	Patio,        // pátio de contêineres em L
	FerroVelho,   // carros batidos/ônibus com barris
	Acampamento,  // barricadas e gerador
	Count
};

/** Etiqueta de cada célula (por que ela está bloqueada). */
enum class EJRArenaCellTag : uint8
{
	None,
	Cover,     // grupo de cobertura comum
	Pillar,    // quebra de linha de visão isolada no meio (vira formação natural: rocha/cristal)
	Assembly   // parte de um conjunto temático
};

struct JOGORESGATE_API FJRArenaAssembly
{
	EJRArenaAssemblyKind Kind = EJRArenaAssemblyKind::Posto;
	/** Direção (uma das 4) que aponta para a muralha. */
	FIntPoint OutDir = FIntPoint(0, -1);
	/** Primeira célula (u = 0, v = 0) do molde, colada no muro. */
	FIntPoint Base = FIntPoint(0, 0);
	/** Direção ao longo do muro (u). */
	FIntPoint AlongDir = FIntPoint(1, 0);
	int32 Width = 0;
	int32 Depth = 0;
	TArray<FIntPoint> Cells;   // todas
	TArray<FIntPoint> Solid;   // altas (bloqueiam visão)
	TArray<FIntPoint> LowCells;
	TArray<FIntPoint> Yard;    // livres (dá para andar)
	FIntPoint ChestSlot = FIntPoint(-1, -1);

	/** Célula do molde: u ao longo do muro, v para dentro (0 = colada no muro). */
	FIntPoint Local(int32 U, int32 V) const { return Base + AlongDir * U - OutDir * V; }
};

/** Moldes da seção 6.2. */
enum class EJRArenaShape : uint8
{
	Circle,
	Cross,
	U,
	TwoYards,
	Street,
	Count
};

struct JOGORESGATE_API FJRArenaLayout
{
	static constexpr int32 MinSize = 10;       // 80 m
	static constexpr int32 MaxSize = 20;       // 160 m
	static constexpr int32 MaxSightRun = 8;    // 64 m de visão reta, no máximo
	static constexpr int32 MinSpawnCells = 6;
	static constexpr int32 MinExtractionCells = 2;
	static constexpr int32 MinObjectiveCells = 3;

	int32 Seed = 0;
	/** Células por lado da área jogável (N). */
	int32 Size = 0;
	/** N + 2 (uma volta de células "Out" em torno). */
	int32 Grid = 0;
	EJRArenaShape Shape = EJRArenaShape::Circle;
	/** Célula onde o herói começa (centro 3 x 3 sempre livre). */
	FIntPoint Start = FIntPoint(0, 0);

	TArray<EJRArenaCell> Cells;
	TArray<uint8> Reserved;

	/** [A-089] Conjuntos temáticos encostados na muralha (posto, pátio de contêineres, ferro-velho, acampamento). */
	TArray<FJRArenaAssembly> Assemblies;
	/** Distância (em células, 4 direções) até a célula de fora mais perto. 1 = colada no muro. */
	TArray<uint8> DistOut;
	TArray<uint8> CellTags;
	/** Índice em Assemblies (-1 = nenhum). */
	TArray<int8> AssemblyAt;

	/** Marco do tema "Posto abandonado": cobertura com bombas (2 x 2 livres) + loja (2 células altas). */
	bool bHasLandmark = false;
	TArray<FIntPoint> CanopyCells;
	TArray<FIntPoint> StoreCells;

	TArray<FIntPoint> SpawnCells;
	TArray<FIntPoint> ExtractionCells;
	TArray<FIntPoint> ObjectiveCells;
	TArray<FIntPoint> ChestCells;

	/** 10 células (80 m) no nível 1, +1 por nível, até 20 (160 m). */
	static int32 SizeForLevel(int32 SectorLevel);
	static FString ShapeName(EJRArenaShape InShape);
	static FString AssemblyName(EJRArenaAssemblyKind InKind);

	/** Raio (Chebyshev, em células) da zona central que fica sempre aberta. */
	static constexpr int32 CenterZoneRadius = 2;
	/** Cobertura alta comum só até esta distância do muro (no meio da arena, só baixa e pilares). */
	static constexpr int32 HighCoverMaxDistOut = 2;
	/** Mínimo de área livre (o resto é cobertura/conjuntos). */
	static constexpr float MinFreeRatio = 0.6f;

	/**
	 * Monta a planta com uma semente. ForcedShape < 0 sorteia o molde. bWithCover = false só põe o mínimo
	 * (quebra de linha de visão), usado como plano B. Retorna false com o motivo em OutProblem.
	 */
	bool Generate(int32 InSeed, int32 SectorLevel, int32 ForcedShape, bool bWithCover, FString& OutProblem);

	/** Tenta BaseSeed e depois sementes derivadas até dar certo (conferência automática). Último recurso: sem cobertura. */
	static bool GenerateWithRetries(int32 BaseSeed, int32 SectorLevel, int32 ForcedShape, int32 MaxAttempts,
		FJRArenaLayout& OutLayout, int32& OutAttempts, FString& OutLastProblem);

	bool IsValidCell(int32 X, int32 Y) const { return X >= 0 && Y >= 0 && X < Grid && Y < Grid; }
	EJRArenaCell Get(int32 X, int32 Y) const { return IsValidCell(X, Y) ? Cells[X * Grid + Y] : EJRArenaCell::Out; }
	EJRArenaCell Get(const FIntPoint& P) const { return Get(P.X, P.Y); }
	bool IsInside(int32 X, int32 Y) const { return Get(X, Y) != EJRArenaCell::Out; }
	bool IsReserved(int32 X, int32 Y) const { return IsValidCell(X, Y) && Reserved[X * Grid + Y] != 0; }
	void SetCell(int32 X, int32 Y, EJRArenaCell Value);
	void SetReserved(int32 X, int32 Y, bool bValue);
	EJRArenaCellTag GetTag(int32 X, int32 Y) const
	{
		return IsValidCell(X, Y) && CellTags.Num() == Grid * Grid ? static_cast<EJRArenaCellTag>(CellTags[X * Grid + Y]) : EJRArenaCellTag::None;
	}
	void SetTag(int32 X, int32 Y, EJRArenaCellTag Value);
	int32 GetAssemblyIndex(int32 X, int32 Y) const
	{
		return IsValidCell(X, Y) && AssemblyAt.Num() == Grid * Grid ? static_cast<int32>(AssemblyAt[X * Grid + Y]) : -1;
	}
	int32 GetDistOut(int32 X, int32 Y) const
	{
		return IsValidCell(X, Y) && DistOut.Num() == Grid * Grid ? static_cast<int32>(DistOut[X * Grid + Y]) : 0;
	}
	bool IsCenterZone(const FIntPoint& P) const
	{
		return FMath::Max(FMath::Abs(P.X - Start.X), FMath::Abs(P.Y - Start.Y)) <= CenterZoneRadius;
	}
	/** Vizinhos (4 direções) livres. */
	int32 CountFreeNeighbors4(const FIntPoint& P) const;
	/** Fração das células de dentro que estão livres. */
	float FreeRatio() const;

	/** Marca (1) as células livres alcançáveis a partir de Start andando nas 4 direções. */
	void FloodFromStart(TArray<uint8>& OutSeen) const;
	int32 CountUnreachableFree() const;
	/** Maior trecho reto (linha ou coluna) sem cobertura alta, em células. */
	int32 LongestSightRun() const;
	/** Primeiro trecho reto maior que MaxSightRun (vazio se nenhum). */
	bool FindLongSightRun(TArray<FIntPoint>& OutRun) const;
	/** Lados do centro 3 x 3 que têm saída livre (0 a 4). */
	int32 CountCenterExits() const;

	/** Conferência completa. Vazio = tudo certo; senão, o primeiro problema. */
	FString Validate() const;

	/** Desenho em texto para o log: . livre, b baixa, H alta, @ início, s surgimento, E nave, o objetivo, c baú. */
	FString ToAscii() const;

private:
	bool FixSightLines(const FRandomStream& Rng);
	void ComputeDistOut();
	/** Põe os conjuntos temáticos na borda (regras na seção A-089 do ASSUMPTIONS). */
	void PlaceAssemblies(const FRandomStream& Rng, float Radius);
	bool TryPlaceAssembly(EJRArenaAssemblyKind InKind, const FIntPoint& InBase, const FIntPoint& InOutDir, bool bMirror,
		float Radius);
};

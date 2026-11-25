// Copyright utrazin. All Rights Reserved.

#include "Remap/JRArenaLayout.h"

namespace JRArenaLayoutPrivate
{
	static const FIntPoint Dirs4[4] = { FIntPoint(1, 0), FIntPoint(-1, 0), FIntPoint(0, 1), FIntPoint(0, -1) };

	static int32 Chebyshev(const FIntPoint& A, const FIntPoint& B)
	{
		return FMath::Max(FMath::Abs(A.X - B.X), FMath::Abs(A.Y - B.Y));
	}

	static float Dist(const FIntPoint& A, const FIntPoint& B)
	{
		return FMath::Sqrt(static_cast<float>(FMath::Square(A.X - B.X) + FMath::Square(A.Y - B.Y)));
	}

	template <typename T>
	static void ShuffleWith(TArray<T>& Items, const FRandomStream& Rng)
	{
		for (int32 i = Items.Num() - 1; i > 0; --i)
		{
			const int32 j = Rng.RandRange(0, i);
			Items.Swap(i, j);
		}
	}
}

int32 FJRArenaLayout::SizeForLevel(int32 SectorLevel)
{
	return FMath::Clamp(MinSize + (FMath::Max(1, SectorLevel) - 1), MinSize, MaxSize);
}

FString FJRArenaLayout::ShapeName(EJRArenaShape InShape)
{
	switch (InShape)
	{
	case EJRArenaShape::Circle: return TEXT("Círculo");
	case EJRArenaShape::Cross: return TEXT("Cruz");
	case EJRArenaShape::U: return TEXT("U");
	case EJRArenaShape::TwoYards: return TEXT("Dois pátios");
	case EJRArenaShape::Street: return TEXT("Rua com becos");
	default: return TEXT("?");
	}
}

void FJRArenaLayout::SetCell(int32 X, int32 Y, EJRArenaCell Value)
{
	if (IsValidCell(X, Y))
	{
		Cells[X * Grid + Y] = Value;
	}
}

void FJRArenaLayout::SetReserved(int32 X, int32 Y, bool bValue)
{
	if (IsValidCell(X, Y))
	{
		Reserved[X * Grid + Y] = bValue ? 1 : 0;
	}
}

void FJRArenaLayout::FloodFromStart(TArray<uint8>& OutSeen) const
{
	OutSeen.Init(0, Grid * Grid);
	if (Get(Start) != EJRArenaCell::Free)
	{
		return;
	}
	TArray<FIntPoint> Stack;
	Stack.Add(Start);
	OutSeen[Start.X * Grid + Start.Y] = 1;
	while (Stack.Num() > 0)
	{
		const FIntPoint P = Stack.Pop();
		for (const FIntPoint& D : JRArenaLayoutPrivate::Dirs4)
		{
			const FIntPoint Q = P + D;
			if (Get(Q) == EJRArenaCell::Free && OutSeen[Q.X * Grid + Q.Y] == 0)
			{
				OutSeen[Q.X * Grid + Q.Y] = 1;
				Stack.Add(Q);
			}
		}
	}
}

int32 FJRArenaLayout::CountUnreachableFree() const
{
	TArray<uint8> Seen;
	FloodFromStart(Seen);
	int32 Count = 0;
	for (int32 i = 0; i < Cells.Num(); ++i)
	{
		if (Cells[i] == EJRArenaCell::Free && Seen[i] == 0)
		{
			++Count;
		}
	}
	return Count;
}

bool FJRArenaLayout::FindLongSightRun(TArray<FIntPoint>& OutRun) const
{
	TArray<FIntPoint> Run;
	for (int32 Axis = 0; Axis < 2; ++Axis)
	{
		for (int32 A = 0; A < Grid; ++A)
		{
			Run.Reset();
			for (int32 B = 0; B <= Grid; ++B)
			{
				const int32 X = Axis == 0 ? B : A;
				const int32 Y = Axis == 0 ? A : B;
				const EJRArenaCell C = B < Grid ? Get(X, Y) : EJRArenaCell::Out;
				if (C != EJRArenaCell::Out && C != EJRArenaCell::High)
				{
					Run.Add(FIntPoint(X, Y));
				}
				else
				{
					if (Run.Num() > MaxSightRun)
					{
						OutRun = Run;
						return true;
					}
					Run.Reset();
				}
			}
		}
	}
	OutRun.Reset();
	return false;
}

int32 FJRArenaLayout::LongestSightRun() const
{
	int32 Best = 0;
	for (int32 Axis = 0; Axis < 2; ++Axis)
	{
		for (int32 A = 0; A < Grid; ++A)
		{
			int32 Len = 0;
			for (int32 B = 0; B < Grid; ++B)
			{
				const EJRArenaCell C = Axis == 0 ? Get(B, A) : Get(A, B);
				Len = (C != EJRArenaCell::Out && C != EJRArenaCell::High) ? Len + 1 : 0;
				Best = FMath::Max(Best, Len);
			}
		}
	}
	return Best;
}

int32 FJRArenaLayout::CountCenterExits() const
{
	int32 Exits = 0;
	for (const FIntPoint& D : JRArenaLayoutPrivate::Dirs4)
	{
		bool bOpen = false;
		for (int32 K = -1; K <= 1; ++K)
		{
			const int32 X = Start.X + D.X * 2 + (D.X == 0 ? K : 0);
			const int32 Y = Start.Y + D.Y * 2 + (D.Y == 0 ? K : 0);
			bOpen |= Get(X, Y) == EJRArenaCell::Free;
		}
		Exits += bOpen ? 1 : 0;
	}
	return Exits;
}

bool FJRArenaLayout::FixSightLines(const FRandomStream& Rng)
{
	TArray<FIntPoint> Run;
	for (int32 Iter = 0; Iter < 200; ++Iter)
	{
		if (!FindLongSightRun(Run))
		{
			return true;
		}
		// Candidatos: dentro do trecho (sem as pontas), livres ou baixos, não reservados.
		// Nota menor = divide melhor o trecho e fica longe de outras coberturas altas (evita "muralhas").
		TArray<TPair<float, int32>> Scored;
		for (int32 i = 1; i < Run.Num() - 1; ++i)
		{
			const FIntPoint P = Run[i];
			const EJRArenaCell C = Get(P);
			if ((C != EJRArenaCell::Free && C != EJRArenaCell::Low) || IsReserved(P.X, P.Y))
			{
				continue;
			}
			int32 HighNear = 0;
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				for (int32 DY = -1; DY <= 1; ++DY)
				{
					if ((DX != 0 || DY != 0) && Get(P.X + DX, P.Y + DY) == EJRArenaCell::High)
					{
						++HighNear;
					}
				}
			}
			// [A-089] zona central: só em último caso (e vira pilar natural, nunca prédio)
			const float Score = static_cast<float>(FMath::Max(i, Run.Num() - 1 - i)) + 3.f * HighNear + Rng.FRand() * 2.f
				+ (IsCenterZone(P) ? 6.f : 0.f);
			Scored.Add(TPair<float, int32>(Score, i));
		}
		Scored.Sort([](const TPair<float, int32>& L, const TPair<float, int32>& R) { return L.Key < R.Key; });
		bool bFixed = false;
		for (const TPair<float, int32>& Cand : Scored)
		{
			const FIntPoint P = Run[Cand.Value];
			const EJRArenaCell Old = Get(P);
			SetCell(P.X, P.Y, EJRArenaCell::High);
			if (CountUnreachableFree() > 0)
			{
				SetCell(P.X, P.Y, Old);
				continue;
			}
			// [A-089] perto do muro é cobertura comum; no meio vira pilar natural (rocha/cristal), não prédio
			SetTag(P.X, P.Y, (GetDistOut(P.X, P.Y) <= 1 && !IsCenterZone(P)) ? EJRArenaCellTag::Cover : EJRArenaCellTag::Pillar);
			bFixed = true;
			break;
		}
		if (!bFixed)
		{
			return false;
		}
	}
	TArray<FIntPoint> Left;
	return !FindLongSightRun(Left);
}

bool FJRArenaLayout::Generate(int32 InSeed, int32 SectorLevel, int32 ForcedShape, bool bWithCover, FString& OutProblem)
{
	using namespace JRArenaLayoutPrivate;
	const FRandomStream Rng(InSeed);
	Seed = InSeed;
	Size = SizeForLevel(SectorLevel);
	Grid = Size + 2;
	Cells.Init(EJRArenaCell::Out, Grid * Grid);
	Reserved.Init(0, Grid * Grid);
	CellTags.Init(0, Grid * Grid);
	AssemblyAt.Init(-1, Grid * Grid);
	DistOut.Init(0, Grid * Grid);
	Assemblies.Reset();
	bHasLandmark = false;
	CanopyCells.Reset();
	StoreCells.Reset();
	SpawnCells.Reset();
	ExtractionCells.Reset();
	ObjectiveCells.Reset();
	ChestCells.Reset();
	OutProblem.Reset();

	const int32 N = Size;
	const int32 ShapeCount = static_cast<int32>(EJRArenaShape::Count);
	const int32 ShapeIndex = (ForcedShape >= 0 && ForcedShape < ShapeCount) ? ForcedShape : Rng.RandRange(0, ShapeCount - 1);
	Shape = static_cast<EJRArenaShape>(ShapeIndex);
	const float C = (N - 1) * 0.5f;

	auto SetIn = [this, N](int32 IX, int32 IY)
	{
		if (IX >= 0 && IY >= 0 && IX < N && IY < N)
		{
			SetCell(IX + 1, IY + 1, EJRArenaCell::Free);
		}
	};

	// ---------------- 1. molde
	switch (Shape)
	{
	case EJRArenaShape::Circle:
	{
		const float R = N * 0.5f;
		for (int32 X = 0; X < N; ++X)
		{
			for (int32 Y = 0; Y < N; ++Y)
			{
				if (FMath::Square(X - C) + FMath::Square(Y - C) <= R * R * 0.98f)
				{
					SetIn(X, Y);
				}
			}
		}
		break;
	}
	case EJRArenaShape::Cross:
	{
		const float W = N * 0.2f + 0.01f;
		for (int32 X = 0; X < N; ++X)
		{
			for (int32 Y = 0; Y < N; ++Y)
			{
				if (FMath::Abs(X - C) <= W || FMath::Abs(Y - C) <= W)
				{
					SetIn(X, Y);
				}
			}
		}
		break;
	}
	case EJRArenaShape::U:
	{
		const int32 X0 = N / 3;
		const int32 X1 = N - N / 3;
		const int32 Y0 = N / 2;
		const int32 Turns = Rng.RandRange(0, 3);
		for (int32 X = 0; X < N; ++X)
		{
			for (int32 Y = 0; Y < N; ++Y)
			{
				if (X >= X0 && X < X1 && Y >= Y0)
				{
					continue; // o vão do U
				}
				int32 RX = X;
				int32 RY = Y;
				for (int32 T = 0; T < Turns; ++T)
				{
					const int32 Tmp = RX;
					RX = N - 1 - RY;
					RY = Tmp;
				}
				SetIn(RX, RY);
			}
		}
		break;
	}
	case EJRArenaShape::TwoYards:
	{
		const int32 A = FMath::TruncToInt(N * 0.6f + 0.5f);
		const bool bMirror = Rng.RandRange(0, 1) == 1;
		for (int32 X = 0; X < N; ++X)
		{
			for (int32 Y = 0; Y < N; ++Y)
			{
				if ((X < A && Y < A) || (X >= N - A && Y >= N - A))
				{
					SetIn(bMirror ? N - 1 - X : X, Y);
				}
			}
		}
		break;
	}
	default: // Street
	{
		const bool bHorizontal = Rng.RandRange(0, 1) == 1;
		TArray<FIntPoint> Pts;
		for (int32 X = 0; X < N; ++X)
		{
			for (int32 Y = 0; Y < N; ++Y)
			{
				if (FMath::Abs(Y - C) <= 1.5f)
				{
					Pts.Add(FIntPoint(X, Y));
				}
			}
		}
		const int32 NumAlleys = 2 + N / 8;
		const int32 AlleyWidth = N < 14 ? 2 : 3;
		TArray<int32> AlleyX;
		AlleyX.Add(FMath::TruncToInt(C)); // um beco sempre passa pelo centro
		for (int32 Try = 0; Try < 50 && AlleyX.Num() < NumAlleys; ++Try)
		{
			const int32 X = Rng.RandRange(1, N - 3);
			bool bFar = true;
			for (const int32 Other : AlleyX)
			{
				bFar &= FMath::Abs(X - Other) >= 4;
			}
			if (bFar)
			{
				AlleyX.Add(X);
			}
		}
		const int32 UpStart = FMath::TruncToInt(C + 2.f);
		const int32 DownStart = FMath::TruncToInt(C - 2.f);
		for (int32 i = 0; i < AlleyX.Num(); ++i)
		{
			const int32 X = AlleyX[i];
			for (int32 Side = -1; Side <= 1; Side += 2)
			{
				if (i != 0 && Rng.FRand() >= 0.7f)
				{
					continue;
				}
				const int32 Len = i == 0 ? N : Rng.RandRange(N / 4, N / 2);
				for (int32 K = 0; K < Len; ++K)
				{
					const int32 Y = Side > 0 ? UpStart + K : DownStart - K;
					if (Y >= 0 && Y < N)
					{
						for (int32 WW = 0; WW < AlleyWidth; ++WW)
						{
							Pts.Add(FIntPoint(X + WW, Y));
						}
					}
				}
				if (i > 0)
				{
					// pátio pequeno no fim do beco
					const int32 YEnd = FMath::Clamp(Side > 0 ? UpStart + Len - 1 : DownStart - Len + 1, 1, N - 2);
					for (int32 DX = -1; DX <= 2; ++DX)
					{
						for (int32 DY = -1; DY <= 1; ++DY)
						{
							Pts.Add(FIntPoint(X + DX, YEnd + DY));
						}
					}
				}
			}
		}
		for (const FIntPoint& P : Pts)
		{
			if (bHorizontal)
			{
				SetIn(P.X, P.Y);
			}
			else
			{
				SetIn(P.Y, P.X);
			}
		}
		break;
	}
	}

	// ---------------- centro: célula mais perto do meio com 3 x 3 dentro e pelo menos 3 "braços"
	{
		bool bFound = false;
		float BestDist = TNumericLimits<float>::Max();
		for (int32 X = 1; X < Grid - 1; ++X)
		{
			for (int32 Y = 1; Y < Grid - 1; ++Y)
			{
				int32 Arms = 0;
				Arms += IsInside(X + 2, Y) ? 1 : 0;
				Arms += IsInside(X - 2, Y) ? 1 : 0;
				Arms += IsInside(X, Y + 2) ? 1 : 0;
				Arms += IsInside(X, Y - 2) ? 1 : 0;
				bool bBlock = Arms >= 3;
				for (int32 DX = -1; DX <= 1 && bBlock; ++DX)
				{
					for (int32 DY = -1; DY <= 1 && bBlock; ++DY)
					{
						bBlock = IsInside(X + DX, Y + DY);
					}
				}
				if (!bBlock)
				{
					continue;
				}
				const float D = FMath::Square(X - 1 - C) + FMath::Square(Y - 1 - C);
				if (D < BestDist)
				{
					BestDist = D;
					Start = FIntPoint(X, Y);
					bFound = true;
				}
			}
		}
		if (!bFound)
		{
			OutProblem = TEXT("sem centro 3x3");
			return false;
		}
	}
	for (int32 DX = -1; DX <= 1; ++DX)
	{
		for (int32 DY = -1; DY <= 1; ++DY)
		{
			SetReserved(Start.X + DX, Start.Y + DY, true);
		}
	}
	for (const FIntPoint& D : Dirs4)
	{
		if (IsInside(Start.X + D.X * 2, Start.Y + D.Y * 2))
		{
			SetReserved(Start.X + D.X * 2, Start.Y + D.Y * 2, true); // saídas do centro
		}
	}
	const float R = N * 0.5f;

	// ---------------- [A-089] conjuntos temáticos na borda (posto, pátio, ferro-velho, acampamento)
	ComputeDistOut();
	if (bWithCover)
	{
		PlaceAssemblies(Rng, R);
	}

	TArray<FIntPoint> InsideList;
	for (int32 X = 0; X < Grid; ++X)
	{
		for (int32 Y = 0; Y < Grid; ++Y)
		{
			if (IsInside(X, Y))
			{
				InsideList.Add(FIntPoint(X, Y));
			}
		}
	}
	if (InsideList.Num() == 0)
	{
		OutProblem = TEXT("molde vazio");
		return false;
	}

	// ---------------- 2. bloqueio: primeiro quebra as linhas de visão longas (grade vazia), depois os grupos
	FixSightLines(Rng);
	if (bWithCover)
	{
		static const FIntPoint PatSingle[] = { FIntPoint(0, 0) };
		static const FIntPoint PatLine2[] = { FIntPoint(0, 0), FIntPoint(1, 0) };
		static const FIntPoint PatLine3[] = { FIntPoint(0, 0), FIntPoint(1, 0), FIntPoint(2, 0) };
		static const FIntPoint PatL[] = { FIntPoint(0, 0), FIntPoint(1, 0), FIntPoint(0, 1) };
		const int32 Target = FMath::TruncToInt(InsideList.Num() * (0.12f + Rng.FRand() * 0.06f));
		int32 Blocked = 0;
		for (int32 Try = 0; Try < 600 && Blocked < Target; ++Try)
		{
			const FIntPoint Base = InsideList[Rng.RandRange(0, InsideList.Num() - 1)];
			const float Roll = Rng.FRand();
			const FIntPoint* Pat = PatSingle;
			int32 PatNum = 1;
			if (Roll >= 0.85f) { Pat = PatL; PatNum = 3; }
			else if (Roll >= 0.7f) { Pat = PatLine3; PatNum = 3; }
			else if (Roll >= 0.45f) { Pat = PatLine2; PatNum = 2; }
			const int32 Turns = Rng.RandRange(0, 3);
			TArray<FIntPoint, TInlineAllocator<3>> Group;
			for (int32 i = 0; i < PatNum; ++i)
			{
				FIntPoint D = Pat[i];
				for (int32 T = 0; T < Turns; ++T)
				{
					D = FIntPoint(-D.Y, D.X);
				}
				Group.Add(Base + D);
			}
			bool bOk = true;
			for (const FIntPoint& P : Group)
			{
				if (Get(P) != EJRArenaCell::Free || IsReserved(P.X, P.Y) || IsCenterZone(P))
				{
					bOk = false;
					break;
				}
				// grupos nunca encostam em outra cobertura: sobra sempre um corredor de 8 m
				for (int32 DX = -1; DX <= 1 && bOk; ++DX)
				{
					for (int32 DY = -1; DY <= 1 && bOk; ++DY)
					{
						const FIntPoint Q(P.X + DX, P.Y + DY);
						if (Group.Contains(Q))
						{
							continue;
						}
						const EJRArenaCell QC = Get(Q);
						bOk = QC != EJRArenaCell::Low && QC != EJRArenaCell::High;
					}
				}
				if (!bOk)
				{
					break;
				}
			}
			if (!bOk)
			{
				continue;
			}
			const bool bSingle = PatNum == 1;
			// [A-089] cobertura alta (carro, contêiner) só perto do muro; no meio da arena, só baixa (dá para
			// atirar por cima e ver a horda chegando).
			bool bNearWall = true;
			for (const FIntPoint& P : Group)
			{
				bNearWall &= GetDistOut(P.X, P.Y) <= HighCoverMaxDistOut;
			}
			const bool bHigh = bNearWall && (bSingle ? Rng.FRand() < 0.2f : Rng.FRand() < 0.5f);
			for (const FIntPoint& P : Group)
			{
				SetCell(P.X, P.Y, bHigh ? EJRArenaCell::High : EJRArenaCell::Low);
				SetTag(P.X, P.Y, EJRArenaCellTag::Cover);
			}
			Blocked += Group.Num();
		}
	}

	// ---------------- conserto: nenhuma área fechada (abre a cobertura que separa)
	for (int32 Iter = 0; Iter < 80; ++Iter)
	{
		TArray<uint8> Seen;
		FloodFromStart(Seen);
		auto IsLost = [this, &Seen](const FIntPoint& P)
		{
			return Get(P) == EJRArenaCell::Free && Seen[P.X * Grid + P.Y] == 0;
		};
		bool bAnyLost = false;
		for (const FIntPoint& P : InsideList)
		{
			if (IsLost(P))
			{
				bAnyLost = true;
				break;
			}
		}
		if (!bAnyLost)
		{
			break;
		}
		bool bOpened = false;
		for (const FIntPoint& P : InsideList)
		{
			const EJRArenaCell PC = Get(P);
			if ((PC != EJRArenaCell::Low && PC != EJRArenaCell::High) || IsReserved(P.X, P.Y))
			{
				continue;
			}
			bool bTouchSeen = false;
			bool bTouchLost = false;
			for (const FIntPoint& D : Dirs4)
			{
				const FIntPoint Q = P + D;
				if (!IsValidCell(Q.X, Q.Y))
				{
					continue;
				}
				bTouchSeen |= Seen[Q.X * Grid + Q.Y] != 0;
				bTouchLost |= IsLost(Q);
			}
			if (bTouchSeen && bTouchLost)
			{
				SetCell(P.X, P.Y, EJRArenaCell::Free);
				bOpened = true;
				break;
			}
		}
		if (!bOpened)
		{
			OutProblem = TEXT("área fechada");
			return false;
		}
	}
	if (CountUnreachableFree() > 0)
	{
		OutProblem = TEXT("área fechada");
		return false;
	}
	if (!FixSightLines(Rng))
	{
		OutProblem = TEXT("linha de visão longa");
		return false;
	}
	if (CountCenterExits() < 3)
	{
		OutProblem = FString::Printf(TEXT("só %d saídas do centro"), CountCenterExits());
		return false;
	}

	// ---------------- 3. pontos
	TArray<FIntPoint> FreeCells;
	for (const FIntPoint& P : InsideList)
	{
		if (Get(P) == EJRArenaCell::Free && !IsReserved(P.X, P.Y))
		{
			FreeCells.Add(P);
		}
	}
	auto IsEdge = [this](const FIntPoint& P)
	{
		for (int32 DX = -1; DX <= 1; ++DX)
		{
			for (int32 DY = -1; DY <= 1; ++DY)
			{
				if (Get(P.X + DX, P.Y + DY) == EJRArenaCell::Out)
				{
					return true;
				}
			}
		}
		return false;
	};

	// surgimento: longe do centro, de preferência colado no muro ("chegam pelas bordas")
	{
		TArray<FIntPoint> Cand;
		const float MinDist = FMath::Max(3.f, 0.5f * R);
		for (const FIntPoint& P : FreeCells)
		{
			if (Dist(P, Start) >= MinDist)
			{
				Cand.Add(P);
			}
		}
		ShuffleWith(Cand, Rng);
		Cand.StableSort([&IsEdge](const FIntPoint& A, const FIntPoint& B) { return IsEdge(A) && !IsEdge(B); });
		for (const FIntPoint& P : Cand)
		{
			bool bSpaced = true;
			for (const FIntPoint& O : SpawnCells)
			{
				bSpaced &= Chebyshev(P, O) >= 2;
			}
			if (bSpaced)
			{
				SpawnCells.Add(P);
				if (SpawnCells.Num() >= 20)
				{
					break;
				}
			}
		}
		if (SpawnCells.Num() < MinSpawnCells)
		{
			OutProblem = FString::Printf(TEXT("só %d pontos de surgimento"), SpawnCells.Num());
			return false;
		}
		for (const FIntPoint& P : SpawnCells)
		{
			SetReserved(P.X, P.Y, true);
		}
	}

	// nave: um ponto por quadrante, longe do centro e com espaço em volta
	for (int32 Sector = 0; Sector < 4; ++Sector)
	{
		float BestScore = -1.f;
		FIntPoint Best(-1, -1);
		for (const FIntPoint& P : FreeCells)
		{
			if (IsReserved(P.X, P.Y) || Dist(P, Start) < 0.35f * R)
			{
				continue;
			}
			const float Ang = FMath::Atan2(static_cast<float>(P.Y - Start.Y), static_cast<float>(P.X - Start.X));
			const int32 S = FMath::TruncToInt(((Ang + UE_PI) / (2.f * UE_PI)) * 4.f) % 4;
			if (S != Sector)
			{
				continue;
			}
			int32 FreeAround = 0;
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				for (int32 DY = -1; DY <= 1; ++DY)
				{
					FreeAround += Get(P.X + DX, P.Y + DY) == EJRArenaCell::Free ? 1 : 0;
				}
			}
			const float Score = Dist(P, Start) + 0.5f * FreeAround + Rng.FRand();
			if (Score > BestScore)
			{
				BestScore = Score;
				Best = P;
			}
		}
		if (Best.X >= 0)
		{
			ExtractionCells.Add(Best);
			SetReserved(Best.X, Best.Y, true);
		}
	}
	if (ExtractionCells.Num() < MinExtractionCells)
	{
		OutProblem = FString::Printf(TEXT("só %d pontos da nave"), ExtractionCells.Num());
		return false;
	}

	// objetivos (ninhos, elite): espalhados, fora do centro
	{
		TArray<FIntPoint> Cand;
		for (const FIntPoint& P : FreeCells)
		{
			if (!IsReserved(P.X, P.Y) && Dist(P, Start) >= 0.3f * R)
			{
				Cand.Add(P);
			}
		}
		ShuffleWith(Cand, Rng);
		// [A-089] ninho de preferência longe do muro e sem nada escalável em volta (o herói não sobe num carro
		// colado no ninho para atirar de cima).
		auto NestScore = [this](const FIntPoint& P)
		{
			int32 Score = GetDistOut(P.X, P.Y) >= 2 ? 1 : 0;
			bool bClean = true;
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				for (int32 DY = -1; DY <= 1; ++DY)
				{
					const EJRArenaCell Near = Get(P.X + DX, P.Y + DY);
					bClean &= Near != EJRArenaCell::Low && Near != EJRArenaCell::High;
				}
			}
			return Score + (bClean ? 2 : 0);
		};
		Cand.StableSort([&NestScore](const FIntPoint& A, const FIntPoint& B) { return NestScore(A) > NestScore(B); });
		for (const FIntPoint& P : Cand)
		{
			bool bSpaced = true;
			for (const FIntPoint& O : ObjectiveCells)
			{
				bSpaced &= Chebyshev(P, O) >= 3;
			}
			if (bSpaced)
			{
				ObjectiveCells.Add(P);
				if (ObjectiveCells.Num() >= 6)
				{
					break;
				}
			}
		}
		if (ObjectiveCells.Num() < MinObjectiveCells)
		{
			OutProblem = FString::Printf(TEXT("só %d pontos de objetivo"), ObjectiveCells.Num());
			return false;
		}
		for (const FIntPoint& P : ObjectiveCells)
		{
			SetReserved(P.X, P.Y, true);
		}
	}

	// baús (até 2; não é obrigatório). [A-089] Primeiro nas vagas dos conjuntos (protegidas, 2 acessos);
	// depois colados no muro, longe do centro, nunca em beco sem saída.
	{
		auto ChestSpaced = [this](const FIntPoint& P)
		{
			for (const FIntPoint& O : ObjectiveCells)
			{
				if (Chebyshev(P, O) < 2)
				{
					return false;
				}
			}
			for (const FIntPoint& O : ChestCells)
			{
				if (Chebyshev(P, O) < 4)
				{
					return false;
				}
			}
			return true;
		};
		TArray<FIntPoint> Slots;
		for (const FJRArenaAssembly& Asm : Assemblies)
		{
			if (Asm.ChestSlot.X >= 0)
			{
				Slots.Add(Asm.ChestSlot);
			}
		}
		ShuffleWith(Slots, Rng);
		for (const FIntPoint& P : Slots)
		{
			if (ChestCells.Num() < 2 && Get(P) == EJRArenaCell::Free && CountFreeNeighbors4(P) >= 2 && ChestSpaced(P))
			{
				ChestCells.Add(P);
			}
		}
		TArray<FIntPoint> Cand;
		for (const FIntPoint& P : FreeCells)
		{
			if (!IsReserved(P.X, P.Y) && Dist(P, Start) >= 0.4f * R && GetDistOut(P.X, P.Y) <= 1 && CountFreeNeighbors4(P) >= 2)
			{
				Cand.Add(P);
			}
		}
		ShuffleWith(Cand, Rng);
		for (const FIntPoint& P : Cand)
		{
			if (ChestCells.Num() >= 2)
			{
				break;
			}
			if (ChestSpaced(P))
			{
				ChestCells.Add(P);
				SetReserved(P.X, P.Y, true);
			}
		}
	}

	OutProblem = Validate();
	return OutProblem.IsEmpty();
}

FString FJRArenaLayout::AssemblyName(EJRArenaAssemblyKind InKind)
{
	switch (InKind)
	{
	case EJRArenaAssemblyKind::Posto: return TEXT("posto");
	case EJRArenaAssemblyKind::Patio: return TEXT("pátio de contêineres");
	case EJRArenaAssemblyKind::FerroVelho: return TEXT("ferro-velho");
	case EJRArenaAssemblyKind::Acampamento: return TEXT("acampamento");
	default: return TEXT("?");
	}
}

void FJRArenaLayout::SetTag(int32 X, int32 Y, EJRArenaCellTag Value)
{
	if (IsValidCell(X, Y) && CellTags.Num() == Grid * Grid)
	{
		CellTags[X * Grid + Y] = static_cast<uint8>(Value);
	}
}

int32 FJRArenaLayout::CountFreeNeighbors4(const FIntPoint& P) const
{
	using namespace JRArenaLayoutPrivate;
	int32 Count = 0;
	for (const FIntPoint& D : Dirs4)
	{
		Count += Get(P.X + D.X, P.Y + D.Y) == EJRArenaCell::Free ? 1 : 0;
	}
	return Count;
}

float FJRArenaLayout::FreeRatio() const
{
	int32 InsideCount = 0;
	int32 FreeCount = 0;
	for (const EJRArenaCell Cell : Cells)
	{
		if (Cell != EJRArenaCell::Out)
		{
			++InsideCount;
			FreeCount += Cell == EJRArenaCell::Free ? 1 : 0;
		}
	}
	return InsideCount > 0 ? static_cast<float>(FreeCount) / static_cast<float>(InsideCount) : 0.f;
}

void FJRArenaLayout::ComputeDistOut()
{
	using namespace JRArenaLayoutPrivate;
	DistOut.Init(0, Grid * Grid);
	TArray<FIntPoint> Queue;
	for (int32 X = 0; X < Grid; ++X)
	{
		for (int32 Y = 0; Y < Grid; ++Y)
		{
			if (!IsInside(X, Y))
			{
				continue;
			}
			DistOut[X * Grid + Y] = 255;
			for (const FIntPoint& D : Dirs4)
			{
				if (!IsInside(X + D.X, Y + D.Y))
				{
					DistOut[X * Grid + Y] = 1;
					Queue.Add(FIntPoint(X, Y));
					break;
				}
			}
		}
	}
	for (int32 Head = 0; Head < Queue.Num(); ++Head)
	{
		const FIntPoint P = Queue[Head];
		const int32 NextDist = static_cast<int32>(DistOut[P.X * Grid + P.Y]) + 1;
		for (const FIntPoint& D : Dirs4)
		{
			const FIntPoint Q(P.X + D.X, P.Y + D.Y);
			if (IsInside(Q.X, Q.Y) && static_cast<int32>(DistOut[Q.X * Grid + Q.Y]) > NextDist)
			{
				DistOut[Q.X * Grid + Q.Y] = static_cast<uint8>(FMath::Min(NextDist, 254));
				Queue.Add(Q);
			}
		}
	}
}

void FJRArenaLayout::PlaceAssemblies(const FRandomStream& Rng, float Radius)
{
	using namespace JRArenaLayoutPrivate;
	const int32 Wanted = Size <= 12 ? 2 : (Size <= 16 ? 3 : 4);
	TArray<EJRArenaAssemblyKind> Kinds = { EJRArenaAssemblyKind::Patio, EJRArenaAssemblyKind::FerroVelho,
		EJRArenaAssemblyKind::Acampamento };
	ShuffleWith(Kinds, Rng);
	// o posto é o marco do tema: quase sempre entra (e entra primeiro, que é o maior)
	if (Rng.FRand() < 0.75f)
	{
		Kinds.Insert(EJRArenaAssemblyKind::Posto, 0);
	}
	else
	{
		Kinds.Add(EJRArenaAssemblyKind::Posto);
	}
	TArray<FIntPoint> EdgeCells;
	TArray<FIntPoint> EdgeDirs;
	for (int32 X = 0; X < Grid; ++X)
	{
		for (int32 Y = 0; Y < Grid; ++Y)
		{
			if (!IsInside(X, Y))
			{
				continue;
			}
			for (const FIntPoint& D : Dirs4)
			{
				if (!IsInside(X + D.X, Y + D.Y))
				{
					EdgeCells.Add(FIntPoint(X, Y));
					EdgeDirs.Add(D);
				}
			}
		}
	}
	TArray<int32> Order;
	for (int32 i = 0; i < EdgeCells.Num(); ++i)
	{
		Order.Add(i);
	}
	for (const EJRArenaAssemblyKind Kind : Kinds)
	{
		if (Assemblies.Num() >= Wanted)
		{
			break;
		}
		ShuffleWith(Order, Rng);
		for (const int32 Idx : Order)
		{
			if (TryPlaceAssembly(Kind, EdgeCells[Idx], EdgeDirs[Idx], Rng.RandRange(0, 1) == 1, Radius))
			{
				break;
			}
		}
	}
}

bool FJRArenaLayout::TryPlaceAssembly(EJRArenaAssemblyKind InKind, const FIntPoint& InBase, const FIntPoint& InOutDir, bool bMirror,
	float Radius)
{
	using namespace JRArenaLayoutPrivate;
	// Molde por linha (linha 0 colada no muro). S = alta, L = baixa, Y = pátio livre, C = vaga do baú (livre).
	const TCHAR* Rows[3] = { nullptr, nullptr, nullptr };
	int32 RowCount = 0;
	switch (InKind)
	{
	case EJRArenaAssemblyKind::Posto:
		Rows[0] = TEXT("SS"); Rows[1] = TEXT("YY"); Rows[2] = TEXT("YY"); RowCount = 3; // loja + cobertura 2 x 2
		break;
	case EJRArenaAssemblyKind::Patio:
		Rows[0] = TEXT("SSS"); Rows[1] = TEXT("SCY"); RowCount = 2; // contêineres em L, baú no canto protegido
		break;
	case EJRArenaAssemblyKind::FerroVelho:
		Rows[0] = TEXT("SYS"); Rows[1] = TEXT("YCL"); RowCount = 2; // dois carcaças, barris, baú na frente do vão
		break;
	default: // Acampamento
		Rows[0] = TEXT("LL"); Rows[1] = TEXT("CY"); RowCount = 2; // barricadas de costas para o muro
		break;
	}
	FJRArenaAssembly Asm;
	Asm.Kind = InKind;
	Asm.OutDir = InOutDir;
	Asm.Base = InBase;
	Asm.AlongDir = FIntPoint(-InOutDir.Y, InOutDir.X) * (bMirror ? -1 : 1);
	Asm.Width = FCString::Strlen(Rows[0]);
	Asm.Depth = RowCount;

	for (int32 V = 0; V < Asm.Depth; ++V)
	{
		for (int32 U = 0; U < Asm.Width; ++U)
		{
			const FIntPoint P = Asm.Local(U, V);
			if (!IsInside(P.X, P.Y) || IsReserved(P.X, P.Y) || Get(P) != EJRArenaCell::Free || IsCenterZone(P))
			{
				return false;
			}
			if (V == 0 && IsInside(P.X + InOutDir.X, P.Y + InOutDir.Y))
			{
				return false; // a linha de trás precisa encostar no muro (de costas para a muralha)
			}
			for (int32 DX = -1; DX <= 1; ++DX)
			{
				for (int32 DY = -1; DY <= 1; ++DY)
				{
					if (GetAssemblyIndex(P.X + DX, P.Y + DY) >= 0)
					{
						return false; // folga de uma célula entre conjuntos
					}
				}
			}
		}
	}
	// frente livre: a linha logo depois do conjunto fica aberta (caminho)
	for (int32 U = 0; U < Asm.Width; ++U)
	{
		const FIntPoint Front = Asm.Local(U, Asm.Depth);
		if (!IsInside(Front.X, Front.Y) || Get(Front) != EJRArenaCell::Free || GetAssemblyIndex(Front.X, Front.Y) >= 0)
		{
			return false;
		}
	}
	// longe do centro e separado dos outros por ângulo (visto do centro)
	const FIntPoint Far = Asm.Local(Asm.Width - 1, Asm.Depth - 1);
	const float MidX = (Asm.Base.X + Far.X) * 0.5f;
	const float MidY = (Asm.Base.Y + Far.Y) * 0.5f;
	if (FMath::Sqrt(FMath::Square(MidX - Start.X) + FMath::Square(MidY - Start.Y)) < 0.45f * Radius)
	{
		return false;
	}
	const float Angle = FMath::Atan2(MidY - Start.Y, MidX - Start.X);
	for (const FJRArenaAssembly& Other : Assemblies)
	{
		const FIntPoint OtherFar = Other.Local(Other.Width - 1, Other.Depth - 1);
		const float OtherAngle = FMath::Atan2((Other.Base.Y + OtherFar.Y) * 0.5f - Start.Y, (Other.Base.X + OtherFar.X) * 0.5f - Start.X);
		if (FMath::Abs(FMath::FindDeltaAngleRadians(Angle, OtherAngle)) < FMath::DegreesToRadians(70.f))
		{
			return false;
		}
	}

	for (int32 V = 0; V < Asm.Depth; ++V)
	{
		for (int32 U = 0; U < Asm.Width; ++U)
		{
			const FIntPoint P = Asm.Local(U, V);
			Asm.Cells.Add(P);
			switch (Rows[V][U])
			{
			case TEXT('S'):
				SetCell(P.X, P.Y, EJRArenaCell::High);
				Asm.Solid.Add(P);
				break;
			case TEXT('L'):
				SetCell(P.X, P.Y, EJRArenaCell::Low);
				Asm.LowCells.Add(P);
				break;
			case TEXT('C'):
				Asm.ChestSlot = P;
				Asm.Yard.Add(P);
				break;
			default:
				Asm.Yard.Add(P);
				break;
			}
		}
	}
	if (CountUnreachableFree() > 0)
	{
		for (const FIntPoint& P : Asm.Cells)
		{
			SetCell(P.X, P.Y, EJRArenaCell::Free);
		}
		return false;
	}
	const int32 Index = Assemblies.Num();
	for (const FIntPoint& P : Asm.Cells)
	{
		SetReserved(P.X, P.Y, true);
		SetTag(P.X, P.Y, EJRArenaCellTag::Assembly);
		AssemblyAt[P.X * Grid + P.Y] = static_cast<int8>(Index);
	}
	for (int32 U = 0; U < Asm.Width; ++U)
	{
		const FIntPoint Front = Asm.Local(U, Asm.Depth);
		SetReserved(Front.X, Front.Y, true);
	}
	if (InKind == EJRArenaAssemblyKind::Posto)
	{
		StoreCells = Asm.Solid;
		CanopyCells = Asm.Yard;
		bHasLandmark = true;
	}
	Assemblies.Add(Asm);
	return true;
}

FString FJRArenaLayout::Validate() const
{
	if (Grid <= 2 || Cells.Num() != Grid * Grid)
	{
		return TEXT("planta vazia");
	}
	if (Get(Start) != EJRArenaCell::Free)
	{
		return TEXT("centro bloqueado");
	}
	const int32 Lost = CountUnreachableFree();
	if (Lost > 0)
	{
		return FString::Printf(TEXT("%d células sem caminho"), Lost);
	}
	const int32 Longest = LongestSightRun();
	if (Longest > MaxSightRun)
	{
		return FString::Printf(TEXT("linha de visão de %d células"), Longest);
	}
	if (CountCenterExits() < 3)
	{
		return TEXT("menos de 3 saídas do centro");
	}
	if (SpawnCells.Num() < MinSpawnCells || ExtractionCells.Num() < MinExtractionCells || ObjectiveCells.Num() < MinObjectiveCells)
	{
		return TEXT("pontos insuficientes");
	}
	TArray<uint8> Seen;
	FloodFromStart(Seen);
	auto AllReachable = [this, &Seen](const TArray<FIntPoint>& List)
	{
		for (const FIntPoint& P : List)
		{
			if (Get(P) != EJRArenaCell::Free || Seen[P.X * Grid + P.Y] == 0)
			{
				return false;
			}
		}
		return true;
	};
	if (!AllReachable(SpawnCells) || !AllReachable(ExtractionCells) || !AllReachable(ObjectiveCells) || !AllReachable(ChestCells)
		|| !AllReachable(CanopyCells))
	{
		return TEXT("ponto especial fora do caminho");
	}
	// [A-089] regras de posicionamento
	for (int32 X = 0; X < Grid; ++X)
	{
		for (int32 Y = 0; Y < Grid; ++Y)
		{
			const EJRArenaCell Kind = Get(X, Y);
			if ((Kind == EJRArenaCell::Low || Kind == EJRArenaCell::High) && IsCenterZone(FIntPoint(X, Y))
				&& GetTag(X, Y) != EJRArenaCellTag::Pillar)
			{
				return TEXT("cobertura na zona central");
			}
		}
	}
	for (const FIntPoint& P : ChestCells)
	{
		if (CountFreeNeighbors4(P) < 2)
		{
			return TEXT("baú com menos de 2 acessos");
		}
	}
	for (const FJRArenaAssembly& Asm : Assemblies)
	{
		for (int32 U = 0; U < Asm.Width; ++U)
		{
			const FIntPoint P = Asm.Local(U, 0);
			if (IsInside(P.X + Asm.OutDir.X, P.Y + Asm.OutDir.Y))
			{
				return FString::Printf(TEXT("%s solto do muro"), *AssemblyName(Asm.Kind));
			}
		}
	}
	if (FreeRatio() < MinFreeRatio)
	{
		return FString::Printf(TEXT("pouca área livre (%.0f%%)"), FreeRatio() * 100.f);
	}
	// ninguém em cima de ninguém
	TSet<FIntPoint> Used;
	for (const TArray<FIntPoint>* List : { &SpawnCells, &ExtractionCells, &ObjectiveCells, &ChestCells, &CanopyCells })
	{
		for (const FIntPoint& P : *List)
		{
			bool bAlready = false;
			Used.Add(P, &bAlready);
			if (bAlready)
			{
				return TEXT("pontos sobrepostos");
			}
		}
	}
	return FString();
}

bool FJRArenaLayout::GenerateWithRetries(int32 BaseSeed, int32 SectorLevel, int32 ForcedShape, int32 MaxAttempts,
	FJRArenaLayout& OutLayout, int32& OutAttempts, FString& OutLastProblem)
{
	OutAttempts = 0;
	for (int32 Attempt = 0; Attempt < FMath::Max(1, MaxAttempts); ++Attempt)
	{
		++OutAttempts;
		const uint32 Mixed = static_cast<uint32>(BaseSeed) * 7919u + static_cast<uint32>(Attempt) * 104729u;
		const int32 TrySeed = Attempt == 0 ? BaseSeed : static_cast<int32>(Mixed & 0x7fffffffu);
		if (OutLayout.Generate(TrySeed, SectorLevel, ForcedShape, true, OutLastProblem))
		{
			return true;
		}
	}
	// Plano B: círculo sem cobertura extra (só as quebras de visão).
	++OutAttempts;
	return OutLayout.Generate(BaseSeed, SectorLevel, static_cast<int32>(EJRArenaShape::Circle), false, OutLastProblem);
}

FString FJRArenaLayout::ToAscii() const
{
	FString Out;
	for (int32 Y = Grid - 1; Y >= 0; --Y)
	{
		for (int32 X = 0; X < Grid; ++X)
		{
			const FIntPoint P(X, Y);
			TCHAR Ch = TEXT(' ');
			switch (Get(P))
			{
			case EJRArenaCell::Free: Ch = TEXT('.'); break;
			case EJRArenaCell::Low: Ch = TEXT('b'); break;
			case EJRArenaCell::High: Ch = TEXT('H'); break;
			default: break;
			}
			if (GetTag(X, Y) == EJRArenaCellTag::Pillar) { Ch = TEXT('I'); }
			if (GetAssemblyIndex(X, Y) >= 0 && Get(P) == EJRArenaCell::Free) { Ch = TEXT('y'); }
			if (P == Start) { Ch = TEXT('@'); }
			else if (SpawnCells.Contains(P)) { Ch = TEXT('s'); }
			else if (ExtractionCells.Contains(P)) { Ch = TEXT('E'); }
			else if (ObjectiveCells.Contains(P)) { Ch = TEXT('o'); }
			else if (ChestCells.Contains(P)) { Ch = TEXT('c'); }
			else if (CanopyCells.Contains(P)) { Ch = TEXT('p'); }
			Out.AppendChar(Ch);
		}
		Out.AppendChar(TEXT('\n'));
	}
	return Out;
}

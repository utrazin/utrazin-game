// Stub MÍNIMO de tipos da Unreal para compilar a lógica pura fora da engine (g++/clang).
// NÃO substitui a compilação real com a Unreal. Ver tests/cpp/README.md.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <random>

using int32 = std::int32_t;
using uint8 = std::uint8_t;

#define UENUM(...)
#define USTRUCT(...)
#define UPROPERTY(...)
#define UFUNCTION(...)
#define UMETA(...)
#define GENERATED_BODY()
#define JOGORESGATE_API
#define KINDA_SMALL_NUMBER (1.e-4f)

template <typename T> struct TNumericLimits { static constexpr T Max() { return std::numeric_limits<T>::max(); } };

struct FMath
{
	template <typename T> static T Clamp(T V, T Lo, T Hi) { return V < Lo ? Lo : (V > Hi ? Hi : V); }
	template <typename T> static T Max(T A, T B) { return A > B ? A : B; }
	template <typename T> static T Min(T A, T B) { return A < B ? A : B; }
	template <typename T> static T Abs(T A) { return A < 0 ? -A : A; }
	static double Sqrt(double V) { return std::sqrt(V); }
	static float Lerp(float A, float B, float Alpha) { return A + (B - A) * Alpha; }
	static float DegreesToRadians(float D) { return D * 3.14159265358979323846f / 180.f; }
	static double Acos(double V) { return std::acos(V); }
};

struct FVector
{
	double X = 0, Y = 0, Z = 0;
	FVector() = default;
	FVector(double InX, double InY, double InZ) : X(InX), Y(InY), Z(InZ) {}
	FVector operator+(const FVector& O) const { return {X + O.X, Y + O.Y, Z + O.Z}; }
	FVector operator-(const FVector& O) const { return {X - O.X, Y - O.Y, Z - O.Z}; }
	FVector operator*(double S) const { return {X * S, Y * S, Z * S}; }
	static double DotProduct(const FVector& A, const FVector& B) { return A.X * B.X + A.Y * B.Y + A.Z * B.Z; }
	static FVector CrossProduct(const FVector& A, const FVector& B)
	{
		return {A.Y * B.Z - A.Z * B.Y, A.Z * B.X - A.X * B.Z, A.X * B.Y - A.Y * B.X};
	}
	double Size() const { return std::sqrt(X * X + Y * Y + Z * Z); }
	bool IsNearlyZero(double Tol = 1.e-4) const { return std::fabs(X) <= Tol && std::fabs(Y) <= Tol && std::fabs(Z) <= Tol; }
	FVector GetSafeNormal() const { const double S = Size(); return S < 1.e-8 ? FVector() : FVector(X / S, Y / S, Z / S); }
};

/** Equivalente funcional ao FRandomStream::VRandCone (distribuição uniforme no cone). */
struct FRandomStream
{
	std::mt19937 Gen;
	explicit FRandomStream(int32 Seed) : Gen(static_cast<unsigned>(Seed)) {}
	double FRand() { return std::uniform_real_distribution<double>(0.0, 1.0)(Gen); }
	FVector VRandCone(const FVector& Dir, float HalfAngleRad)
	{
		const FVector W = Dir.GetSafeNormal();
		const FVector Helper = std::fabs(W.Z) < 0.999 ? FVector(0, 0, 1) : FVector(1, 0, 0);
		const FVector U = FVector::CrossProduct(Helper, W).GetSafeNormal();
		const FVector V = FVector::CrossProduct(W, U);
		const double CosMax = std::cos(HalfAngleRad);
		const double CosT = 1.0 - FRand() * (1.0 - CosMax);
		const double SinT = std::sqrt(std::max(0.0, 1.0 - CosT * CosT));
		const double Phi = FRand() * 2.0 * 3.14159265358979323846;
		return (U * (std::cos(Phi) * SinT) + V * (std::sin(Phi) * SinT) + W * CosT).GetSafeNormal();
	}
};

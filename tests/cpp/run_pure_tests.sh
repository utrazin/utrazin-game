#!/bin/sh
# Compila e roda a lógica pura do jogo fora da Unreal (stubs em tests/cpp/stubs).
# Uso: sh tests/cpp/run_pure_tests.sh   (requer g++ ou clang++ com C++17)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../../unreal/JogoResgate/Source/JogoResgate"
OUT="${TMPDIR:-/tmp}/jr_pure_tests"
CXX="${CXX:-g++}"
"$CXX" -std=c++17 -Wall -Wextra -Werror -I"$HERE/stubs" -I"$SRC" \
  "$HERE/pure_logic_tests.cpp" "$SRC/Vehicles/JRVehicleDamageModel.cpp" "$SRC/AI/JRAimPrediction.cpp" \
  "$SRC/AI/JREnemyStateLogic.cpp" -o "$OUT"
"$OUT"

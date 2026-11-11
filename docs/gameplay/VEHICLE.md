# Veículo (SUV 4x4 provisório, A-008)

## Parâmetros iniciais de tuning (a validar em M1)

| Parâmetro | Valor inicial | Observação |
|---|---|---|
| Massa | 2.100 kg | SUV médio |
| Centro de massa | offset Z -40 cm do centro do chassi | evita capotar fácil |
| Torque máx. | 450 Nm a 3.500 RPM | curva em `CurveFloat` `CF_SUV_Torque` |
| RPM máx. | 6.000 | |
| Marchas | 5 + ré, automática | |
| Tração | 4x4, 50/50 | |
| Ângulo de direção | 40° dianteiras | |
| Suspensão: curso | 30 cm | terreno acidentado |
| Suspensão: rigidez | 250 (Spring Rate) | ajustar |
| Amortecimento | compressão 0,5 / retorno 0,6 | |
| Raio da roda | 40 cm | |

Valores são ponto de partida para o `vehicle-engineer`; registre alterações em `docs/qa/vehicle-tuning.md`.

## Modelo de dano (`FJRVehicleDamageState`)

| Zona | Vida | Efeito ao zerar |
|---|---|---|
| Front | 100 | Integridade -; atropelar causa dano aqui (A-010) |
| Rear | 100 | Integridade - |
| Left / Right | 100 | Integridade - |
| Engine | 100 | Torque escala de 100% até 35% conforme vida; abaixo de 25%: fumaça |
| Pneus (FL, FR, RL, RR) | 1 estado: ok/furado | Atrito da roda x0,45, raio -12%, puxão lateral |

Integridade global = média ponderada das zonas (Engine peso 2). Veículo **inutilizado** quando o motor chega a 0 **ou** a integridade cai abaixo de 10% -> `OnVehicleDisabled` (A-014: reinício no checkpoint).

Dano de impacto: `max(0, (velocidade_relativa_kmh - 15) * 0,8)` aplicado à zona mais próxima do ponto de contato. Pneu fura com projétil (arqueiro/atirador) ou impacto lateral > 40 km/h na roda (chance configurável).

## Critérios de teste (prompt mestre, Etapa 5)

Ver `tests/gameplay/checklists/VEHICLE.md`. Lógica pura coberta por `JR.Vehicle.DamageModel.*` (Automation Tests).

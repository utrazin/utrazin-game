# ADR-003: Chaos Vehicles e modelo de dano

- Status: proposto
- Data: 2026-11-11

## Decisão

- `AJRVehiclePawn` herda de `AWheeledVehiclePawn` com `UChaosWheeledVehicleMovementComponent` (4 rodas, tração 4x4).
- Dano é **lógica pura** em `FJRVehicleDamageState` (zonas: Front, Rear, Left, Right, Engine; 4 pneus), aplicada ao movimento por `UJRVehicleDamageComponent`.
- Pneu furado: reduz `FrictionForceMultiplier` e raio efetivo da roda afetada, e aplica leve torque de puxão; resultado físico real, não só visual.
- Motor danificado: escala a curva de torque (`SetMaxEngineTorque`) e ativa fumaça/áudio.
- Integridade 0 = `OnVehicleDisabled` (A-014).

## Alternativas

Física customizada (raycast suspension) dá controle total, mas custa meses. Chaos Vehicles é nativo e suficiente para o MVP.

## Riscos

Tuning de Chaos é sensível à massa/centro de gravidade e colisão; ver `docs/gameplay/VEHICLE.md`.

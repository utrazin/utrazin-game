# Pesquisa técnica UE5.8 (resumo)

Resumo do agente de pesquisa técnica (o arquivo completo não pôde ser gravado por ele). Valores são ponto de partida, ajustar testando.

## Carro (Chaos Vehicles)
1. Colisão primeiro: malha visual do buggy em NoCollision; só o physics asset do SKM_Offroad encosta no mundo, com corpo do chassi parecido com o buggy.
2. Rastreio das rodas: Pawn = Ignore; SweepShape Spherecast ou Shapecast; SweepType Simple.
3. Corpo: Mass 1400; Center Of Mass Override Z ~ -30; InertiaTensorScale Z 1.5; Angular Damping do chassi ~1.
4. Rodas: FrictionForceMultiplier 4; CorneringStiffness 2000; LateralSlipGraph plano; SideSlipModifier 0.7 frente / 0.4 trás; MaxSteerAngle 35; ABS e controle de tração ligados.
5. Tração: AllWheelDrive (FrontRearSplit 0.45); curva de torque mais plana, MaxTorque ~600; um pouco de downforce.
6. Física: Async Physics ~120 Hz OU substepping (não os dois); CCD no chassi; colisão simples e grossa em rampas e paredes. Se ainda "flutuar": TargetRotationControl / StabilizeControl.
7. Motorista: socket "Seat" + componente DriverMesh (NoCollision) tocando a animação "Driving" do Mixamo (retarget); IK de mãos no volante é opcional.
8. Zumbi x carro: cápsula continua Overlap; caixa ImpactZone no para-choque/capô; acima de X km/h ragdoll com impulso pela velocidade (AddImpulse bVelChange); abaixo, cambaleio.
9. Hordas: freio limitado por batida; sockets de agarrar no capô (attach + montage); limite de ragdolls ativos; pooling.
10. Não há plugin grátis bom de carro arcade para UE5: ajustar o Chaos primeiro.

## Vegetação densa
- Assets CC0: Quaternius (Ultimate Nature etc.), KayKit; Nanite em árvores e pedras.
- Grama: Landscape Grass Type (precisa de Landscape) ou instâncias HISM.
- Árvores/pedras: PCG por script (PCGVolume, set_graph, generate(True)).
- Evitar InstancedFoliageActor.add_instances via Python na 5.8 (relatos de crash).

Pontos não confirmados (o leitor de páginas atingiu limite): alguns nomes de propriedades do Chaos e a notícia de Megascans grátis de novo.

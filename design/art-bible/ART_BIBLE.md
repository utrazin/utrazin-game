# Art Bible (v0.1 provisória)

> Valores marcados **[PROVISÓRIO]** derivam de A-004 (semi-realista estilizado) e **não foram aprovados**. Nenhuma arte final avança sem aprovação humana registrada no manifesto.

## 1. Identidade

- **Tom**: sobrevivência tensa, mas com calor humano no resgate (o abraço é o clímax emocional de cada fase).
- **Estilo [PROVISÓRIO]**: semi-realista estilizado. Proporções humanas reais com leve exagero de mãos/cabeça (até 5%), formas legíveis, superfícies com desgaste pintado em vez de detalhe fotográfico.
- **Originalidade**: nada copiado de franquias. Referências servem para mood e leitura de forma, nunca para silhueta ou elementos de marca.

## 2. Forma e silhueta

- Cada personagem jogável deve ser reconhecível **apenas pela silhueta** a 30 m (teste: silhueta preta em fundo branco, ver `silhouettes/`).
- Inimigos: silhuetas quebradas e assimétricas; jogáveis: silhuetas limpas e estáveis.
- Arqueiro e atirador zumbis precisam ser distinguíveis do corpo a corpo pela pose e pela arma a 40 m.

## 3. Paleta [PROVISÓRIO]

| Uso | Cor | Hex |
|---|---|---|
| Ambiente Fase 1 base | Verde-oliva dessaturado | `#5B5F45` |
| Terra / estrada | Marrom poeira | `#7A6450` |
| Céu Fase 1 | Cinza âmbar | `#A89B85` |
| Zumbis (pele) | Cinza-esverdeado | `#7D8A78` |
| Ameaça / dano | Vermelho escuro | `#7A1E1E` |
| Jogáveis acento | Azul-petróleo | `#1F6F78` |
| Tecnologia alienígena | Ciano emissivo | `#3FF2E0` |
| UI primária | Off-white | `#EDE8DF` |

Arquivos `.ase`/`.png` de paleta vão em `palettes/` com versão no nome.

## 4. Especificações técnicas [PROVISÓRIO]

| Categoria | Triângulos LOD0 | Texturas | Texel density |
|---|---|---|---|
| Personagem jogável | 40k a 60k | 2x 4K (corpo, cabeça) | 10.24 px/cm |
| Inimigo | 20k a 35k | 1x 2K + variações MI | 5.12 px/cm |
| SUV | 60k a 90k (sem interior detalhado) | 4K corpo + 2K rodas | 5.12 px/cm |
| Pistola | 8k a 12k | 2K | 20.48 px/cm (vista em 1ª/3ª pessoa) |
| Props médios | 500 a 5k | atlas 2K | 5.12 px/cm |
| Rochas/terreno | 2k a 15k | tileable 2K + máscaras | 2.56 px/cm |

- LODs: 4 níveis (100%, 50%, 25%, 12%) para personagens e veículo; props via auto-LOD.
- Materiais: PBR metal/roughness. Texturas: `T_<Asset>_BC` (base color), `_N` (normal), `_ORM` (oclusão, roughness, metallic empacotados), `_E` (emissivo).
- Escala: 1 unidade Blender = 1 m; 1 uu Unreal = 1 cm. Export com escala aplicada (ver `docs/pipeline/BLENDER_TO_UNREAL.md`).

## 5. Personagens

- Esqueleto padrão compatível com o **UE5 Manny/Quinn** (nomes de ossos UE5) para retarget de bibliotecas.
- Skins: mesma malha base e esqueleto; variam roupa, cabelo e materiais. Skins não alteram hitbox.

## 6. Veículo

- SUV 4x4 original, suspensão alta, para-choque de impulsão, estepe traseiro visível (reforça a mecânica de pneu furado).
- Estados visuais: intacto, danificado (amassados por zona via morph/peças trocáveis), destruído.

## 7. Pistola alienígena

- Design próprio. Proibido reproduzir formas, cores ou elementos da arma de referência citada no GDD.
- Leitura: corpo orgânico-metálico, núcleo ciano emissivo que indica munição restante.

## 8. Aprovação

1. Brief (`/create-asset`) 2. Concepts (`/generate-concept`) 3. Revisão (`/review-art-style`) 4. **Aprovação humana** registrada em `approved/` + manifesto.

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 0.1 | 2026-11-11 | Versão provisória inicial |

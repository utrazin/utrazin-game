# Art Bible (v0.2)

> Estilo **cartunesco aprovado** (A-004, 2026-11-11). Valores marcados **[PROVISÓRIO]** (paleta, orçamentos) ainda não foram aprovados. Nenhuma arte final avança sem aprovação humana registrada no manifesto.

## 1. Identidade

- **Tom**: sobrevivência tensa, mas com calor humano no resgate (o abraço é o clímax emocional de cada fase).
- **Estilo (aprovado)**: **cartunesco**. Proporções exageradas (cabeça e mãos maiores, silhuetas fortes), formas simples e arredondadas, cores chapadas ou com gradiente suave, pouco detalhe de superfície. Sem fotorrealismo. Zumbis com humor visual, não grotescos. A física continua crível; só o visual é estilizado.
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

Cartoon pede menos detalhe: orçamentos menores, texturas pequenas ou cor por material, e quase nada de normal map de alta frequência.

| Categoria | Triângulos LOD0 | Texturas | Texel density |
|---|---|---|---|
| Personagem jogável | 15k a 25k | 1x 2K (ou atlas de cores 512 + máscaras) | 5.12 px/cm |
| Inimigo | 8k a 15k | 1x 1K + variações por MI (cor) | 2.56 px/cm |
| SUV | 20k a 35k | 1x 2K | 2.56 px/cm |
| Pistola | 3k a 6k | 1x 1K | 10.24 px/cm |
| Props médios | 200 a 2k | atlas/paleta compartilhada 1K | 2.56 px/cm |
| Rochas/terreno | 500 a 5k | tileable 1K + cor por vértice | 1.28 px/cm |

- **Técnica preferida**: paleta de cores em textura pequena (gradient/atlas) + UVs posicionadas por cor. Muitos props compartilham um único material. Barato e coerente.
- **Shading**: material toon (ramp de luz em 2 a 3 faixas) + contorno por pós-processo ou casco invertido, a decidir em teste visual (M3).
- LODs: 3 níveis (100%, 50%, 25%) para personagens e veículo; props via auto-LOD.
- Texturas: `T_<Asset>_BC` (cor), `_ORM` só quando necessário, `_N` raramente.
- Escala: 1 unidade Blender = 1 m; 1 uu Unreal = 1 cm.

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
| 0.2 | 2026-11-11 | Estilo cartunesco aprovado; orçamentos reduzidos; técnica de paleta e shading toon |

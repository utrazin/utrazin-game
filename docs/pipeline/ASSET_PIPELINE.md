# Pipeline de assets

Todo asset principal percorre as etapas abaixo. O status no manifesto (`assets/manifest/assets.json`) acompanha a etapa.

| Etapa | Status no manifesto | Responsável | Saída | Skill |
|---|---|---|---|---|
| A. Brief | `planned` | art-director | `design/concepts/<cat>/<ID>/BRIEF.md` | `/create-asset` |
| B. Concept | `concept` | art-director | imagens + `prompts.md` | `/generate-concept` |
| C. Aprovação | `approved_concept` ou `rejected` | **humano** | registro em `design/art-bible/approved/` | `/review-art-style` |
| D. Modelagem | `modeling` | blender-specialist | `blender/scenes/<cat>/<ID>_vNNN.blend` | n/a |
| E. Rig | `rigging` | blender-specialist | `blender/rigs/` | n/a |
| F. Animação | `animation` | animation-specialist | ações no .blend ou FBX de biblioteca | n/a |
| G. Export | `exported` | blender-specialist | `assets/final/...` + hash | `/export-blender` |
| H. Import | `imported` | gameplay/world | `.uasset` em `Content/` | `/import-unreal` |
| I. QA | `in_review` > `approved` | qa-engineer + **humano** | relatório | `/validate-asset` |

Status `deprecated` para assets substituídos (nunca apagar o histórico).

## Regras

- ID estável por asset: `CHR-` personagem, `SKN-` skin, `ENM-` inimigo, `VEH-` veículo, `WPN-` arma, `PRP-` prop, `ENV-` ambiente, `ANM-` animação, `SFX-` áudio, `UI-` interface, `FNT-` fonte, `MAT-` material. Formato `XXX-000`.
- Arquivos-fonte versionados por sufixo `_v001`, `_v002`... Arte aprovada **nunca** é sobrescrita: nova versão + novo hash.
- Placeholders: `creation_method: placeholder`, nunca `approved`.
- Image-to-3D não é malha final: precisa de retopologia, UV e revisão (`creation_method: ai_assisted`).

## Fluxo resumido

```
BRIEF -> CONCEPT -> [humano aprova] -> MODELO -> RIG -> ANIMAÇÃO -> EXPORT (hash) -> IMPORT -> QA -> [humano aprova]
                       \-> rejeitado: volta ao CONCEPT com notas
```

Detalhes técnicos de export/import: [`BLENDER_TO_UNREAL.md`](BLENDER_TO_UNREAL.md). Validação: [`ASSET_VALIDATION_IMPORT.md`](ASSET_VALIDATION_IMPORT.md).

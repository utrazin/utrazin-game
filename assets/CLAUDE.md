# assets/

- `manifest/assets.json` é a fonte de verdade de todo asset; schema em `manifest/manifest.schema.json`. Edite via `tools/pipeline/manifest.py` sempre que possível.
- `raw/`: material de entrada (referências, gravações, mocap, downloads) com licença em `licenses/`.
- `work/`: intermediários.
- `final/`: somente exports com hash registrado no manifesto.
- Nunca marque `approved` sem `reviewer` humano e `approved_at`. Nunca sobrescreva arquivo aprovado: crie nova versão.
- Download de terceiros só com licença verificada (`asset-license-auditor`).

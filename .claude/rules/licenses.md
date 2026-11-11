# Regras de licenciamento

- Leia `ASSET_LICENSES.md` antes de adicionar qualquer conteúdo de terceiros.
- Nenhum arquivo de terceiros entra sem entrada no manifesto com `license`, `origin_url`, `author` e cópia da licença em `assets/licenses/`.
- Licenças `NC`, `ND`, "personal use", "editorial" e desconhecidas são bloqueadas.
- `commercial_use_status` só vira `allowed` com fonte primária citada e aprovação humana.
- Prompts de IA nunca citam franquias, marcas ou artistas vivos.
- Rodar `python tools/pipeline/check_licenses.py` antes de PR que mexa em `assets/`.

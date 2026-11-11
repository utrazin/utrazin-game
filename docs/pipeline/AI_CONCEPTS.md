# Geração de conceitos com IA

IA gerativa é **opcional** e serve para explorar ideias. Ferramenta ainda não escolhida (OD-025).

## Requisitos para qualquer ferramenta

- Gratuita para o uso pretendido e com **licença dos pesos/saídas conhecida** e compatível com uso comercial (A-022).
- Registro de: nome, versão do modelo, licença, data, prompt, prompt negativo, seed, resolução.
- Execução local preferida (ex.: modelos abertos em interface local) para controle de licença e privacidade.

## Regras

1. **Nunca** usar nome de personagem, franquia, artista vivo ou marca no prompt.
2. Concepts de IA não são arte final. Malhas image-to-3D não são malhas finais.
3. Todo prompt fica versionado em `design/concepts/<categoria>/<ID>/prompts.md`.
4. Usar a paleta e as regras de silhueta da Art Bible no prompt.
5. Seleção e aprovação final são humanas (`/review-art-style`).

## Template de prompt (`prompts.md`)

```markdown
## <ID> v<NN> - <data>
- ferramenta: <nome> <versão>
- modelo/pesos: <nome> <versão> | licença: <licença> <url>
- seed: <seed> | resolução: <WxH> | steps/cfg: <...>
- prompt: <texto>
- negativo: <texto>
- referências usadas: <arquivos em design/art-bible/references/>
- resultado: <arquivos gerados>
- decisão: pendente | aprovado (por, data) | rejeitado (motivo)
```

## Vistas exigidas por categoria

| Categoria | Vistas |
|---|---|
| Personagem / skin | frente, lateral, costas (T-pose ou A-pose), rosto, detalhes de roupa |
| Inimigo | frente, lateral, pose de ataque |
| Veículo | frente, lateral, traseira, 3/4, estados de dano |
| Arma | lateral esquerda/direita, topo, detalhe do núcleo |

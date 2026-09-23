# Dados e atribuição a terceiros

## WiCE

Fonte: Ryo Kamoi, Tanya Goyal, Juan Diego Rodriguez e Greg Durrett. **WiCE: Real-World Entailment for Claims in Wikipedia**, EMNLP 2023. [Paper](https://aclanthology.org/2023.emnlp-main.470/) · [Repositório](https://github.com/ryokamoi/wice).

Commit usado: `ddeb6c183665e2a20c5f03c5aa07f03888b9870f`, diretório `data/entailment_retrieval/claim`, arquivos `dev.jsonl` e `test.jsonl`. Origem e SHA-256 registrados em [audit](experimento/snapshots/wice-v4-audit.json).

A [licença dos autores](https://github.com/ryokamoi/wice/blob/ddeb6c183665e2a20c5f03c5aa07f03888b9870f/LICENSE.md) distingue:

- Anotações: [Open Data Commons Attribution License (ODC-BY) 1.0](https://opendatacommons.org/licenses/by/1-0/). Os arquivos derivados de rótulos mantêm essa atribuição; não são relicenciados como MIT.
- Textos: origem na Wikipédia e em sites arquivados no Common Crawl, sujeitos aos termos indicados pelos autores. Não redistribuímos os textos integrais aqui. O usuário deve observar esses termos ao obtê-los e utilizá-los.
- Código e saídas dos modelos dos autores em seus diretórios específicos: MIT. Não presumir que essa licença se aplica ao dataset inteiro.

Transformações das anotações: prefixo `wice:` no ID; `supported` mapeado a `ATTRIBUTABLE`; `partially_supported` e `not_supported` mapeados a `NOT_ATTRIBUTABLE`. O rótulo original é preservado. Três documentos de teste acima de 60 mil caracteres são excluídos antes da avaliação. O gabarito público inclui desenvolvimento e teste; não é um conjunto cego para quem lê este repositório.

As previsões, métricas, código experimental e gráficos deste repositório foram produzidos para o estudo de Fabricio Pedreira. Dependências de SDK continuam sob suas respectivas licenças; não há SDK nem credencial de fornecedor incorporados.

# Histórico relevante e limites

O artigo apresenta o estudo final, não um changelog. Este registro preserva o contexto metodológico necessário para não ocultar tentativas e correções.

- Pilotos anteriores com issues e composição de múltiplas perguntas não isolaram o efeito de Jev do contexto, do gabarito e da regra de decisão. Não sustentam os números deste artigo.
- Uma rodada anterior sobre AttributionBench teve erro na medição de repetibilidade: uma resposta foi replicada como se fossem chamadas repetidas. Além disso, sua cascata foi estimada por replay de respostas existentes. As alegações confirmatórias e de estabilidade daquela rodada foram retiradas.
- O diagnóstico posterior de repetição real usou casos já conhecidos; é exploratório, não um novo holdout cego. Não fornece latência observada da cascata do estudo atual.
- O teste WiCE aqui disponibilizado usa um protocolo próprio congelado e uma cascata realmente executada. Não apaga as limitações anteriores e não mede repetibilidade por si só.
- O [protocolo V3](https://github.com/fabriciopedreira/jev-decision-benchmark/blob/b02e95dfd47eea6aae17d0c0cc0bfcf78ee7a110/protocolo-v3.md) é mantido apenas para documentar a origem dos critérios herdados, inclusive o portão heurístico de custo 5×. Seus estados e intenções são históricos, não instruções para reinterpretar o WiCE.
- A [triagem RAGTruth](https://github.com/fabriciopedreira/jev-decision-benchmark/blob/b02e95dfd47eea6aae17d0c0cc0bfcf78ee7a110/experimento/resultados/ragtruth-triagem-v4.md) não foi executada como benchmark e não entra nas métricas.

Este pacote contém uma única implementação do estudo WiCE, não todos os pilotos anteriores. O código usado foi consolidado em `experimento/harness/`; o protocolo anterior e a triagem descartada ficam acessíveis apenas nos links históricos acima. O [protocolo original](protocolo-original.md) mantém seu texto e seu hash: referências a versões e estados anteriores nesse documento são registros históricos, não opções de execução. [Proveniência](proveniencia.md) distingue os originais da implementação reorganizada.

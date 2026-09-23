> Cópia para publicação. Consulte [proveniência](proveniencia.md). Estados de aprovação abaixo são históricos.

# Leitura operacional de latência e custo

Data: 23/09/2026. **Análise posterior à abertura do gabarito.** Não altera o [protocolo congelado](protocolo-original.md), os dados, os thresholds nem o veredito dos portões pré-definidos. Valores calculados do [resultado público saneado](../experimento/resultados/previsoes.jsonl) e conferidos com a [análise](../experimento/resultados/analise.json).

## Origem do mínimo de 5×

O mínimo de custo 5× foi uma **heurística editorial/experimental proposta por nós** na seção 8 do [protocolo V3](https://github.com/fabriciopedreira/jev-decision-benchmark/blob/b02e95dfd47eea6aae17d0c0cc0bfcf78ee7a110/protocolo-v3.md), para exigir que uma nova dependência compensasse sua complexidade. Não veio de um SLA, da operação de Fabricio, de um modelo econômico validado ou de uma exigência técnica do Jev. O protocolo WiCE herdou o número antes do teste. Foi um erro de comunicação apresentá-lo como se fosse um critério natural ou acordado.

Por integridade, o resultado formal permanece: Jev direto atingiu 4,41× de redução de custo calculado frente à Luna e **falhou no portão pré-registrado de 5×**. Isso não significa que 4,41× seja economicamente irrelevante ou que o modelo fracassou. Um julgamento de adoção precisaria do volume, custo de integração/monitoramento, valor da latência, custo de erro e requisito de estabilidade do fluxo real — nenhum deles foi medido neste estudo. A estabilidade também não foi testada. Não criar agora um novo corte conveniente para convertê-lo em aprovação.

## A velocidade não é uma nota de rodapé

| Condição | p50 | p95 | Relação com Luna no mesmo placar |
| --- | ---: | ---: | --- |
| Jev direto | 350 ms | 475 ms | 3,86× e 4,51× mais rápido |
| Luna baseline | 1.350 ms | 2.143 ms | referência |
| Cascata Jev → Luna, ponta a ponta | 367 ms | 1.898 ms | 3,68× e **1,13×** mais rápido |

Em 280/355 casos (78,9%), a cascata encerrou em Jev. Nos outros 75, pagou **duas chamadas sequenciais**: nesse subgrupo a cascata teve p50/p95 de 1.672/2.433 ms, contra 1.322/1.991 ms da Luna baseline nos mesmos casos. A média desse subgrupo foi 1.760 vs 1.435 ms (+325 ms). Em comparação pareada por caso, a cascata foi mais rápida em 297/355; a média geral caiu de 1.450 para 667 ms. Mas essa média e a mediana não escondem que o ganho de cauda ponta a ponta foi modesto. Esses tempos incluem chamada e adapter medidos no harness serial da execução; não são throughput sob carga, latência de um produto completo nem SLA de produção.

## Custo e cache

Com uso de tokens e preços públicos registrados, o custo/1.000 foi US$ 0,119 para Jev, US$ 0,523 para Luna e US$ 0,192 para a cascata; a última economizou 63,4% vs Luna nesta execução. A ordem intercalada das duas condições Luna fez uma condição aquecer o cache da outra em parte dos casos. Logo **63,4% não é uma previsão isolada de produção**. Numa sensibilidade que elimina tanto desconto quanto penalidade de escrita de cache e cobra entrada à tarifa normal para ambas, os totais recalculados são US$ 0,167196 para Luna e US$ 0,080512792 para a cascata, economia de 51,85%. A direção permanece favorável neste conjunto, mas custos de integração, observabilidade, revisão, falha e alteração de preços não foram incluídos. Também não se deve misturar custo calculado com fatura.

## Consequência arquitetural provisória

O estudo oferece um sinal forte de **eficiência para uma tarefa estreita de suporte entre afirmação e documento**: nesta amostra, Jev direto foi mais rápido e barato que Luna, com boa concordância relativa ao gabarito; a cascata preservou seus portões técnicos frente à Luna e trouxe ganho expressivo na mediana, menor no p95. Isso justifica investigar um piloto em sombra e sensibilidade operacional, não substituir o revisor humano nem declarar Jev superior a LLMs em geral.

Para uma decisão real, comparar explicitamente: taxa de falso suporte tolerável, qualidade por tipo de erro, p50 **e** p95 ponta a ponta, custo por decisão no mix de produção, estabilidade em repetições, dificuldade de integração e manutenção. Sem metas reais fornecidas por Fabricio, não converter esses eixos num score único ou inventar um novo mínimo universal. A [orientação oficial de avaliações da OpenAI](https://developers.openai.com/api/docs/guides/evaluation-best-practices) recomenda objetivos e conjuntos representativos do uso real; a [orientação de latência](https://developers.openai.com/api/docs/guides/latency-optimization) trata velocidade como eixo próprio de projeto. Essas fontes orientam método, não validam os números deste teste.

# Protocolo V4 — replicação externa e cascata executada

Status: **fase primária pronta para congelamento; nenhuma chamada paga da V4 realizada**  
Data: 23 de setembro de 2026

## Decisão que queremos informar

Para verificar afirmações contra evidências no fluxo editorial, devemos manter só regras, usar Jev como juiz direto, colocar Jev antes de uma LLM ou manter a LLM sem essa camada? A V4 testa se a indicação exploratória da V3 sobrevive a uma fonte independente e a uma cascata **executada de verdade**. Não testa se Jev é seguro para aprovar/publicar conteúdo automaticamente.

## Estimando e hipótese

Unidade: uma afirmação e o documento citado. `ATTRIBUTABLE` significa que **todas** as proposições factuais materiais da afirmação são sustentadas pelo documento; `NOT_ATTRIBUTABLE` inclui suporte parcial, ausência e contradição. A medida de qualidade é concordância com o rótulo humano publicado, não verdade absoluta nem segurança em produção.

Hipótese arquitetural: numa decisão semântica fechada que regra lexical não resolve com qualidade suficiente, Jev pode entregar um ganho operacional material. O ganho só tem valor se o risco de aceitar uma afirmação não sustentada não aumentar além da margem predefinida. Uma cascata só se justifica se encaminhar os casos incertos para a LLM **em execução sequencial real**, preservando qualidade e economizando custo/tempo no fluxo inteiro.

## Conjunto primário: WiCE

Usar o [WiCE original](https://github.com/ryokamoi/wice), nível `claim`, **não** o conjunto com recuperação *oracle*. É uma coleção independente da V3, de frases da Wikipédia e artigos citados, anotada por pessoas como `supported`, `partially_supported` ou `not_supported`. O [paper](https://aclanthology.org/2023.emnlp-main.470/) deriva `supported` quando todas as subafirmações têm suporte; por isso, a conversão binária da V4 é semanticamente direta.

- Commit da fonte: `ddeb6c183665e2a20c5f03c5aa07f03888b9870f`.
- Desenvolvimento: `dev.jsonl` (349 registros de origem); teste oficial: `test.jsonl` (358 registros de origem). Não usar `train` no resultado primário.
- Entrada comum aos julgadores: `claim`, `evidence[]` integral e, se necessário para resolver referências, `claim_context` marcado como **contexto da afirmação, não evidência**. A rubrica e a representação exata devem ser congeladas antes de qualquer chamada.
- Exclusões mecânicas, sem consultar acerto de modelo: afirmação/evidência vazia ou evidência acima de 60.000 caracteres. Pré-contagem: 348 casos de desenvolvimento e 355 de teste; no teste, 111 `supported` e 244 não totalmente sustentados. Nenhum título de página, texto integral da evidência ou afirmação coincide exatamente entre desenvolvimento e teste na checagem local.
- Grupo estatístico: `claim_title`; múltiplas afirmações sobre a mesma página não são independentes. Há 326 títulos no teste **antes** das exclusões e 323 depois.
- Nenhum *supporting_sentences* ou rótulo entra no estado. O texto dos documentos deve ser enviado **sem recuperação oracle** ou seleção orientada pelo gabarito. Se um provedor não aceitar a entrada integral, registrar falha operacional; não truncar só para ele.

O conjunto é público: não é possível assegurar ausência de exposição nos treinamentos. Além disso, apenas 355 casos de teste, com 244 negativos, provavelmente não resolvem margens de 1–2 pontos percentuais. Calcular a incerteza por grupo e aceitar explicitamente `inconclusivo`; não afrouxar o critério após ver o resultado.

## Transferência secundária: RAGTruth

O [RAGTruth](https://github.com/ParticleMedia/RAGTruth) tem respostas geradas sobre textos de QA, resumo e dados estruturados, com anotações humanas de trechos alucinados e `source_id` para agrupar seis respostas por contexto. Seu teste oficial tem 2.700 respostas/450 contextos: 900/150 por tarefa; 25 respostas QA têm `quality` diferente de `good`. Commit `c103204b9ce28d6bbad859304bf30de72b8ed8fe`.

Ele **não mede a mesma unidade** do WiCE: é uma resposta potencialmente com várias afirmações, não uma única frase. Não somar seu placar ao do WiCE nem usá-lo para resgatar um portão primário que falhar. Antes de executá-lo, definir uma conversão explícita das anotações por trecho, incluindo `implicit_true`, recusas e respostas sem afirmação verificável. Como uma reclassificação pode introduzir erro de gabarito, a primeira entrega será apenas um diagnóstico de viabilidade e uma auditoria manual cega; a etapa secundária permanece fechada até essa definição.

## Comparadores e fluxo

1. Código lexical: a regra da V3, com threshold escolhido **só no desenvolvimento WiCE**. Nenhum resultado V3 é usado para ajustá-la nesta fonte.
2. Jev: uma `Noul` binária com o mesmo estado/rubrica e o modelo/SDK registrados na execução. Corte direto fixo em 0,50.
3. `gpt-5.6-luna`, saída discreta, *reasoning* `none`: comparador barato da V3, não representante de todas as LLMs.
4. `gpt-5.6-terra`, saída discreta, *reasoning* padrão: comparador de qualidade mais forte, incluído porque a própria [TypeSafe](https://typesafe.ai/blog/introducing-system-one-models-and-jev) o usa como referência de inteligência em sua demonstração. Os resultados contra Luna e Terra permanecem separados.
5. Cascata real Jev → Luna: para cada caso, chamar Jev; somente se a probabilidade cair no intervalo aberto `(0,30; 0,70)` ou houver erro Jev, chamar Luna sequencialmente. A chamada Luna da cascata é distinta da chamada da baseline Luna em todos os casos. Os thresholds 0,30/0,70 vêm da V3 e **não são reajustados** no WiCE. Registrar eventos, latência ponta a ponta e tokens das duas pernas. Um replay de duas predições independentes não conta.

As quatro condições recebem o mesmo documento sem busca externa. Sem ferramentas, *retry* zero, timeout de 30 s, nenhuma resposta malformada convertida silenciosamente em classe. Falha direta conta como erro de qualidade; falha Jev na cascata escala; falha Luna na cascata deixa decisão não concluída e conta separadamente. Intercalar a ordem das baselines por semente fixa, serializando chamadas para que p50/p95 não sejam confundidos por concorrência desigual. Registrar versão retornada, parâmetros, preço público na data, uso de tokens e possíveis tokens em cache. Custo calculado a partir do uso reportado não é fatura.

## Análise e portões

Primário: macro F1 e falso `ATTRIBUTABLE` (denominador: rótulos `NOT_ATTRIBUTABLE`), com intervalos pareados por `claim_title`. Secundários: balanced accuracy, matriz de confusão, taxa de falha, custo/1.000 decisões, latências p50/p95, Brier/ECE apenas para Jev, sensibilidade à prevalência e erros por tipo `partially_supported`/`not_supported`. Estabilidade de classe/probabilidade requer chamadas repetidas distintas e não será inferida deste teste de uma chamada.

Manter os portões V3 como **política de decisão, sem pós-ajuste**: Jev direto precisa de limite inferior de Δmacro F1 ≥ −3 pp, limite superior de Δfalso suporte ≤ +2 pp, custo ≥5× menor, p95 ≥2× menor e falha ≤ +0,5 pp contra o comparador escolhido. A estabilidade fica **não avaliada** nesta rodada, portanto o portão completo de substituição direta não pode passar só pela V4. A cascata precisa de cobertura Jev ≥25%, economia calculada ≥30% e limites de qualidade contra Luna de −1 pp em macro F1 e +1 pp em falso suporte; se o tamanho não permitir esses limites, a decisão é `inconclusivo`, mesmo que a estimativa pontual pareça boa. Relatar Terra separadamente como checagem contra comparador fraco; não trocar retrospectivamente o comparador que favorece a tese.

Bootstrap pareado por grupo, 10.000 amostras e semente registrada; reportar IC bilateral descritivo e unilateral para cada portão. Um efeito agregado não substitui o resultado por tipo de erro, nem elimina a necessidade de teste em sombra com afirmações reais do workflow.

## Portões de integridade antes da execução

1. Script de preparação com commit e SHA-256 de cada arquivo de origem, manifesto sem rótulos, gabarito separado, exclusões justificadas e testes de duplicidade/grupo.
2. Rubrica e representação do estado revisadas em casos de desenvolvimento, incluindo anáforas, suporte parcial e documento longo. Nenhuma consulta ao acerto no teste.
3. Harness V4 com testes offline de chamadas distintas, sequência Jev→Luna, contabilização de falhas e custo/latência de duas pernas; não alterar o harness V3 congelado.
4. Congelar protocolo, código, estado, manifesto, gabarito e política em hashes **antes** da primeira chamada de teste. Registrar desvios/erros sem sobrescrever resultados.
5. Depois do teste, auditoria independente dos cálculos e dos erros antes de qualquer texto de artigo. Nenhuma publicação ou piloto automático decorre da V4.

Até cumprir os quatro primeiros pontos, **não há GO para chamada paga de teste**. Um piloto técnico de até três casos de desenvolvimento, posterior ao congelamento inicial, verifica apenas conectividade e contrato; seus resultados não ajustam rubrica, thresholds, seleção de casos ou portões. Qualquer correção de código exige novo congelamento datado antes do teste. Este arquivo não é um resultado nem uma promessa de que a V4 produzirá uma conclusão positiva.

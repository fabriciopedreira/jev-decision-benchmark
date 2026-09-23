> Cópia para publicação. Consulte [proveniência](proveniencia.md). Estados de aprovação abaixo são históricos.

# WiCE — resultados da cascata executada

Execução: 23/09/2026, 16:58:49–17:21:34 UTC (13:58:49–14:21:34 em São Paulo). [Protocolo prévio](protocolo-original.md); [freeze](../experimento/resultados/freeze-original.json); [abertura do gabarito](../experimento/resultados/abertura-original.json); [dados analíticos](../experimento/resultados/analise.json). **Pesquisa, não autorização de publicação ou automação.**

**Adendo de 23/09, posterior à execução:** a [revisão independente por agentes](revisao.md) confirmou integridade e apontou limites de extrapolação, interação de cache e ganho menor na cauda da cascata. A [leitura operacional](custo-e-tempo.md) esclarece o corte arbitrário de 5× sem alterar o resultado pré-registrado. As [evidências visuais](historico-e-limites.md) são capturas pós-execução, não prints ao vivo.

## Resultado em uma frase

No teste oficial WiCE, a cascata **executada** Jev → GPT-5.6 Luna passou os portões técnicos definidos antes desta comparação: concordância com o gabarito superior à Luna, menor falso suporte, 78,9% dos casos resolvidos por Jev e custo calculado 63,4% menor. Isso sustenta investigar um **piloto em sombra**, não alegar que Jev ou a cascata verificam afirmações com segurança no fluxo editorial. Jev direto **não** passou o portão de custo de 5× frente à Luna (4,41×), e sua estabilidade não foi medida.

## Método e integridade

- Tarefa: decidir se a evidência citada sustenta **todos** os elementos factuais materiais da afirmação. `partially_supported` e `not_supported` do [WiCE](https://github.com/ryokamoi/wice) viraram `NOT_ATTRIBUTABLE`; `supported` virou `ATTRIBUTABLE`. A [definição original](https://aclanthology.org/2023.emnlp-main.470/) exige suporte para todas as subafirmações no rótulo `supported`.
- Fonte: commit WiCE `ddeb6c183665e2a20c5f03c5aa07f03888b9870f`, nível `claim`, documento completo sem evidência *oracle*. Desenvolvimento: 348 de 349 casos; teste oficial: 355 de 358 após exclusões mecânicas de evidência >60.000 caracteres. No teste, 111 positivos e 244 negativos; 323 páginas de origem para agrupar a incerteza. Contexto da afirmação foi enviado apenas para resolver referências, explicitamente marcado como não-evidência.
- Baselines: regra lexical, com threshold `0,757575...` ajustado nos 348 casos de desenvolvimento; Jev `1.13.0`, uma `Noul` binária; GPT-5.6 Luna com `reasoning: none`; GPT-5.6 Terra com *reasoning* padrão, como comparador mais forte separado. A execução validou `typesafe-sdk==0.7.1`, `system-one-adapter==0.2.0` e `openai==3.16.2`. Ambos os modelos OpenAI usaram o mesmo contrato binário estruturado do adapter e `store=false`. Nenhuma busca ou ferramenta foi habilitada.
- A cascata chama Jev **primeiro**, então chama outra instância de Luna se a probabilidade cair no intervalo `(0,30; 0,70)` ou Jev falhar. Não reutiliza a resposta da Luna baseline. A execução seriada fez 355 chamadas Jev, 355 Luna baseline, 355 Terra baseline e 75 Luna após Jev: **1.140 chamadas externas no teste**. Todos os 785 IDs de resposta OpenAI foram distintos. Jev não expõe ID remoto no artefato; chamadas distintas são evidenciadas pelo fluxo e telemetria, não por ID do servidor. Houve zero falhas registradas. O piloto separado de três casos de desenvolvimento não entra no placar.
- Entradas, gabarito, protocolo, código, política e thresholds tiveram SHA-256 congelados antes da primeira chamada do teste. A rotina só abriu o gabarito depois de verificar 355 IDs únicos, hashes de entrada/resultado, modelos retornados, rotas e chamadas Luna distintas. O script de análise foi fechado e hasheado **antes da abertura do gabarito**, mas não estava no freeze inicial; os critérios analíticos já estavam no protocolo. Não houve ajuste após ver os rótulos.
- Bootstrap pareado por página citada, 10.000 reamostragens, semente `20260923`. Os intervalos unilaterais de 95% sustentam os portões; eles representam incerteza amostral neste conjunto público, não desempenho garantido em produção.

## Placar

| Condição | F1 macro | Falso `ATTRIBUTABLE` entre 244 negativos | Positivos perdidos entre 111 | Latência p50 / p95 | Custo calculado / 1.000 decisões |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regra lexical | 0,610 | 94 / 244 = 38,5% | 38 / 111 | 1 / 2 ms | US$ 0 em chamadas de modelo |
| Jev direto | 0,792 | 38 / 244 = 15,6% | 27 / 111 | 350 / 475 ms | US$ 0,119 |
| Luna sem *reasoning* | 0,729 | 66 / 244 = 27,0% | 24 / 111 | 1.350 / 2.143 ms | US$ 0,523 |
| Terra padrão | 0,786 | 51 / 244 = 20,9% | 19 / 111 | 1.509 / 2.891 ms | US$ 5,906 |
| Cascata real Jev → Luna | 0,802 | 45 / 244 = 18,4% | 19 / 111 | 367 / 1.898 ms | US$ 0,192 |

Custo total calculado nos 355 casos: Jev US$ 0,04208; Luna US$ 0,18577; Terra US$ 2,09650; cascata US$ 0,06798. A precificação usa tokens reportados e preços públicos de 23/09/2026: [TypeSafe](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) e [Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra). Inclui leitura de cache com desconto e escrita de cache a 1,25× da tarifa normal de entrada onde reportada; **não é conferência de fatura**. Não inclui engenharia, monitoramento, revisão humana ou custo de erro.

## Portões congelados

| Decisão | Evidência observada | Leitura |
| --- | --- | --- |
| Esta regra lexical basta? | Regra − Jev: −18,3 pp de F1 macro e +23,0 pp de falso suporte; os ICs ficam fora das margens | **Não** neste conjunto; outras soluções determinísticas não foram testadas |
| Jev direto preserva qualidade contra Luna? | ΔF1 +6,37 pp, limite inferior unilateral +1,97 pp (margem −3 pp); Δfalso suporte −11,48 pp, limite superior −7,32 pp (margem +2 pp) | **Sim** para concordância/riscos medidos |
| Jev direto paga nova dependência? | Custo Luna/Jev **4,41×**, abaixo do mínimo 5×; p95 4,51× mais rápido; zero falhas | **Não** no portão de custo; estabilidade não avaliada |
| Cascata contra Luna? | 280/355 casos (78,9%) só com Jev; economia calculada **63,4%** (mínimo 30%); ΔF1 +7,31 pp, limite inferior +4,16 pp (margem −1 pp); Δfalso suporte −8,61 pp, limite superior −5,20 pp (margem +1 pp) | **Passa os portões técnicos neste WiCE** |

Terra foi um controle de qualidade mais exigente, não o comparador primário escolhido retrospectivamente. Jev − Terra em F1 macro foi +0,69 pp, com intervalo unilateral inferior de −2,76 pp; em falso suporte foi −5,33 pp, com limite superior −1,74 pp. Cascata − Terra teve F1 +1,63 pp, limite inferior −1,63 pp, e falso suporte −2,46 pp, limite superior +1,17 pp. Portanto, **não** afirmar que a cascata passou as mesmas margens estritas frente à Terra: esses intervalos cruzam −1 pp e +1 pp, respectivamente.

## Trade-off e leitura qualitativa

Jev foi mais conservador que Luna: aceitou menos negativos (38 versus 66), mas também rejeitou mais positivos (27 versus 24). A cascata recuperou oito positivos, chegando aos 19 perdidos pela Terra, e ao mesmo tempo elevou os falsos suportes de 38 para 45 em relação a Jev sozinho. O resultado agregado não apaga esse custo de composição.

O principal teste de risco foi o suporte **parcial**: entre 213 casos com esse rótulo, Jev aceitou indevidamente 38; Luna, 64; Terra, 49; cascata, 44. Entre apenas 31 `not_supported`, os falsos suportes foram 0, 2, 2 e 1, respectivamente. Não tratar a última fração pequena como taxa estável de produção.

Jev teve Brier 0,124 e ECE de 10 faixas 0,065 neste conjunto. Aos thresholds 0,30/0,70, a decisão Jev isolada cobriu 78,9% dos casos e errou 11,1% dos aceitos. Probabilidade aparentemente útil para roteamento **não** é garantia individual de correção, e as taxas dependem da prevalência/complexidade do domínio.

Uma checagem exploratória de seis divergências escolhidas por hash fixo em estratos de erro não mudou os rótulos: por exemplo, uma afirmação sobre a participação de Harris na seleção vencedora foi marcada `partially_supported` e a evidência citada não menciona Harris pelo nome; Jev rejeitou, Luna e Terra aceitaram. Em outro caso marcado `supported`, o texto fala de aconselhamento e networking a mulheres fundadoras/investidoras, mas o salto para “advogar aumentar seu número” é interpretativo; Jev e Luna rejeitaram, Terra aceitou. São exemplos de por que concordância com anotação humana não substitui auditoria semântica, não prova de erro no gabarito. O [paper WiCE](https://aclanthology.org/2023.emnlp-main.470/) também relata concordância interanotadores imperfeita.

## Limites e decisão

- WiCE é público; exposição em treino dos modelos não pode ser descartada. Documentos citados da Wikipédia não reproduzem a distribuição de afirmações e fontes do processo editorial de Fabricio.
- O snapshot local inclui textos de fontes externas; antes de distribuir os dados brutos fora deste workspace, revisar os [termos/licenças indicados pelos autores do WiCE](https://github.com/ryokamoi/wice/blob/main/LICENSE.md). Scripts, hashes e estatísticas não dependem de republicar esses textos.
- 355 casos/323 grupos ainda limitam conclusões estreitas. Os intervalos foram respeitados, mas não há garantia de taxa de falso suporte em outro domínio ou prevalência.
- Uma execução por caso não mede repetibilidade da rota nem estabilidade após mudança de versão. O diagnóstico exploratório anterior mostrou que rota e classe final podem variar em repetições; esta execução única não elimina esse risco.
- Os aliases de modelo e o serviço podem mudar. Custos/latências pertencem à janela, ao SDK/adapter e aos preços registrados, não a toda a categoria “LLMs”. Luna sem *reasoning* é um comparador barato; Terra padrão oferece outra referência. Não declarar que Jev “vence LLMs”.
- Nenhum sistema escolheu fontes, fez fact-check na web, julgou credibilidade, editou ou publicou texto. Não há medição de perdas editoriais reais, eficiência de revisores, clientes ou resultados da Vector Labs.
- A revisão por agentes de IA foi concluída; ainda falta um teste em sombra com afirmações reais antes de extrapolar os resultados para uso operacional. O [RAGTruth](https://github.com/ParticleMedia/RAGTruth), pré-listado no protocolo como teste secundário de transferência, permanece **não executado** após [triagem do mapeamento](https://github.com/fabriciopedreira/jev-decision-benchmark/blob/b02e95dfd47eea6aae17d0c0cc0bfcf78ee7a110/experimento/resultados/ragtruth-triagem-v4.md); não foi omitido por resultado desfavorável.

**Decisão arquitetural provisória:** manter revisão humana e fonte original como autoridade; considerar um piloto em sombra da cascata para sugerir prioridade de checagem, nunca aprovar afirmações. O resultado distingue uma hipótese operacional defensável de uma promessa de “verificação segura”; não representa aprovação de produção.

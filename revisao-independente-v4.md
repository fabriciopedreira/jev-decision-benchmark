> Cópia para publicação. Consulte [proveniência](docs/proveniencia.md). Estados de aprovação abaixo são históricos.

# Revisão independente da V4 WiCE

23/09/2026. Três revisões auxiliares, somente leitura, examinaram método, integridade/aritmética e viabilidade de transferência ao RAGTruth. **São revisões por agentes de IA, não parecer humano externo ou auditoria certificada.** Seus achados foram conferidos contra os artefatos e fontes primárias; nenhum revisor editou o teste ou executou chamadas pagas.

## Veredito

A V4 é íntegra e informativa **para a decisão estreita de suporte de uma afirmação por um documento**. A cascata Jev → Luna passou os portões técnicos pré-definidos frente à Luna neste conjunto. Isso não demonstra avaliação geral de agentes, segurança para publicar automaticamente ou desempenho no fluxo editorial real. **Artigo e post seguem suspensos.**

## Achados que mudam a interpretação

1. **Escopo.** O [WiCE](https://aclanthology.org/2023.emnlp-main.470/) testa *entailment* de afirmação/documento. Seu [paper](https://aclanthology.org/2023.emnlp-main.470.pdf) descreve filtros que retiveram 16,3% dos candidatos e concordância interanotadores α=0,62 no desenvolvimento. A seleção favorece casos difíceis; suas prevalências, erros e economia não são estimativas do workflow editorial. O título atual da pauta não pode converter essa tarefa em prova de um “avaliador de agentes” geral.
2. **Velocidade e custo.** A [leitura operacional pós-teste](experimento/resultados/v4-latencia-e-decisao.md) distingue Jev direto (p95 4,51× menor que Luna) da cascata ponta a ponta (p95 só 1,13× menor). Os 75 encaminhados ficam mais lentos do que Luna direta no subgrupo. O custo calculado de 63,4% de economia foi influenciado pela ordem intercalada/cache; sem efeitos de cache, a sensibilidade indica 51,85%. Esses valores não representam fatura ou SLA.
3. **Portão 5×.** Nasceu como política proposta na [V3](protocolo-v3.md), sem SLA ou economia operacional de Fabricio. A falha formal de Jev direto em 5× continua registrada: 4,41×. Não é evidência de que 4,41× de economia de custo e 4,51× de ganho p95 sejam operacionalmente insuficientes. Não mover o corte depois do teste.
4. **Comparadores.** O adapter impôs o mesmo contrato binário aos modelos; isso reduz uma fonte de confusão, mas não testa uma LLM com prompt nativo especialmente otimizado. A regra lexical testada ficou atrás; não concluir que **qualquer** solução determinística é insuficiente.
5. **Integridade.** Revisão dos hashes de freeze/unseal/resultado, 355 casos, 280 rotas Jev, 75 rotas Luna e 785 IDs OpenAI distintos não encontrou erro que invalide a execução. A ausência de ID remoto Jev e de print contemporâneo permanece limite; os dados estruturados são a evidência primária. [Evidências visuais pós-execução](docs/historico-e-limites.md) estão rotuladas como tal, não como capturas da execução ao vivo.
6. **Transferência.** O [RAGTruth](https://aclanthology.org/2024.acl-long.585/) anota trechos de respostas inteiras, frequentemente multiafirmativas. A triagem está em [arquivo separado](experimento/resultados/ragtruth-triagem-v4.md). Não combinar seus números com WiCE nem usá-lo para resgatar portões primários.

## Recomendação

Manter o resultado formal da V4 e usar a matriz qualidade–risco–latência–custo–estabilidade para uma futura decisão de arquitetura, sem novo limiar universal. **Próxima evidência de maior valor editorial:** piloto em sombra com afirmações reais, públicas ou autorizadas, do processo que se quer melhorar, rotuladas de maneira cega por pessoas e revisadas em divergências, com Jev/Luna/cascata executados sem aprovar ou publicar nada. Antes disso, definir volume, SLA/valor da velocidade e custo de erro/integração. RAGTruth pode ser usado apenas como transferência exploratória depois de rubrica e auditoria de mapeamento congeladas.

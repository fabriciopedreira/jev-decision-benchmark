# Protocolo experimental v3 — Jev como `if` semântico

Status: **protocolo pronto para congelamento antes do teste confirmatório**  
Data: 22 de setembro de 2026

## 1. Pergunta que o experimento responde

> Em uma decisão semântica estreita que normalmente seria entregue a uma LLM generativa, Jev preserva a concordância com o benchmark e o perfil de risco de GPT-5.6 Luna, reduzindo materialmente custo, latência e variabilidade sob o mesmo estado, os mesmos critérios e o mesmo contrato de saída — o bastante para justificar um piloto editorial em sombra?

A intenção não é demonstrar que Jev “entende melhor” ou que substitui LLMs em geral. É verificar se o produto apresentado como especializado evita usar geração autoregressiva para executar um `if` semântico sem transferir o ganho de infraestrutura para pior concordância e maior risco no benchmark. Aprovação operacional exigiria o piloto em sombra e evidência do workflow real.

## 2. Tarefa

Decisão binária, fechada e cognitivamente delimitada de atribuição:

> A evidência fornecida sustenta **todo o conteúdo factual material** da afirmação?

Saída:

- `ATTRIBUTABLE`: todos os elementos factuais materiais estão diretamente sustentados ou decorrem claramente da evidência;
- `NOT_ATTRIBUTABLE`: ao menos um elemento material está ausente, contradito ou depende de conhecimento externo ou suposição não declarada.

O estado contém apenas `claim` e `evidence[]`. Pergunta, resposta original, URL e rótulo do benchmark não são enviados aos julgadores. A pergunta é única e executada com `Noul`, evitando a composição artificial de várias probabilidades que contaminou a v2.

## 3. O que Jev pode acrescentar ao código determinístico

Código continua responsável por regras exatas, datas, busca literal, cálculos, efeitos e roteamento. Jev entra somente no intervalo em que:

- a resposta não pode ser expressa de modo confiável por igualdade ou regra lexical;
- a taxonomia é fechada;
- a evidência necessária está no estado;
- uma pessoa consegue decidir rapidamente sem investigação aberta;
- a incerteza pode ser usada para escalar casos a outro modelo ou à revisão humana.

Jev não é determinístico: sua saída é probabilística, ainda que tipada. “System One Model” é a categoria apresentada pela TypeSafe; os detalhes públicos não permitem verificar de forma independente toda a arquitetura ou o treinamento. Repetibilidade, calibração e especialização útil são resultados a medir, não propriedades a presumir.

## 4. Dataset de autoria independente e separação do teste

Será usado o [AttributionBench](https://huggingface.co/datasets/osunlp/AttributionBench), Apache 2.0, cuja tarefa é decidir se uma afirmação é atribuível à evidência. A fonte não foi produzida pela TypeSafe, mas, por ser pública, não há como garantir que nunca tenha aparecido no treinamento dos modelos.

- desenvolvimento e escolha de política (split técnico `calibration`): `dev_all_subset_balanced.jsonl`, 1.198 registros antes das exclusões;
- teste confirmatório ainda não pontuado: `test_all_subset_balanced.jsonl`, 1.610 registros antes das exclusões;
- estresse fora de distribuição: `test_ood_balanced.jsonl`, 1.686 registros antes das exclusões;
- rótulos publicados: `attributable` e `not attributable`;
- fontes do teste primário: ExpertQA, Stanford-GenSearch, AttributedQA e LFQA;
- fontes do estresse OOD: BEGIN, AttrScore-GenSearch e HAGRID.

Exclusões são definidas só pela validade da entrada, antes de consultar os rótulos:

1. afirmação vazia;
2. lista de evidências vazia ou composta apenas por texto vazio;
3. evidência total superior a 60.000 caracteres, para evitar que o limite de contexto vire variável escondida.

O script registra cada exclusão e o hash SHA-256 dos arquivos de origem. O snapshot e o manifesto de entrada entregues aos julgadores não contêm gabarito; os rótulos ficam em arquivo separado, carregado somente depois que todas as previsões confirmatórias forem gravadas. Os thresholds são escolhidos apenas no desenvolvimento; o teste confirmatório é aberto uma vez, sem ajustes posteriores.

Durante o preflight, a baseline determinística chegou a ser pontuada no conjunto OOD antes do congelamento. Seu resultado é preservado, mas o OOD deixa de ser o holdout confirmatório. O conjunto `test_all_subset_balanced.jsonl`, que não foi consultado pela equipe durante o ajuste, passa a ser o teste primário. O OOD permanece como estresse secundário e nenhum parâmetro pode ser ajustado por seu resultado.

AttributionBench é um proxy público alinhado ao problema. A aplicação editorial em sombra, separada e sem alegação de acurácia, é que verificará se a taxonomia faz sentido no workflow real.

## 5. Condições comparadas

### A. Regra determinística

Baseline lexical que combina:

- correspondência literal normalizada da afirmação;
- cobertura dos tokens da afirmação pela evidência;
- veto quando um número presente na afirmação não aparece na evidência.

O threshold é escolhido na calibração por macro F1, com desempate por menor falso positivo e depois maior threshold. Ela responde se a nova dependência é desnecessária.

### B. Jev

- `typesafe-sdk==0.7.1`;
- modelo `jev-1.13.0`;
- uma única `Noul`;
- timeout de 30 segundos;
- zero retry;
- probabilidade nativa preservada;
- custo observado calculado com os tokens reportados e o preço público vigente na data da execução.

### C. LLM generativa

Comparador operacional recomendado — sem representar a classe inteira de LLMs:

- `gpt-5.6-luna`, via Responses API;
- reasoning `none`, sem ferramentas e `store=false`;
- Structured Outputs;
- `system-one-adapter==0.2.0`, com extensão mínima e registrada para enviar `reasoning={"effort":"none"}`;
- resposta **discreta** como condição primária;
- zero retry de transporte e de estrutura;
- registro integral de modelo retornado, tokens, latência, falha e parâmetros.

A saída discreta é primária porque representa o uso real de uma LLM como juiz e evita obrigá-la a inventar uma distribuição apenas para imitar Jev. Uma rodada LLM em modo `probabilities` pode ser feita como diagnóstico de calibração, mas não altera o comparador primário nem os portões de substituição.

O cutoff de classe do Jev fica congelado em 0,50 como política padrão para a comparação direta; a curva de sensibilidade mostrará o trade-off, mas não mudará o placar primário. A cascata usa thresholds assimétricos, escolhidos apenas no desenvolvimento em uma grade pré-declarada: `ATTRIBUTABLE` em 0,70/0,80/0,90/0,95 e `NOT_ATTRIBUTABLE` em 0,30/0,20/0,10/0,05. Isso reflete o maior custo de aceitar suporte inexistente.

O alias `gpt-5.6-luna` não apresenta snapshot datado na documentação consultada em 22 de setembro de 2026. Isso limita a reprodução futura; a data e o modelo retornado serão parte do resultado.

## 6. Execução justa

- mesma entrada e mesma definição semântica para Jev e LLM;
- inglês preservado, sem tradução do dataset;
- concorrência igual a 1 para a medição principal;
- ordem aleatória intercalada com seed `20260922`, executada pelo comando `run-paired` para que os dois provedores atravessem a mesma janela temporal;
- aquecimento separado e excluído da latência;
- zero retry: erro de serviço ou estrutura conta como falha operacional;
- na comparação direta, falha não autoriza `ATTRIBUTABLE`, conta como erro de qualidade e é reportada separadamente; na cascata, falha Jev segue para Luna e conserva custo e latência das duas tentativas;
- resultados nunca são sobrescritos;
- credenciais ficam fora dos artefatos;
- nenhuma chamada externa ocorre sem `--execute-external`.

A execução deve registrar início, fim, região observável quando disponível, versão do SDK, hash do protocolo, hash do snapshot e hash do manifesto.

## 7. Métricas

Qualidade primária, entendida como concordância com o rótulo publicado e não como verdade perfeita:

- macro F1 em todos os casos, contando falha operacional como erro;
- balanced accuracy;
- taxa de falso `ATTRIBUTABLE`, risco editorial principal;
- matriz de confusão.

Qualidade probabilística de Jev:

- Brier score;
- ECE em dez faixas;
- curva risco-cobertura.

Sistema:

- custo total e por mil decisões;
- latência ponta a ponta p50 e p95;
- taxa e tipo de falha;
- tokens de entrada e saída quando reportados.

Robustez:

- 96 casos OOD, 16 por combinação fonte × rótulo, repetidos para Jev e GPT-5.6 Luna;
- cinco repetições idênticas por condição;
- concordância de classe para ambas; amplitude da probabilidade apenas para Jev, pois a condição Luna primária é discreta;
- a estabilidade mede o mesmo modelo; não corrige qualidade.

Incerteza:

- bootstrap pareado por pergunta/resposta de origem, estratificado por fonte, para não tratar múltiplas afirmações do mesmo conteúdo como observações independentes;
- 10.000 reamostragens, seed `20260922`;
- intervalos unilaterais de 95% para os portões de não inferioridade e intervalos bilaterais de 95% para descrição;
- análise de potência depois de observar a correlação pareada com Luna no desenvolvimento e antes de congelar; se 748 grupos do teste não puderem distinguir a margem de risco, o resultado permitido será `inconclusivo`, sem relaxar o portão.

## 8. Portões recomendados antes de abrir o teste

Estes valores são uma política experimental escolhida para esta pauta, não propriedades universais dos modelos. A margem de qualidade é pequena porque falso suporte pode contaminar uma publicação; os ganhos de 5× em custo e 2× em p95 exigem que a nova dependência pague sua complexidade operacional. A cascata exige cobertura e economia materiais para evitar uma camada que quase sempre encaminha o caso. O relatório mostrará também sensibilidade em torno desses valores, sem mudar a decisão binária pré-definida.

### Substituição direta

Todos precisam ser verdadeiros:

1. limite inferior do IC 95% de `macro F1 Jev − LLM` ≥ **−3 pontos percentuais**;
2. limite superior do IC 95% da diferença de falso positivo ≤ **+2 pontos percentuais**;
3. custo por mil decisões do Jev ao menos **5× menor**;
4. p95 do Jev ao menos **2× menor**;
5. falha operacional do Jev não superior à da LLM em mais de **0,5 ponto percentual**.
6. proporção de casos com a mesma classe nas cinco repetições não inferior à Luna por mais de **5 pontos percentuais**.

### Cascata Jev → LLM

O threshold de confiança é escolhido apenas na calibração. No teste, a cascata só passa se:

1. Jev resolver pelo menos **25%** dos casos sem LLM;
2. custo cair pelo menos **30%** contra LLM em todos os casos;
3. macro F1 ficar a até **1 ponto percentual** da LLM;
4. falso positivo ficar a até **1 ponto percentual** da LLM.

Os dois portões de qualidade da cascata usam os respectivos limites unilaterais de 95%, não apenas estimativas pontuais. O mesmo vale para concluir que a regra determinística está dentro das margens do melhor modelo.

### Regra determinística

Se a regra ficar dentro de 3 pontos de macro F1 e 2 pontos de falso positivo do melhor modelo, a conclusão preferida é manter código e não adicionar Jev.

## 9. Interpretação pré-declarada

- **Código basta:** a regra passa o portão determinístico.
- **Jev substitui a LLM:** Jev passa todos os portões de substituição direta.
- **Jev filtra a LLM:** substituição direta falha, mas a cascata passa.
- **LLM continua necessária:** Jev falha qualidade ou risco e a cascata não compensa.
- **Nenhuma conclusão:** falha de infraestrutura, mudança de modelo ou desvio de protocolo invalida a comparação.

Resultado negativo será mantido. Não haverá ajuste de prompt, threshold, exclusão ou taxonomia após a abertura do teste.

## 10. Aplicação editorial em sombra

Depois do benchmark, uma pequena amostra de afirmações e evidências deste workspace pode validar ergonomia e tipos de erro. Ela não será somada ao benchmark, não produzirá alegação de acurácia e não aprovará, removerá ou publicará conteúdo automaticamente.

## 11. Decisão necessária para congelar

Antes das chamadas pagas, é preciso aprovar:

1. os portões numéricos da seção 8;
2. `gpt-5.6-luna` discreto como comparador LLM primário;
3. a obtenção de uma credencial de API da OpenAI separada da assinatura do ChatGPT.

Sem os três itens, o dataset e o harness podem ser validados offline, mas o teste confirmatório permanece fechado.

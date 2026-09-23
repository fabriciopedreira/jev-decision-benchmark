# Proveniência e saneamento

O [manifesto de exportação](../manifesto-exportacao.json) separa os hashes da distribuição atual (`files_sha256`) dos artefatos históricos preservados (`preserved_artifacts`). Protocolo original, gabarito, manifesto de casos, freeze, metadados, abertura e análise continuam idênticos em conteúdo, mesmo com caminhos mais claros. O JSONL público saneado também permanece idêntico.

## Código consolidado e código original

Há um único `experimento/harness/`: componentes usados pelo estudo, sem as rotinas antigas de replay, repetição e datasets que não participam dele. A dependência não usada de scikit-learn foi retirada. Nomes e imports foram simplificados; prompts, critérios, limiares, modelos e cálculos foram conservados. Relatórios receberam links atualizados; suas versões anteriores também estão no Git.

Isso muda o hash da implementação. **O código atual não é apresentado como cópia byte a byte do código executado em 23/09/2026.** Os originais e o primeiro manifesto público estão no [commit histórico](https://github.com/fabriciopedreira/jev-decision-benchmark/tree/b02e95dfd47eea6aae17d0c0cc0bfcf78ee7a110). Os links do artigo fixados nesse commit continuam válidos.

O recálculo offline usa as previsões publicadas e compara toda a análise. Para chamar os serviços novamente, o comando `freeze` cria uma identidade da implementação atual; `run` rejeita o freeze antigo. Isso não altera nem substitui os registros da execução original. Os identificadores históricos `lexical-v3` e `not_evaluable_without_v4_stability` permanecem nos registros e cálculos para não mudar o significado/formato das evidências; não indicam implementações alternativas disponíveis.

Na revisão da consolidação, foram corrigidas duas proteções para novas execuções: criação dos diretórios de resultado/metadados antes de acessar credenciais ou clientes, e rejeição de probabilidades não finitas ou fora de `[0,1]` como erro operacional. Removido também um cálculo redundante de custos que a análise já descartava. Essas alterações estão cobertas por testes; não reescrevem respostas, custos, latências nem hashes da execução histórica.

## O que foi retirado das previsões

O JSONL público mantém IDs dos casos, hashes das entradas, ordem, classes, probabilidades, rotas, latências, status e contagens de tokens. Payloads completos, prompts, textos de terceiros e demais metadados dos fornecedores foram removidos por lista explícita de campos permitidos. IDs das respostas OpenAI foram substituídos pelo SHA-256 de cada ID; isso preserva a verificação de duplicidade sem divulgar identificadores operacionais. O pequeno campo `raw` remanescente contém somente esses hashes e contagens de escrita de cache, necessárias para o cálculo original.

O arquivo público **não é o resultado bruto intacto**. Por isso, seu hash é diferente. Freeze/unseal históricos referem-se ao original não distribuído; não devem ser usados para fingir uma abertura inédita do JSONL saneado. O recálculo público verifica o manifesto de exportação e reproduz a análise a partir dos campos conservados. Quando os textos são baixados da origem, seus hashes também podem ser comparados ao freeze original.

## O que se consegue e o que não se consegue conferir

- Conferir matrizes, F1, percentis, custo, cache, rotas, agrupamento e intervalos a partir dos registros publicados.
- Conferir 355 IDs de caso e 785 hashes distintos de respostas OpenAI (355 Luna de controle, 355 Terra e 75 Luna na cascata).
- Conferir a identidade do protocolo e dos dados; o código original pode ser auditado no commit histórico. A identidade da implementação consolidada é distinta e verificável.
- Não autenticar junto aos fornecedores que cada chamada ocorreu: hashes e logs locais não são recibos assinados ou auditoria externa. Jev não forneceu ID remoto por chamada neste registro.
- Não reconstruir a íntegra dos payloads retirados. Uma nova execução é evidência nova, não substitui ou “corrige” retrospectivamente a original.
- Não provar segurança de produção, throughput, estabilidade nem desempenho fora da tarefa medida.

As figuras foram geradas depois da execução a partir dos resultados. Não são screenshots contemporâneos das chamadas. A revisão independente referida nos documentos foi realizada por agentes de IA, não por especialistas humanos certificados.

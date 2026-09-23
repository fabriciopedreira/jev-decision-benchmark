# Proveniência e saneamento

O [manifesto de exportação](../manifesto-exportacao.json) registra hashes dos originais e das cópias públicas. O código do teste primário, seu protocolo, gabarito, manifesto, freeze, metadados, unseal e análise são preservados byte a byte quando listados em `exact_copies_sha256`. Relatórios com links adaptados são identificados em `transformed_documents`.

## O que foi retirado das previsões

O JSONL público mantém IDs dos casos, hashes das entradas, ordem, classes, probabilidades, rotas, latências, status e contagens de tokens. Payloads completos, prompts, textos de terceiros e demais metadados dos fornecedores foram removidos por lista explícita de campos permitidos. IDs das respostas OpenAI foram substituídos pelo SHA-256 de cada ID; isso preserva a verificação de duplicidade sem divulgar identificadores operacionais. O pequeno campo `raw` remanescente contém somente esses hashes e contagens de escrita de cache, necessárias para o cálculo original.

O arquivo público **não é o resultado bruto intacto**. Por isso, seu hash é diferente. Freeze/unseal históricos referem-se ao original não distribuído; não devem ser usados para fingir uma abertura inédita do JSONL saneado. O recálculo público verifica o manifesto de exportação e reproduz a análise a partir dos campos conservados. Quando os textos são baixados da origem, seus hashes também podem ser comparados ao freeze original.

## O que se consegue e o que não se consegue conferir

- Conferir matrizes, F1, percentis, custo, cache, rotas, agrupamento e intervalos a partir dos registros publicados.
- Conferir 355 IDs de caso e 785 hashes distintos de respostas OpenAI (355 Luna de controle, 355 Terra e 75 Luna na cascata).
- Conferir a identidade do código e do protocolo usados, e a reconstrução dos inputs oficiais.
- Não autenticar junto aos fornecedores que cada chamada ocorreu: hashes e logs locais não são recibos assinados ou auditoria externa. Jev não forneceu ID remoto por chamada neste registro.
- Não reconstruir a íntegra dos payloads retirados. Uma nova execução é evidência nova, não substitui ou “corrige” retrospectivamente a original.
- Não provar segurança de produção, throughput, estabilidade nem desempenho fora da tarefa medida.

As figuras foram geradas depois da execução a partir dos resultados. Não são screenshots contemporâneos das chamadas. A revisão independente referida nos documentos foi realizada por agentes de IA, não por especialistas humanos certificados.

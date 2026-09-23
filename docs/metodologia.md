# Metodologia e fluxo executado

## Pergunta e referência

Entrada: afirmação, contexto para resolver referências e documento de evidência. Contexto não é evidência adicional. Saída: `ATTRIBUTABLE` somente quando todas as afirmações materiais têm suporte; `partially_supported` e `not_supported` do WiCE viram `NOT_ATTRIBUTABLE`.

O gabarito é a anotação publicada pelos autores do WiCE, não uma resposta de LLM criada para este estudo. O conjunto é público, tem ambiguidades e pode ter aparecido no treinamento dos modelos. Concordância com ele não é garantia de verdade ou segurança.

## Cascata na prática

1. Jev recebe a afirmação e o documento, com os critérios binários do estudo.
2. Uma regra no código interpreta a probabilidade estimada de suporte completo: `p <= 0.30` encerra com não; `p >= 0.70` encerra com sim.
3. Para `0.30 < p < 0.70`, ou falha de Jev, uma **nova chamada** é feita a Luna.
4. Luna recebe a mesma entrada e os mesmos critérios; não recebe a resposta de Jev para revisar. A saída de Luna substitui a de Jev como resposta final. Não há votação ou média.

Por exemplo, 0,92 encerra em Jev e 0,55 aciona Luna. São exemplos ilustrativos. Os limiares pertencem ao experimento e não garantem uma frequência de acerto igual à probabilidade reportada.

O controle Luna sozinha é uma chamada separada da Luna acionada na cascata. No sistema em avaliação não se chama a baseline para depois aproveitar sua resposta. Veja [decide_cascade e run_case](../experimento/harness/runner.py).

## Condições e instrumentação

- Regra lexical treinada em desenvolvimento; Jev `jev-1.13.0`; Luna `gpt-5.6-luna`, reasoning `none`; Terra `gpt-5.6-terra`, reasoning padrão como controle adicional.
- Mesmo contrato e critérios, via SDK/adapter; sem ferramentas ou busca de outras fontes. Isso não equivale a um prompt nativo otimizado separadamente para cada LLM.
- Ordem de blocos intercalada por caso, seed `20260923`, concorrência 1, timeout 30 s e retries 0. Cascata medida de ponta a ponta com relógio monotônico; nos encaminhados entram duas chamadas.
- 355 dos 358 casos oficiais; três exclusões por evidência acima de 60 mil caracteres; 111 positivos e 244 negativos, em 323 grupos de página.
- Protocolo, entradas, gabarito, manifesto, implementação e limites congelados antes do teste. O código de análise foi hasheado antes da abertura do gabarito, mas não estava no freeze inicial. Os hashes são evidência local, não pré-registro público com carimbo independente.
- Bootstrap pareado por grupo de página, 10 mil reamostragens. Métricas, limites de não inferioridade e resultados formais no [protocolo](protocolo-original.md) e [relatório](resultados.md).

## Cuidados de interpretação

O portão de custo 5× para Jev direto foi uma heurística prévia, não exigência universal. Seu resultado de 4,41× não o torna economicamente inútil; o critério não foi reescrito depois. A cascata teve critérios próprios. Não alegar estabilidade: só houve uma execução por caso nesta rodada.

Cache, ordem e infraestrutura afetam custo e tempo. A conta sem cache é uma sensibilidade posterior, não nova observação. A regra lexical não representa todo código determinístico possível, Luna não representa todas as LLMs e WiCE não representa a operação de Fabricio ou de clientes.

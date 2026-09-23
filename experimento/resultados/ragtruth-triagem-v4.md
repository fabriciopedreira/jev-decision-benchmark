# RAGTruth — triagem de transferência secundária da V4

23/09/2026. **Triagem, não benchmark executado.** Fonte: [paper dos autores](https://aclanthology.org/2024.acl-long.585/) e arquivos oficiais [respostas](https://raw.githubusercontent.com/ParticleMedia/RAGTruth/c103204b9ce28d6bbad859304bf30de72b8ed8fe/dataset/response.jsonl) e [fontes](https://raw.githubusercontent.com/ParticleMedia/RAGTruth/c103204b9ce28d6bbad859304bf30de72b8ed8fe/dataset/source_info.jsonl), commit `c103204b9ce28d6bbad859304bf30de72b8ed8fe`. Os dados brutos não foram copiados para a pasta da pauta. SHA-256 informado para `response.jsonl`: `e4c2e4ac24fff676d8984cc61c35d791612fadc58015335d97dd632375e18073`; para `source_info.jsonl`: `0dffc26ea9f3c1c3d7c7e8336b56ef1646e3cec876edffcca3c9c624d12d578b`. Os hashes devem ser novamente conferidos se houver execução local.

## Por que o mapeamento não é automático

O WiCE pergunta se **uma afirmação** é inteiramente sustentada por uma evidência. O RAGTruth anota **trechos alucinados em uma resposta inteira** de QA, resumo ou geração a partir de dados. O paper também avalia detecção no nível da resposta (presença de qualquer alucinação); isso torna plausível uma transferência binária, mas muda a unidade e a distribuição.

Na contagem do teste oficial pinado: 2.700 respostas/450 `source_id`; 2.675 com `quality=good` e 25 com outra qualidade. Entre as boas, 943 têm ao menos um trecho anotado e 1.732 têm zero. Por tarefa (`good` / zero trecho / algum trecho): Data2txt 900/321/579; QA 875/715/160; Summary 900/696/204. Pelo menos quatro respostas exatamente “Unable to answer based on given passages.” aparecem como boas e sem trecho: zero trecho **não** significa necessariamente uma decisão factual atribuível.

## Regra candidata — ainda não congelada

- Um ou mais trechos alucinados, inclusive `implicit_true` (verdadeiro, mas sem suporte na fonte) e `due_to_null`, sugere `NOT_ATTRIBUTABLE` para a resposta inteira, caso ela contenha afirmações verificáveis.
- Zero trecho só pode ser candidato a `ATTRIBUTABLE` após tratar recusas, vazios e respostas sem proposição verificável. Não converter ausência de anotação em prova automática de suporte.
- Excluir do placar principal as 25 respostas de qualidade não boa; reportar quantas e por quê, sem selecionar por acerto do modelo.
- Separar QA, resumo e Data2txt; agrupar incerteza por `source_id`; não agregar ao WiCE nem chamar o placar de replicação do mesmo estimando.

## Portão antes de chamadas pagas

Fixar uma rubrica de inclusão e mapeamento **usando apenas desenvolvimento**, auditar uma amostra estratificada e cega às predições com revisões independentes/adjudicação, registrar ambiguidades e só depois congelar código, hashes e protocolo de transferência. A revisão é semântica: as anotações humanas originais existem, mas a conversão para a nova pergunta ainda precisa ser validada. Contagens e exemplos do teste já foram examinados nesta triagem; por isso, mesmo se executado depois, seria **transferência exploratória prospectiva**, não confirmação cega da V4. Não usar o teste para adaptar a rubrica. Se essa etapa não for viável, **não executar RAGTruth** e priorizar um piloto em sombra com exemplos do uso real. Nenhuma chamada Jev/OpenAI foi feita nesta triagem.

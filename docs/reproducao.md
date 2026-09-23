# Guia de reprodução

Execute os comandos na raiz deste repositório. Use Python 3.11 ou superior; a validação de exportação usa apenas a biblioteca padrão. Não coloque resultados novos nos arquivos de referência.

## 1. Recalcular os resultados existentes: sem rede, sem chaves, sem cobrança

```bash
python3 scripts/reproduzir.py
```

Verifica hashes do pacote, IDs, rotas, chamadas distintas por hash, matriz de confusão, F1, p50/p95, custos, breakdowns e todos os intervalos da análise original. Inclui 10 mil reamostragens e pode levar alguns minutos. A saída deve indicar `status: OK`, 355 casos, 323 grupos e 280/75 rotas. Recalcular não é executar os modelos novamente nem provar autenticidade do fornecedor.

## 2. Reconstruir entradas oficiais: acesso à rede, sem API de modelos

Leia [THIRD_PARTY](../THIRD_PARTY.md) antes de obter os textos. A origem é fixada num commit, não em `main`.

```bash
python3 scripts/obter_dados.py
python3 -m unittest discover -s experimento/tests -p '*v4.py' -v
cd experimento
python3 -m harness_v4.runner validate
cd ..
```

O download compara os hashes de inputs, labels e manifesto ao freeze original. Não sobrescreve um snapshot existente divergente. Os dez testes do harness/análise incluem uma checagem que exige esse snapshot; os demais usam fixtures locais e não chamam modelos. O download não acrescenta os textos ao Git.

## 3. Gerar os gráficos novamente

Em ambiente virtual, instale `matplotlib==3.11.2` (versão usada nas figuras) e execute:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install matplotlib==3.11.2
.venv/bin/python experimento/gerar_graficos.py
```

Saída em `outputs/graficos/`. Os valores vêm da análise conferida e das previsões saneadas. Fontes e metadados gráficos podem variar entre ambientes; a equivalência esperada é dos valores e da composição, não necessariamente dos bytes do PNG/SVG. Os arquivos distribuídos em `assets/` são as figuras finais do artigo.

## 4. Nova execução: requer chaves e gera cobrança

**Não executado automaticamente por nenhum comando anterior.** Esta etapa é opcional. Os modelos, SDKs e tarifas podem mudar ou deixar de estar disponíveis. Se uma versão fixada não existir, interrompa e documente a mudança como outro experimento; não use um alias substituto silenciosamente.

```bash
.venv/bin/python -m pip install -r experimento/requirements.txt
cp .env.example .env
```

Edite `.env` localmente com `TYPESAFE_API_KEY` e `OPENAI_API_KEY`. A assinatura de um aplicativo não substitui credenciais de API. As chaves nunca devem entrar em commit, issue ou log público. O próprio harness valida as versões dos SDKs antes de chamar os serviços.

Depois de reconstruir as entradas, crie **um novo congelamento** e novos arquivos de resultado:

```bash
mkdir -p outputs/nova-execucao
cd experimento
../.venv/bin/python -m harness_v4.runner freeze --output ../outputs/nova-execucao/freeze.json
../.venv/bin/python -m harness_v4.runner run \
  --split test \
  --freeze ../outputs/nova-execucao/freeze.json \
  --env-file ../.env \
  --output ../outputs/nova-execucao/resultados.jsonl \
  --metadata-output ../outputs/nova-execucao/metadados.json \
  --execute-external
../.venv/bin/python analisar_wice_v4.py \
  --results ../outputs/nova-execucao/resultados.jsonl \
  --metadata ../outputs/nova-execucao/metadados.json \
  --freeze ../outputs/nova-execucao/freeze.json \
  --unseal-output ../outputs/nova-execucao/abertura.json \
  --output ../outputs/nova-execucao/analise.json
cd ..
```

A chamada `run` custa dinheiro. O desenho faz 355 chamadas Jev, 355 Luna de controle, 355 Terra de controle e até 355 Luna na cascata. O histórico teve 75 encaminhamentos, mas uma execução nova pode diferir. Não há teto financeiro global automatizado; configure limites no fornecedor se necessário. Sem a flag `--execute-external`, o harness bloqueia a execução.

O script de análise foi preservado para comparabilidade, inclusive tarifas históricas de 23/09/2026. Seu custo em uma nova execução é calculado com essas tarifas: **não** tratá-lo como custo atual/fatura. Preços atuais podem ser avaliados em análise separada e identificada. Os novos resultados contêm payloads de fornecedores: não publique `outputs/` sem nova revisão de dados e credenciais.

Nova execução sobre um benchmark cujo gabarito já foi publicado não é um novo teste cego. Ela verifica a reprodução do procedimento sob as condições registradas, com variação possível de serviço, modelo, cache, rede e tempo. O protocolo original permanece intacto.

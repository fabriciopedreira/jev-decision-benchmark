# Jev entre o if e a LLM

Experimento de Fabricio Pedreira sobre uma decisão de arquitetura: **vale colocar um modelo especializado antes de uma LLM para reduzir custo e espera, sem degradar a qualidade da decisão?**

A tarefa é delimitada: verificar se um documento sustenta **todas** as afirmações materiais de uma frase. Não é avaliar um agente inteiro, determinar a verdade universal de uma frase nem autorizar publicação automática.

## Comece aqui

- [Metodologia e funcionamento da cascata](docs/metodologia.md)
- [Reproduzir cálculos ou executar novamente](docs/reproducao.md)
- [Resultados completos](experimento/resultados/v4-wice-resultados.md)
- [Latência, custo e efeitos de cache](experimento/resultados/v4-latencia-e-decisao.md)
- [Protocolo original congelado](protocolo-v4.md)
- [Revisão por agentes de IA](revisao-independente-v4.md) — não é parecer humano externo.
- [Proveniência, saneamento e limites da evidência](docs/proveniencia.md)
- [Histórico metodológico e correções](docs/historico-e-limites.md)
- [Verificações da distribuição](docs/validacao.md)

## Resultado delimitado

355 casos do teste oficial WiCE, após três exclusões por documentos acima de 60 mil caracteres. Execução serial em 23/09/2026; uma execução por caso.

| Caminho | Aceitou sem suporte completo /244 | Rejeitou com suporte completo /111 | p50 / p95 | US$/1.000 decisões |
|---|---:|---:|---:|---:|
| Regra baseada em palavras | 94 | 38 | 1 / 2 ms | 0 em API |
| Jev sozinho | 38 | 27 | 350 / 475 ms | 0,119 |
| Luna sozinha | 66 | 24 | 1.350 / 2.143 ms | 0,523 |
| Jev, com Luna nos casos incertos | 45 | 19 | 367 / 1.898 ms | 0,192 |

Jev resolveu 280 casos sem a segunda chamada; 75 exigiram Luna. A cascata passou os critérios técnicos definidos contra Luna **neste conjunto**. A economia calculada foi 63,4%, ou 51,85% na análise posterior sem efeitos de cache. O ganho no p95 foi modesto; os casos encaminhados esperaram duas chamadas. Terra foi controle adicional, e os mesmos critérios de não inferioridade não foram demonstrados contra ele.

Os custos são calculados a partir de tokens e preços registrados, não fatura. Não incluem integração, operação ou custo dos erros. Não há evidência aqui de segurança em produção, estabilidade em repetições ou generalização a outras tarefas.

## Recalcular sem API, sem credenciais e sem baixar os textos

Python 3.11 ou superior. O caminho abaixo usa somente biblioteca padrão:

```bash
git clone https://github.com/fabriciopedreira/jev-decision-benchmark.git
cd jev-decision-benchmark
python3 scripts/reproduzir.py
```

O recálculo lê previsões saneadas, rótulos e grupos, audita as rotas e compara **toda a análise**, inclusive bootstrap por página com 10 mil reamostragens, com a referência publicada. Não chama modelos e não mede novamente latência: recalcula percentis das medições registradas.

Para nova execução, aquisição dos dados, dependências de API e gráficos, siga o [guia de reprodução](docs/reproducao.md). Chamadas externas custam dinheiro e exigem ativação explícita. Disponibilidade dos modelos/pacotes e comportamento dos serviços podem mudar; não substituímos versões silenciosamente.

## Licenças e dados

Código próprio e documentação: [MIT](LICENSE). Anotações derivadas do WiCE mantêm os termos e atribuição próprios, descritos em [THIRD_PARTY.md](THIRD_PARTY.md). Os textos completos de terceiros não são redistribuídos: o script os obtém do commit oficial utilizado e verifica os hashes. `.env` e payloads completos de fornecedores não fazem parte deste repositório.

Uma cópia dos registros permite conferir cálculos; não constitui certificação independente de que as chamadas ocorreram. Veja as limitações em [proveniência](docs/proveniencia.md).

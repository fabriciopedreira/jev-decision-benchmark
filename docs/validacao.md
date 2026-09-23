# Validação da distribuição

23/09/2026. Verificação automatizada local, não auditoria humana nem nova medição dos modelos.

Uma cópia limpa do pacote, sem caches, credenciais ou entradas baixadas, foi testada com Python 3.12.14:

| Verificação | Resultado |
|---|---|
| `python3 scripts/obter_dados.py` | Reconstrução da fonte oficial, hashes de entradas/rótulos/manifesto e auditoria idênticos ao registro original |
| `python3 scripts/reproduzir.py` | Toda a análise conferida, inclusive 10.000 reamostragens; 355 casos, 323 grupos, rotas 280/75 e 785 hashes distintos de IDs OpenAI |
| `python3 -m unittest discover -s experimento/tests -p '*v4.py' -v` | 10 testes passaram |
| `python3 -m harness_v4.runner validate` dentro de `experimento/` | 348 casos de calibração, 355 de teste; identidade de implementação, protocolo e dados preservada |
| `python experimento/gerar_graficos.py` | Figuras regeneradas com Matplotlib 3.11.2; execução gráfica em ambiente Python 3.14 |

Nenhuma API de modelo foi chamada. Só a reconstrução dos dados acessou a fonte pública. Os tempos publicados continuam sendo os da execução original; não foram medidos novamente.

A distribuição foi inspecionada quanto a links locais quebrados, caminhos privados, formatos comuns de chaves/tokens e IDs operacionais não saneados: nenhum encontrado. Essa checagem complementa — não substitui — a exportação por lista explícita de campos e arquivos. Credenciais, prompts completos e textos integrais de terceiros não foram incluídos.

Os testes exercitam a política da cascata e os cálculos; não provam que modelos atuais produzirão as mesmas respostas. Consulte [reprodução](reproducao.md) e [proveniência](proveniencia.md).

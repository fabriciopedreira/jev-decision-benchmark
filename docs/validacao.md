# Validação independente da distribuição

23/09/2026. Duas revisões por agentes de IA, separadas da implementação: uma de código/integridade e outra de execução em cópia limpa. Não é auditoria humana nem nova avaliação dos modelos ao vivo.

**Parecer:** o pacote instala e reproduz localmente os resultados publicados. Os problemas encontrados foram corrigidos e rechecados; não restou bloqueio no escopo testado.

## Execução em ambiente limpo

Sem credenciais, caches, ambientes anteriores ou entradas previamente baixadas. Python 3.12.14, com instalação nova de `typesafe-sdk==0.7.1`, `openai==3.16.2`, `system-one-adapter==0.2.0` e `matplotlib==3.11.2`.

| Verificação | Resultado |
|---|---|
| `python scripts/reproduzir.py` | Toda a análise idêntica: 355 casos, 323 grupos, rotas 280/75, 785 hashes distintos e 10.000 reamostragens |
| `python scripts/obter_dados.py` | Fonte oficial reconstruída; hashes de entradas, rótulos e manifesto conferidos |
| `python -m unittest discover -s experimento/tests -v` | 15 testes passaram |
| `python -m harness.runner validate` dentro de `experimento/` | 348 casos de calibração e 355 de teste válidos |
| `python -m harness.runner freeze --output ../outputs/novo-freeze.json` | Novo congelamento criado e validado; reutilizar o original no código reorganizado é corretamente rejeitado |
| Instalação das dependências fixadas + `pip check` | Instalação concluída; nenhuma incompatibilidade reportada |
| `python experimento/gerar_graficos.py` | Quatro figuras em PNG e SVG geradas |
| `python scripts/verificar_sdks.py` após instalar dependências | Três clientes reais passaram, com transporte HTTP simulado e rede bloqueada |

O teste dos SDKs usa credenciais fictícias e ambiente limpo. Verifica serialização das requisições, parsing de respostas sintéticas, JSON Schema, `store=false`, Luna com `reasoning=none`, Terra sem override, modelo retornado, rótulos e tokens/cache. O script está incluído para que essa checagem seja reproduzível.

**Não verificado:** credenciais reais, autenticação, disponibilidade dos endpoints/modelos, respostas ao vivo ou novos tempos/custos. Nenhuma API de modelo foi chamada. Download de dados e instalação de pacotes acessaram suas fontes públicas.

## Achados e correções

- A pasta de metadados não era criada previamente: poderia falhar só depois das chamadas. Agora ambos os diretórios são preparados antes das credenciais/clientes, e destinos iguais são rejeitados.
- Probabilidades não finitas ou fora de `[0,1]` podiam virar decisão: agora são erro operacional e acionam o encaminhamento previsto.
- Havia uma precificação redundante, com uma tarifa OpenAI única, descartada pela análise final: foi removida. O cálculo por modelo continua na análise e reproduz todos os resultados.

A primeira revisão comparou o código ao commit histórico, conferiu preservação de prompts/critérios e confirmou as correções com testes e recálculo integral. Não foram alterados dados, respostas, limiares ou resultados do estudo.

## Identidade e alcance

Implementação consolidada auditada: `ac41e5fc0a6395e66a4d7ce37659768e8c239f65ee0f0739a5c1ae55ed59bdc0`. Esse hash cobre preparação, dependências, analisador e módulos do harness; não é o hash da execução histórica. O [manifesto](../manifesto-exportacao.json) cobre também os documentos e scripts da distribuição atual.

As verificações não demonstram segurança em produção nem resultados iguais numa nova chamada. O recálculo de percentis usa latências registradas, não uma nova medição. Consulte [reprodução](reproducao.md) e [proveniência](proveniencia.md).

"""Gera gráficos editoriais a partir da análise congelada, sem chamadas de API."""
from pathlib import Path
import hashlib
import json
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

TOPIC = Path(__file__).resolve().parent.parent
ASSETS = TOPIC / 'outputs/graficos'
ASSETS.mkdir(parents=True, exist_ok=True)
ANALYSIS = TOPIC / 'experimento/resultados/analise.json'
data = json.loads(ANALYSIS.read_text())

BG, INK, MUTED, GRID = '#F7F8FA', '#182535', '#536275', '#DDE3E8'
COLORS = {'rule': '#8A959F', 'jev': '#087F79', 'luna': '#7A6A9D', 'cascade': '#2764CE'}
NAMES = {'rule': 'Regra em palavras', 'jev': 'Jev sozinho', 'luna': 'Luna sozinha', 'cascade': 'Jev + Luna\nse necessário'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 16, 'text.color': INK,
                     'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': INK})

def br(value, decimals=0):
    return f'{value:,.{decimals}f}'.replace(',', '_').replace('.', ',').replace('_', '.')

def frame(title, subtitle, height=11):
    fig = plt.figure(figsize=(16, height), dpi=100, facecolor=BG)
    fig.text(.06, .945, title, fontsize=32, weight='bold', va='top')
    fig.text(.06, .888, subtitle, fontsize=19, color=MUTED, va='top')
    return fig

def bars(fig, rect, keys, values, max_value, heading, unit, labels):
    ax = fig.add_axes(rect, facecolor=BG)
    yy = list(range(len(keys)))
    ax.barh(yy, values, color=[COLORS[k] for k in keys], height=.5, zorder=3)
    ax.set_yticks(yy, [NAMES[k] for k in keys], fontsize=18)
    ax.invert_yaxis()
    ax.set_xlim(0, max_value)
    for i, (value, label) in enumerate(zip(values, labels)):
        ax.text(value + max_value*.018, i, label, va='center', fontsize=18, weight='bold')
    ax.set_title(heading, loc='left', fontsize=20, weight='bold', pad=20)
    ax.set_xlabel(unit, fontsize=15, labelpad=8)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    ax.tick_params(axis='both', length=0, pad=9)
    for spine in ax.spines.values(): spine.set_visible(False)
    return ax

def save(fig, name, note):
    fig.text(.06, .045, note, fontsize=13, color=MUTED, va='bottom')
    fig.savefig(ASSETS / f'{name}.png', facecolor=fig.get_facecolor(), dpi=100)
    fig.savefig(ASSETS / f'{name}.svg', facecolor=fig.get_facecolor())
    plt.close(fig)

# Capa tipográfica vetorial: sem números promocionais ou falsa captura de interface.
fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=INK)
fig.text(.08, .84, 'UM EXPERIMENTO DE ARQUITETURA', color='#88D8CE', fontsize=22, weight='bold')
fig.text(.08, .64, 'Jev entre o if e a LLM', color='white', fontsize=59, weight='bold')
fig.text(.08, .55, 'Qualidade, tempo e custo de uma decisão', color='#D3DDE7', fontsize=29)
for x, title, sub, color in [(.08, 'Código', 'Regras exatas', '#718294'),
                             (.365, 'Jev', 'Decisões delimitadas', '#087F79'),
                             (.65, 'LLM', 'Geração e síntese', '#7A6A9D')]:
    fig.add_artist(FancyBboxPatch((x, .245), .265, .19, transform=fig.transFigure,
                   boxstyle='round,pad=0.008,rounding_size=0.015', facecolor=color, edgecolor='none'))
    fig.text(x+.024, .355, title, fontsize=35, color='white', weight='bold')
    fig.text(x+.024, .287, sub, fontsize=21, color='white')
fig.text(.08, .13, 'Fabricio Pedreira', fontsize=23, color='white')
fig.text(.08, .087, 'CTO · Engenharia de IA aplicada', fontsize=18, color='#AFC1D3')
fig.savefig(ASSETS / 'jev-capa.png', dpi=100, facecolor=INK)
fig.savefig(ASSETS / 'jev-capa.svg', facecolor=INK)
plt.close(fig)

keys = ['rule', 'jev', 'luna', 'cascade']
fps = [data['metrics'][k]['confusion']['NOT_ATTRIBUTABLE']['ATTRIBUTABLE'] for k in keys]
fns = [data['metrics'][k]['confusion']['ATTRIBUTABLE']['NOT_ATTRIBUTABLE'] for k in keys]
fig = frame('Economizar só interessa se a decisão for boa', 'Dois erros diferentes. Em ambos, menos é melhor.', 13.6)
bars(fig, [.24, .53, .63, .25], keys, fps, 112,
     'Aceitou sem suporte completo · 244 casos', 'Número de afirmações', [f'{v} de 244' for v in fps])
bars(fig, [.24, .15, .63, .25], keys, fns, 48,
     'Rejeitou apesar do suporte completo · 111 casos', 'Número de afirmações', [f'{v} de 111' for v in fns])
save(fig, 'jev-qualidade', 'Fonte: experimento de Fabricio Pedreira · WiCE, 355 casos · 23/09/2026\nGráfico derivado dos resultados. Concordância com o gabarito; não prova de segurança em produção.')

keys = ['jev', 'luna', 'cascade']
p50 = [round(data['metrics'][k]['latency_ms']['p50']) for k in keys]
p95 = [round(data['metrics'][k]['latency_ms']['p95']) for k in keys]
fig = frame('A maioria responde rápido. A cauda muda a conta.', 'Tempo do caminho completo · barras com a mesma escala', 12.4)
bars(fig, [.22, .54, .65, .25], keys, p50, 2700,
     'p50 · tempo mediano', 'Milissegundos (ms)', [f'{br(v)} ms' for v in p50])
bars(fig, [.22, .17, .65, .25], keys, p95, 2700,
     'p95 · tempo dentro do qual 95% terminaram', 'Milissegundos (ms)', [f'{br(v)} ms' for v in p95])
save(fig, 'jev-tempo', 'Fonte: experimento de Fabricio Pedreira · WiCE, 355 casos · 23/09/2026\nRegra em palavras: p50 de 1 ms e p95 de 2 ms. Medição serial; não é SLA de produção.')

values = [data['costs'][k]['calculated_per_1000_usd'] for k in keys]
saving = 100*(1-data['costs']['cascade']['calculated_total_usd']/data['costs']['luna']['calculated_total_usd'])
rows = [json.loads(line) for line in (TOPIC/'experimento/resultados/previsoes.jsonl').read_text().splitlines() if line]
def no_cache_luna(pred):
    u = pred['usage']
    return (u.get('input_tokens_total',u['input_tokens'])*.20 + u.get('output_tokens_total',u['output_tokens'])*1.20)/1e6
lc = sum(no_cache_luna(r['luna_baseline']) for r in rows)
cc = data['costs']['jev']['calculated_total_usd'] + sum(no_cache_luna(r['cascade']['luna']) for r in rows if r['cascade']['luna'])
saving_no_cache = 100*(1-cc/lc)
assert round(saving_no_cache,2) == 51.85
fig = frame('Menos chamadas à LLM, menor custo calculado', 'Dólares por 1.000 decisões · mesma tarefa e mesmas entradas', 10.4)
bars(fig, [.22, .43, .65, .33], keys, values, .69, '', 'US$ por 1.000 decisões', [f'US$ {br(v,3)}' for v in values])
fig.text(.09, .265, f'−{br(saving,1)}%', fontsize=41, weight='bold', color=COLORS['cascade'])
fig.text(.09, .208, 'Jev + Luna se necessário, vs. Luna\nna execução observada', fontsize=17)
fig.text(.53, .265, f'−{br(saving_no_cache,2)}%', fontsize=41, weight='bold', color=COLORS['cascade'])
fig.text(.53, .208, 'Na simulação de preço\nsem efeitos de cache', fontsize=17)
save(fig, 'jev-custo', 'Fonte: tokens reportados e preços de 23/09/2026 · WiCE, 355 casos\nCusto de API calculado, não fatura. Exclui integração, operação, revisão e custo dos erros.')


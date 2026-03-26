import csv
import json
import os
from collections import defaultdict

ARQUIVO_COMPARATIVO = "outputs/comparativo_precos.csv"
ARQUIVO_DASHBOARD = "outputs/dashboard.html"

AJUSTE_MAXIMO_CICLO = 5.0


# =========================================================
# UTILITÁRIOS
# =========================================================

def to_float(valor):
    try:
        if valor is None:
            return None
        texto = str(valor).strip()
        if not texto:
            return None
        return float(texto)
    except Exception:
        return None


def brl(v):
    if v is None:
        return "N/A"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def pct(v):
    if v is None:
        return "N/A"
    return f"{v:.2f}%"


def status_cor(status):
    mapa = {
        "CRITICO": "#dc2626",
        "ALERTA": "#f59e0b",
        "ACEITAVEL": "#65a30d",
        "ALINHADO": "#15803d",
        "ABAIXO_MANTECORP": "#2563eb",
        "SEM_DADO": "#6b7280",
    }
    return mapa.get(status, "#6b7280")


def esc(v):
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# =========================================================
# REGRAS DE NEGÓCIO
# =========================================================

def score_status(status):
    mapa = {
        "CRITICO": 4,
        "ALERTA": 3,
        "ACEITAVEL": 2,
        "ALINHADO": 1,
        "ABAIXO_MANTECORP": 2,
        "SEM_DADO": 0,
    }
    return mapa.get(status, 0)


def score_gravidade_magnitude(premium_pct):
    if premium_pct is None:
        return 0.0
    return abs(premium_pct) / 10.0


def classificar_faixa(premium_pct):
    if premium_pct is None:
        return "SEM_DADO"
    if premium_pct < 0:
        return "ABAIXO_MANTECORP"
    if premium_pct <= 3:
        return "ALINHADO"
    if premium_pct <= 7:
        return "ACEITAVEL"
    if premium_pct <= 10:
        return "ALERTA"
    return "CRITICO"


def recomendar_acao_hibrida(premium_pct):
    """
    Estratégia híbrida:
    - acima de 10%: reduzir para aproximar da faixa de alerta/aceitável, mas limitado a 5%
    - 7 a 10%: reduzir seletivamente
    - 3 a 7%: sustentar/monitorar
    - abaixo de 0: oportunidade de aumento, mas comedida
    """
    if premium_pct is None:
        return {
            "acao": "Sem recomendação",
            "ajuste_pct": 0.0,
            "direcao": "neutro",
            "racional": "Sem base suficiente para sugerir ação."
        }

    if premium_pct > 10:
        ajuste = min(AJUSTE_MAXIMO_CICLO, max(2.0, premium_pct - 7.0))
        return {
            "acao": f"Reduzir preço em {ajuste:.1f}%",
            "ajuste_pct": -ajuste,
            "direcao": "reduzir",
            "racional": "Prêmio acima da faixa crítica. Recomendação de correção imediata, preservando a lógica híbrida."
        }

    if premium_pct > 7:
        ajuste = min(AJUSTE_MAXIMO_CICLO, max(1.0, premium_pct - 5.0))
        return {
            "acao": f"Reduzir preço em {ajuste:.1f}%",
            "ajuste_pct": -ajuste,
            "direcao": "reduzir",
            "racional": "Prêmio em alerta. Recomendação de ajuste com urgência, porém de forma seletiva."
        }

    if premium_pct > 3:
        return {
            "acao": "Sustentar e monitorar",
            "ajuste_pct": 0.0,
            "direcao": "manter",
            "racional": "Prêmio dentro da faixa aceitável. Não há urgência de ajuste."
        }

    if premium_pct >= 0:
        return {
            "acao": "Manter posicionamento",
            "ajuste_pct": 0.0,
            "direcao": "manter",
            "racional": "Posicionamento competitivo saudável."
        }

    oportunidade = min(AJUSTE_MAXIMO_CICLO, max(1.0, abs(premium_pct) * 0.7))
    return {
        "acao": f"Elevar preço em {oportunidade:.1f}%",
        "ajuste_pct": oportunidade,
        "direcao": "aumentar",
        "racional": "GreenCare abaixo da Mantecorp. Há oportunidade comercial e possível subprecificação."
    }


def score_prioridade(item):
    peso_total = item.get("peso_total") or 0.0
    status_score = score_status(item.get("status"))
    magnitude = score_gravidade_magnitude(item.get("premium_pct"))
    return round((status_score * 2.0 + magnitude) * (1.0 + peso_total * 10.0), 3)


# =========================================================
# LEITURA
# =========================================================

def carregar_comparativo():
    if not os.path.exists(ARQUIVO_COMPARATIVO):
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_COMPARATIVO}")

    rows = []
    with open(ARQUIVO_COMPARATIVO, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["premium_pct"] = to_float(r.get("premium_pct"))
            r["green_price"] = to_float(r.get("green_price"))
            r["mantecorp_price"] = to_float(r.get("mantecorp_price"))
            r["delta_abs"] = to_float(r.get("delta_abs"))
            r["peso_sku"] = to_float(r.get("peso_sku"))
            r["peso_rede"] = to_float(r.get("peso_rede"))
            r["peso_total"] = to_float(r.get("peso_total"))
            r["status"] = r.get("status", "SEM_DADO")
            r["recomendacao"] = recomendar_acao_hibrida(r["premium_pct"])
            r["prioridade_score"] = score_prioridade(r)
            rows.append(r)
    return rows


# =========================================================
# AGREGAÇÕES
# =========================================================

def gerar_kpis(rows):
    premiums = [r["premium_pct"] for r in rows if r["premium_pct"] is not None]
    premio_medio = sum(premiums) / len(premiums) if premiums else None
    maior_premium = max(premiums) if premiums else None
    menor_premium = min(premiums) if premiums else None

    qtd_criticos = sum(1 for r in rows if r["status"] == "CRITICO")
    qtd_alerta = sum(1 for r in rows if r["status"] == "ALERTA")
    qtd_aceitavel = sum(1 for r in rows if r["status"] == "ACEITAVEL")
    qtd_alinhado = sum(1 for r in rows if r["status"] == "ALINHADO")
    qtd_abaixo = sum(1 for r in rows if r["status"] == "ABAIXO_MANTECORP")

    total_peso = sum(r.get("peso_total") or 0 for r in rows)
    total_score = sum(score_status(r["status"]) * (r.get("peso_total") or 0) for r in rows)
    score_executivo = (total_score / total_peso) if total_peso > 0 else 0
    score_executivo = round(score_executivo, 2)

    criticidade_texto = "Controlado"
    if score_executivo >= 3.2:
        criticidade_texto = "Muito crítico"
    elif score_executivo >= 2.7:
        criticidade_texto = "Crítico"
    elif score_executivo >= 2.0:
        criticidade_texto = "Atenção"
    elif score_executivo >= 1.2:
        criticidade_texto = "Moderado"

    return {
        "premio_medio": premio_medio,
        "maior_premium": maior_premium,
        "menor_premium": menor_premium,
        "qtd_criticos": qtd_criticos,
        "qtd_alerta": qtd_alerta,
        "qtd_aceitavel": qtd_aceitavel,
        "qtd_alinhado": qtd_alinhado,
        "qtd_abaixo": qtd_abaixo,
        "qtd_total": len(rows),
        "score_executivo": score_executivo,
        "criticidade_texto": criticidade_texto,
    }


def resumo_por_rede(rows):
    grupos = defaultdict(list)
    for r in rows:
        grupos[r["rede"]].append(r)

    saida = []
    for rede, itens in grupos.items():
        premiums = [x["premium_pct"] for x in itens if x["premium_pct"] is not None]
        premium_medio = sum(premiums) / len(premiums) if premiums else None

        score_criticidade = sum(x["prioridade_score"] for x in itens)
        qtd_criticos = sum(1 for x in itens if x["status"] == "CRITICO")
        qtd_alertas = sum(1 for x in itens if x["status"] == "ALERTA")

        saida.append({
            "rede": rede,
            "premium_medio": premium_medio,
            "score_criticidade": round(score_criticidade, 2),
            "qtd_criticos": qtd_criticos,
            "qtd_alertas": qtd_alertas,
            "qtd_itens": len(itens),
        })

    saida.sort(key=lambda x: x["score_criticidade"], reverse=True)
    return saida


def resumo_por_sku(rows):
    grupos = defaultdict(list)
    for r in rows:
        grupos[r["sku"]].append(r)

    saida = []
    for sku, itens in grupos.items():
        premiums = [x["premium_pct"] for x in itens if x["premium_pct"] is not None]
        premium_medio = sum(premiums) / len(premiums) if premiums else None

        gc_vals = [x["green_price"] for x in itens if x["green_price"] is not None]
        mt_vals = [x["mantecorp_price"] for x in itens if x["mantecorp_price"] is not None]

        gc_medio = sum(gc_vals) / len(gc_vals) if gc_vals else None
        mt_medio = sum(mt_vals) / len(mt_vals) if mt_vals else None

        peso_sku = itens[0].get("peso_sku") or 0

        saida.append({
            "sku": sku,
            "premium_medio": premium_medio,
            "green_medio": gc_medio,
            "mantecorp_medio": mt_medio,
            "peso_sku": peso_sku,
            "qtd_itens": len(itens),
        })

    saida.sort(key=lambda x: x["peso_sku"], reverse=True)
    return saida


def heatmap(rows):
    mapa = defaultdict(dict)
    for r in rows:
        mapa[r["rede"]][r["sku"]] = r["status"]

    redes = list(mapa.keys())
    skus = list({r["sku"] for r in rows})
    skus.sort()
    return redes, skus, mapa


def top_problemas(rows, n=5):
    itens = [r for r in rows if r["status"] in {"CRITICO", "ALERTA"}]
    itens.sort(key=lambda x: x["prioridade_score"], reverse=True)
    return itens[:n]


def top_oportunidades(rows, n=5):
    itens = [r for r in rows if r["premium_pct"] is not None and r["premium_pct"] < 0]
    itens.sort(key=lambda x: x["prioridade_score"], reverse=True)
    return itens[:n]


def gerar_insights(rows, kpis, ranking_redes, resumo_skus):
    insights = []

    if kpis["premio_medio"] is not None:
        if kpis["premio_medio"] > 10:
            insights.append(
                f"A GreenCare encerra o ciclo com prêmio médio de {pct(kpis['premio_medio'])}, acima da faixa crítica definida."
            )
        elif kpis["premio_medio"] > 7:
            insights.append(
                f"A GreenCare encerra o ciclo com prêmio médio de {pct(kpis['premio_medio'])}, em zona de alerta."
            )
        elif kpis["premio_medio"] > 3:
            insights.append(
                f"A GreenCare encerra o ciclo com prêmio médio de {pct(kpis['premio_medio'])}, dentro da faixa aceitável."
            )
        elif kpis["premio_medio"] >= 0:
            insights.append(
                f"A GreenCare encerra o ciclo em faixa competitiva saudável, com prêmio médio de {pct(kpis['premio_medio'])}."
            )
        else:
            insights.append(
                f"A GreenCare está abaixo da Mantecorp em média, indicando oportunidade de recomposição seletiva de preço."
            )

    if ranking_redes:
        pior_rede = ranking_redes[0]
        insights.append(
            f"A rede mais crítica no recorte atual é {pior_rede['rede']}, com premium médio de {pct(pior_rede['premium_medio'])} e score ponderado de {pior_rede['score_criticidade']:.2f}."
        )

    if resumo_skus:
        sku_mais_pesado = resumo_skus[0]
        insights.append(
            f"O SKU de maior peso estratégico no modelo é {sku_mais_pesado['sku']}, o que exige disciplina adicional na leitura de preço."
        )

    probs = top_problemas(rows, n=1)
    if probs:
        p = probs[0]
        insights.append(
            f"O principal foco de ação do ciclo é {p['rede']} no SKU {p['sku']}, onde a recomendação é: {p['recomendacao']['acao'].lower()}."
        )

    ops = top_oportunidades(rows, n=1)
    if ops:
        o = ops[0]
        insights.append(
            f"A principal oportunidade está em {o['rede']} no SKU {o['sku']}, onde GreenCare está abaixo da Mantecorp em {pct(o['premium_pct'])}."
        )

    return insights


# =========================================================
# HTML HELPERS
# =========================================================

def html_cards_kpi(kpis):
    cards = [
        ("Score Executivo", f"{kpis['score_executivo']}", kpis["criticidade_texto"]),
        ("Prêmio médio GreenCare", pct(kpis["premio_medio"]), "Média do ciclo"),
        ("Maior premium", pct(kpis["maior_premium"]), "Pico observado"),
        ("Menor premium", pct(kpis["menor_premium"]), "Menor relação"),
        ("Comparações", str(kpis["qtd_total"]), "Itens comparados"),
        ("Críticos", str(kpis["qtd_criticos"]), "Faixa > 10%"),
        ("Alertas", str(kpis["qtd_alerta"]), "Faixa 7% a 10%"),
        ("Abaixo da Mantecorp", str(kpis["qtd_abaixo"]), "Oportunidade / subpreço"),
    ]

    html = []
    for titulo, valor, sub in cards:
        html.append(f"""
        <div class="kpi-card">
            <div class="kpi-title">{esc(titulo)}</div>
            <div class="kpi-value">{esc(valor)}</div>
            <div class="kpi-sub">{esc(sub)}</div>
        </div>
        """)
    return "\n".join(html)


def html_ranking_redes(ranking):
    linhas = []
    for idx, item in enumerate(ranking, start=1):
        linhas.append(f"""
        <tr>
            <td>{idx}</td>
            <td>{esc(item["rede"])}</td>
            <td>{pct(item["premium_medio"])}</td>
            <td>{item["qtd_criticos"]}</td>
            <td>{item["qtd_alertas"]}</td>
            <td>{item["score_criticidade"]:.2f}</td>
        </tr>
        """)
    return "\n".join(linhas)


def html_tabela_detalhada(rows):
    linhas = []
    for r in rows:
        cor = status_cor(r["status"])
        rec = r["recomendacao"]["acao"]
        linhas.append(f"""
        <tr>
            <td>{esc(r["rede"])}</td>
            <td>{esc(r["sku"])}</td>
            <td>{brl(r["green_price"])}</td>
            <td>{brl(r["mantecorp_price"])}</td>
            <td>{brl(r["delta_abs"])}</td>
            <td>{pct(r["premium_pct"])}</td>
            <td><span class="badge" style="background:{cor};">{esc(r["status"])}</span></td>
            <td>{esc(rec)}</td>
            <td>{r["prioridade_score"]:.2f}</td>
        </tr>
        """)
    return "\n".join(linhas)


def html_problemas(problemas):
    if not problemas:
        return "<li>Nenhum problema relevante identificado.</li>"

    itens = []
    for p in problemas:
        itens.append(
            f"<li><b>{esc(p['rede'])}</b> | {esc(p['sku'])} | {pct(p['premium_pct'])} | ação: {esc(p['recomendacao']['acao'])}</li>"
        )
    return "\n".join(itens)


def html_oportunidades(itens):
    if not itens:
        return "<li>Nenhuma oportunidade relevante identificada.</li>"

    html = []
    for o in itens:
        html.append(
            f"<li><b>{esc(o['rede'])}</b> | {esc(o['sku'])} | {pct(o['premium_pct'])} | ação: {esc(o['recomendacao']['acao'])}</li>"
        )
    return "\n".join(html)


def html_heatmap(redes, skus, mapa):
    linhas = []

    for rede in redes:
        linha = f"<tr><td class='sticky-col'><b>{esc(rede)}</b></td>"
        for sku in skus:
            status = mapa[rede].get(sku, "-")
            cor = status_cor(status)
            linha += f"<td style='background:{cor}; color:white;'>{esc(status)}</td>"
        linha += "</tr>"
        linhas.append(linha)

    cabecalho_skus = "".join([f"<th>{esc(s)}</th>" for s in skus])

    return f"""
    <div class="table-wrap">
        <table class="heatmap-table">
            <thead>
                <tr>
                    <th class="sticky-col">Rede</th>
                    {cabecalho_skus}
                </tr>
            </thead>
            <tbody>
                {"".join(linhas)}
            </tbody>
        </table>
    </div>
    """


# =========================================================
# DASHBOARD HTML
# =========================================================

def gerar_dashboard_html(rows):
    kpis = gerar_kpis(rows)
    ranking = resumo_por_rede(rows)
    skus = resumo_por_sku(rows)
    problemas = top_problemas(rows, n=5)
    oportunidades = top_oportunidades(rows, n=5)
    insights = gerar_insights(rows, kpis, ranking, skus)
    redes_heat, skus_heat, mapa_heat = heatmap(rows)

    labels_sku = [x["sku"] for x in skus]
    green_sku = [round(x["green_medio"], 2) if x["green_medio"] is not None else 0 for x in skus]
    mt_sku = [round(x["mantecorp_medio"], 2) if x["mantecorp_medio"] is not None else 0 for x in skus]
    premium_sku = [round(x["premium_medio"], 2) if x["premium_medio"] is not None else 0 for x in skus]

    labels_status = ["ALINHADO", "ACEITAVEL", "ALERTA", "CRITICO", "ABAIXO_MANTECORP"]
    valores_status = [
        kpis["qtd_alinhado"],
        kpis["qtd_aceitavel"],
        kpis["qtd_alerta"],
        kpis["qtd_criticos"],
        kpis["qtd_abaixo"],
    ]

    labels_rede = [x["rede"] for x in ranking]
    criticidade_rede = [round(x["score_criticidade"], 2) for x in ranking]
    premium_rede = [round(x["premium_medio"], 2) if x["premium_medio"] is not None else 0 for x in ranking]

    insights_html = "".join([f"<li>{esc(i)}</li>" for i in insights])

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Dashboard Executivo de Pricing</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #0b1220;
            --bg-soft: #111827;
            --card: rgba(255,255,255,0.06);
            --card-strong: rgba(255,255,255,0.10);
            --line: rgba(255,255,255,0.10);
            --text: #e5e7eb;
            --muted: #9ca3af;
            --accent: #0f766e;
            --accent-2: #14b8a6;
            --shadow: 0 20px 40px rgba(0,0,0,0.28);
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background:
                radial-gradient(circle at top left, rgba(20,184,166,0.12), transparent 25%),
                radial-gradient(circle at top right, rgba(59,130,246,0.10), transparent 20%),
                linear-gradient(180deg, #0b1220 0%, #0f172a 100%);
            color: var(--text);
        }}

        .container {{
            max-width: 1500px;
            margin: 0 auto;
            padding: 28px;
        }}

        .hero {{
            position: relative;
            overflow: hidden;
            border-radius: 24px;
            padding: 28px 32px;
            background: linear-gradient(135deg, #064e3b 0%, #0f766e 45%, #0f172a 100%);
            box-shadow: var(--shadow);
            margin-bottom: 24px;
            border: 1px solid rgba(255,255,255,0.08);
        }}

        .hero h1 {{
            margin: 0 0 8px 0;
            font-size: 40px;
            letter-spacing: -0.02em;
        }}

        .hero p {{
            margin: 0;
            color: rgba(255,255,255,0.85);
            font-size: 16px;
        }}

        .hero-badges {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 18px;
        }}

        .hero-badge {{
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(255,255,255,0.10);
            color: white;
            font-size: 13px;
            border: 1px solid rgba(255,255,255,0.10);
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .kpi-card {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(10px);
        }}

        .kpi-title {{
            color: var(--muted);
            font-size: 13px;
            margin-bottom: 8px;
        }}

        .kpi-value {{
            font-size: 34px;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 8px;
        }}

        .kpi-sub {{
            color: var(--muted);
            font-size: 12px;
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }}

        .grid-2-equal {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }}

        .panel {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 22px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(12px);
        }}

        .panel h2 {{
            margin: 0 0 16px 0;
            font-size: 22px;
            letter-spacing: -0.02em;
        }}

        .panel p.small {{
            margin: -8px 0 16px 0;
            color: var(--muted);
            font-size: 13px;
        }}

        canvas {{
            width: 100% !important;
            height: 340px !important;
        }}

        .insights ul, .bullets ul {{
            margin: 0;
            padding-left: 20px;
        }}

        .insights li, .bullets li {{
            margin-bottom: 12px;
            line-height: 1.5;
            color: var(--text);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        th, td {{
            text-align: left;
            padding: 12px 10px;
            border-bottom: 1px solid var(--line);
        }}

        th {{
            color: #cbd5e1;
            font-weight: 700;
            background: rgba(255,255,255,0.03);
        }}

        .badge {{
            display: inline-block;
            color: white;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
        }}

        .table-wrap {{
            overflow-x: auto;
            border-radius: 16px;
        }}

        .heatmap-table th, .heatmap-table td {{
            text-align: center;
            white-space: nowrap;
        }}

        .sticky-col {{
            position: sticky;
            left: 0;
            background: #111827;
            z-index: 2;
        }}

        .footer {{
            color: var(--muted);
            font-size: 12px;
            padding: 8px 4px 20px 4px;
        }}

        @media (max-width: 1080px) {{
            .grid-2, .grid-2-equal {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">

        <div class="hero">
            <h1>Dashboard Executivo de Pricing</h1>
            <p>GreenCare vs Mantecorp | visão executiva com criticidade ponderada, heatmap e ação sugerida</p>

            <div class="hero-badges">
                <div class="hero-badge">Estratégia: híbrida</div>
                <div class="hero-badge">Ajuste máximo por ciclo: {AJUSTE_MAXIMO_CICLO:.0f}%</div>
                <div class="hero-badge">Prioridade: rede + SKU ponderados</div>
                <div class="hero-badge">Score executivo: {kpis['score_executivo']}</div>
                <div class="hero-badge">Leitura: {esc(kpis['criticidade_texto'])}</div>
            </div>
        </div>

        <div class="kpi-grid">
            {html_cards_kpi(kpis)}
        </div>

        <div class="grid-2">
            <div class="panel">
                <h2>Preço médio por SKU</h2>
                <p class="small">Comparação média GreenCare vs Mantecorp por SKU monitorado</p>
                <canvas id="graficoSku"></canvas>
            </div>

            <div class="panel">
                <h2>Distribuição de status competitivos</h2>
                <p class="small">Participação do portfólio nas faixas definidas de pricing</p>
                <canvas id="graficoStatus"></canvas>
            </div>
        </div>

        <div class="grid-2-equal">
            <div class="panel">
                <h2>Ranking de criticidade por rede</h2>
                <p class="small">Score ponderado considerando rede, SKU e gravidade do prêmio</p>
                <canvas id="graficoRede"></canvas>
            </div>

            <div class="panel insights">
                <h2>Leitura executiva automática</h2>
                <ul>
                    {insights_html}
                </ul>
            </div>
        </div>

        <div class="panel" style="margin-bottom:24px;">
            <h2>Heatmap Rede × SKU</h2>
            <p class="small">Leitura visual direta do posicionamento competitivo por rede e SKU</p>
            {html_heatmap(redes_heat, skus_heat, mapa_heat)}
        </div>

        <div class="grid-2-equal">
            <div class="panel bullets">
                <h2>Top problemas</h2>
                <ul>
                    {html_problemas(problemas)}
                </ul>
            </div>

            <div class="panel bullets">
                <h2>Top oportunidades</h2>
                <ul>
                    {html_oportunidades(oportunidades)}
                </ul>
            </div>
        </div>

        <div class="panel" style="margin-bottom:24px;">
            <h2>Ranking executivo de redes</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Rede</th>
                        <th>Premium médio</th>
                        <th>Críticos</th>
                        <th>Alertas</th>
                        <th>Score de criticidade</th>
                    </tr>
                </thead>
                <tbody>
                    {html_ranking_redes(ranking)}
                </tbody>
            </table>
        </div>

        <div class="panel" style="margin-bottom:24px;">
            <h2>Tabela detalhada com ação sugerida</h2>
            <p class="small">Base operacional para decisão e priorização tática</p>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Rede</th>
                            <th>SKU</th>
                            <th>GreenCare</th>
                            <th>Mantecorp</th>
                            <th>Delta</th>
                            <th>Premium</th>
                            <th>Status</th>
                            <th>Ação sugerida</th>
                            <th>Prioridade</th>
                        </tr>
                    </thead>
                    <tbody>
                        {html_tabela_detalhada(rows)}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            Dashboard V3 gerado automaticamente a partir de outputs/comparativo_precos.csv
        </div>
    </div>

    <script>
        const labelsSku = {json.dumps(labels_sku, ensure_ascii=False)};
        const greenSku = {json.dumps(green_sku)};
        const mtSku = {json.dumps(mt_sku)};
        const premiumSku = {json.dumps(premium_sku)};

        const labelsStatus = {json.dumps(labels_status, ensure_ascii=False)};
        const valoresStatus = {json.dumps(valores_status)};

        const labelsRede = {json.dumps(labels_rede, ensure_ascii=False)};
        const criticidadeRede = {json.dumps(criticidade_rede)};
        const premiumRede = {json.dumps(premium_rede)};

        const axisColor = 'rgba(255,255,255,0.12)';
        const tickColor = '#cbd5e1';

        new Chart(document.getElementById('graficoSku'), {{
            type: 'bar',
            data: {{
                labels: labelsSku,
                datasets: [
                    {{
                        label: 'GreenCare',
                        data: greenSku,
                        backgroundColor: 'rgba(20,184,166,0.75)',
                        borderColor: 'rgba(20,184,166,1)',
                        borderWidth: 1,
                        borderRadius: 8
                    }},
                    {{
                        label: 'Mantecorp',
                        data: mtSku,
                        backgroundColor: 'rgba(244,114,182,0.75)',
                        borderColor: 'rgba(244,114,182,1)',
                        borderWidth: 1,
                        borderRadius: 8
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: tickColor }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: tickColor }},
                        grid: {{ color: axisColor }}
                    }},
                    y: {{
                        ticks: {{ color: tickColor }},
                        grid: {{ color: axisColor }}
                    }}
                }}
            }}
        }});

        new Chart(document.getElementById('graficoStatus'), {{
            type: 'doughnut',
            data: {{
                labels: labelsStatus,
                datasets: [
                    {{
                        data: valoresStatus,
                        backgroundColor: [
                            '#15803d',
                            '#65a30d',
                            '#f59e0b',
                            '#dc2626',
                            '#2563eb'
                        ],
                        borderWidth: 0
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: tickColor }}
                    }}
                }}
            }}
        }});

        new Chart(document.getElementById('graficoRede'), {{
            type: 'bar',
            data: {{
                labels: labelsRede,
                datasets: [
                    {{
                        label: 'Score de criticidade',
                        data: criticidadeRede,
                        backgroundColor: 'rgba(59,130,246,0.75)',
                        borderColor: 'rgba(59,130,246,1)',
                        borderWidth: 1,
                        borderRadius: 8
                    }},
                    {{
                        label: 'Premium médio (%)',
                        data: premiumRede,
                        backgroundColor: 'rgba(239,68,68,0.70)',
                        borderColor: 'rgba(239,68,68,1)',
                        borderWidth: 1,
                        borderRadius: 8
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: tickColor }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: tickColor }},
                        grid: {{ color: axisColor }}
                    }},
                    y: {{
                        ticks: {{ color: tickColor }},
                        grid: {{ color: axisColor }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 88)
    print("GERANDO DASHBOARD V3")
    print("=" * 88)

    rows = carregar_comparativo()
    print(f"[DASHBOARD] Registros carregados: {len(rows)}")

    if not rows:
        raise ValueError("Nenhum registro encontrado no comparativo_precos.csv")

    html = gerar_dashboard_html(rows)

    with open(ARQUIVO_DASHBOARD, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[DASHBOARD] Dashboard salvo em: {ARQUIVO_DASHBOARD}")
    print("=" * 88)
    print("DASHBOARD V3 FINALIZADO")
    print("=" * 88)


if __name__ == "__main__":
    main()
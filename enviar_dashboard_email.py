import csv
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# =========================
# CONFIG
# =========================

ARQUIVO_CSV = "outputs/comparativo_precos.csv"

EMAIL_REMETENTE = "inteligenciapricing@gmail.com"
SENHA_APP = "xjxc sqrw hihd toal"

LINK_DASHBOARD = "https://greencare-pricing.netlify.app"

DESTINATARIOS = [
    "fabio.furtado@greencarepharma.com.br",
    "sabrina.albertoni@greencarepharma.com.br",
    "gustavo.franceli@greencarepharma.com.br",
    "marcelo.ma@greencarepharma.com.br",
    "marcelo.macedo@greencarepharma.com.br",
    "marcelo.caetano@greencarepharma.com.br",
    "edmar.neix@greencarepharma.com.br",
    "filipe.lopes@greencarepharma.com.br",
    "flavio.brito@greencarepharma.com.br",
    "denil.rabelo@greencarepharma.com.br",
    "vagner.soares@greencarepharma.com.br",
    "felipe.santos@greencarepharma.com.br",
    "hamza.yaziji@greencarepharma.com.br",
    "martim.mattos@greencarepharma.com.br",
    "nelson@greenfield.global"
]

# =========================
# UTILS
# =========================

def to_float(v):
    try:
        return float(v)
    except Exception:
        return None

def pct(v):
    if v is None:
        return "N/A"
    return f"{v:.2f}%"

# =========================
# LEITURA
# =========================

def carregar():
    rows = []
    with open(ARQUIVO_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["premium_pct"] = to_float(r.get("premium_pct"))
            r["peso_total"] = to_float(r.get("peso_total"))
            rows.append(r)
    return rows

# =========================
# KPI
# =========================

def gerar_kpis(rows):
    premiums = [r["premium_pct"] for r in rows if r["premium_pct"] is not None]

    premio_medio = sum(premiums) / len(premiums) if premiums else 0
    criticos = sum(1 for r in rows if r.get("status") == "CRITICO")
    alerta = sum(1 for r in rows if r.get("status") == "ALERTA")

    return premio_medio, criticos, alerta

# =========================
# TOPS
# =========================

def top_problemas(rows):
    criticos = [r for r in rows if r.get("status") == "CRITICO"]
    criticos.sort(key=lambda x: x.get("peso_total") or 0, reverse=True)
    return criticos[:5]

def top_oportunidades(rows):
    ops = [r for r in rows if r.get("premium_pct") is not None and r.get("premium_pct") < 0]
    ops.sort(key=lambda x: x.get("peso_total") or 0, reverse=True)
    return ops[:5]

# =========================
# HTML EMAIL
# =========================

def montar_html(rows):
    premio_medio, criticos, alerta = gerar_kpis(rows)
    problemas = top_problemas(rows)
    oportunidades = top_oportunidades(rows)

    data_ref = datetime.now().strftime("%d/%m/%Y %H:%M")

    html_prob = ""
    for p in problemas:
        html_prob += f"<li>{p['rede']} - {p['sku']} ({pct(p['premium_pct'])})</li>"

    html_op = ""
    for o in oportunidades:
        html_op += f"<li>{o['rede']} - {o['sku']} ({pct(o['premium_pct'])})</li>"

    return f"""
    <html>
    <body style="background:#0b1220;color:#e5e7eb;font-family:Arial;padding:24px">

    <h2 style="color:#10b981;">GreenCare Pricing Intelligence</h2>

    <p>Atualização automática de pricing competitivo</p>

    <p><b>Data:</b> {data_ref}</p>

    <hr style="border:1px solid #1f2937">

    <h3>Resumo executivo</h3>
    <ul>
        <li>Prêmio médio: <b>{pct(premio_medio)}</b></li>
        <li>Itens críticos: <b>{criticos}</b></li>
        <li>Itens em alerta: <b>{alerta}</b></li>
    </ul>

    <h3>Leitura rápida</h3>
    <p>
    O portfólio segue posicionado como premium frente ao principal concorrente,
    com concentração relevante de itens em zona crítica, exigindo ajuste seletivo
    por rede e SKU.
    </p>

    <h3>Principais pontos de atenção</h3>
    <ul>
        {html_prob}
    </ul>

    <h3>Oportunidades identificadas</h3>
    <ul>
        {html_op}
    </ul>

    <br>

    <a href="{LINK_DASHBOARD}"
       style="
        display:inline-block;
        padding:14px 22px;
        background:#10b981;
        color:#ffffff;
        text-decoration:none;
        border-radius:8px;
        font-weight:bold;
       ">
       👉 Abrir Dashboard Completo
    </a>

    <p style="margin-top:20px;font-size:12px;color:#9ca3af;">
    Recomendado: acessar o dashboard completo para visão detalhada por rede, SKU e criticidade.
    </p>

    </body>
    </html>
    """

# =========================
# ENVIO
# =========================

def enviar_email(html):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = ", ".join(DESTINATARIOS)
    msg["Subject"] = "GreenCare | Pricing Dashboard"

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_REMETENTE, SENHA_APP)
        server.sendmail(EMAIL_REMETENTE, DESTINATARIOS, msg.as_string())

# =========================
# MAIN
# =========================

def main():
    print("Carregando dados...")
    rows = carregar()

    print("Montando email...")
    html = montar_html(rows)

    print("Enviando email...")
    enviar_email(html)

    print("Email enviado com sucesso!")

if __name__ == "__main__":
    main()
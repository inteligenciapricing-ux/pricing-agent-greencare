import csv
import os
from collections import defaultdict
from datetime import datetime


ARQUIVO_ENTRADA = "outputs/precos.csv"
ARQUIVO_RELATORIO = "outputs/analise.txt"
ARQUIVO_COMPARATIVO = "outputs/comparativo_precos.csv"


def parse_preco(preco_str):
    if preco_str is None:
        return None

    texto = str(preco_str).strip()
    if not texto:
        return None

    texto = texto.replace("R$", "").replace(".", "").replace(",", ".").strip()

    try:
        return float(texto)
    except Exception:
        return None


def formatar_brl(valor):
    if valor is None:
        return "N/A"
    return f"R$ {valor:.2f}"


def formatar_pct(valor):
    if valor is None:
        return "N/A"
    return f"{valor:.2f}%"


def ler_csv_precos(caminho):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    registros = []

    with open(caminho, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            preco = parse_preco(row.get("preco_promocional", ""))
            if preco is None:
                continue

            row["_preco_float"] = preco

            try:
                row["_datahora"] = datetime.strptime(row["data_hora"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                row["_datahora"] = None

            registros.append(row)

    return registros


def normalizar_rede(rede):
    rede = str(rede or "").strip()
    return rede


def normalizar_empresa(empresa, marca):
    empresa = str(empresa or "").strip().lower()
    marca = str(marca or "").strip().lower()

    if "greencare" in empresa or "greencare" in marca:
        return "GreenCare"

    if "mantecorp" in empresa or "mantecorp" in marca:
        return "Mantecorp"

    return str(marca or empresa).strip()


def chave_sku(row):
    return (
        str(row.get("grupo_comparacao", "")).strip(),
        str(row.get("concentracao_mg_ml", "")).strip(),
        str(row.get("volume_ml", "")).strip(),
        str(row.get("tipo_produto", "")).strip(),
    )


def nome_sku(row):
    concentracao = str(row.get("concentracao_mg_ml", "")).strip()
    volume = str(row.get("volume_ml", "")).strip()
    tipo = str(row.get("tipo_produto", "")).strip()

    if tipo:
        return f"{tipo}_{concentracao}mg_{volume}ml"
    return f"{concentracao}mg_{volume}ml"


def classificar_status(premium_pct):
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


def peso_sku(concentracao, volume):
    chave = (str(concentracao).strip(), str(volume).strip())

    pesos = {
        ("79,14", "30"): 0.50,
        ("160,32", "10"): 0.30,
        ("23,75", "10"): 0.20,
    }

    return pesos.get(chave, 0.0)


def peso_rede(rede):
    rede = normalizar_rede(rede)

    pesos = {
        "Drogasil": 0.20,
        "DrogaRaia": 0.20,
        "Raia": 0.20,
        "DrogariaSaoPaulo": 0.30,
        "PagueMenos": 0.20,
        "Panvel": 0.10,
    }

    return pesos.get(rede, 0.0)


def ordenar_registros_mais_recentes(registros):
    return sorted(
        registros,
        key=lambda x: (
            x["_datahora"] is not None,
            x["_datahora"] or datetime.min
        ),
        reverse=True
    )


def selecionar_ultimo_registro_por_rede_empresa_sku(registros):
    registros_ordenados = ordenar_registros_mais_recentes(registros)

    melhores = {}

    for row in registros_ordenados:
        rede = normalizar_rede(row.get("rede", ""))
        empresa_norm = normalizar_empresa(row.get("empresa", ""), row.get("marca", ""))
        sku = chave_sku(row)

        chave = (rede, empresa_norm, sku)

        if chave not in melhores:
            melhores[chave] = row

    return melhores


def montar_comparativos(registros):
    ultimos = selecionar_ultimo_registro_por_rede_empresa_sku(registros)

    chaves_base = set()
    for rede, empresa, sku in ultimos.keys():
        chaves_base.add((rede, sku))

    comparativos = []

    for rede, sku in sorted(chaves_base):
        gc = ultimos.get((rede, "GreenCare", sku))
        mt = ultimos.get((rede, "Mantecorp", sku))

        if not gc or not mt:
            continue

        preco_gc = gc["_preco_float"]
        preco_mt = mt["_preco_float"]

        diferenca_absoluta = preco_gc - preco_mt
        diferenca_percentual = ((preco_gc / preco_mt) - 1.0) * 100 if preco_mt else None
        premium_gc = diferenca_percentual
        status = classificar_status(premium_gc)

        concentracao = gc.get("concentracao_mg_ml", "")
        volume = gc.get("volume_ml", "")
        tipo = gc.get("tipo_produto", "")
        grupo = gc.get("grupo_comparacao", "")

        item = {
            "data_hora": gc.get("data_hora", ""),
            "rede": rede,
            "grupo_comparacao": grupo,
            "sku": nome_sku(gc),
            "tipo_produto": tipo,
            "concentracao_mg_ml": concentracao,
            "volume_ml": volume,
            "green_price": round(preco_gc, 2),
            "mantecorp_price": round(preco_mt, 2),
            "delta_abs": round(diferenca_absoluta, 2),
            "premium_pct": round(premium_gc, 2) if premium_gc is not None else None,
            "status": status,
            "peso_sku": peso_sku(concentracao, volume),
            "peso_rede": peso_rede(rede),
            "peso_total": round(peso_sku(concentracao, volume) * peso_rede(rede), 4),
            "gc_produto": gc.get("produto", ""),
            "mt_produto": mt.get("produto", ""),
            "gc_url": gc.get("url", ""),
            "mt_url": mt.get("url", ""),
        }

        comparativos.append(item)

    return comparativos


def salvar_comparativo_csv(comparativos, caminho):
    cabecalho = [
        "data_hora",
        "rede",
        "grupo_comparacao",
        "sku",
        "tipo_produto",
        "concentracao_mg_ml",
        "volume_ml",
        "green_price",
        "mantecorp_price",
        "delta_abs",
        "premium_pct",
        "status",
        "peso_sku",
        "peso_rede",
        "peso_total",
        "gc_produto",
        "mt_produto",
        "gc_url",
        "mt_url",
    ]

    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cabecalho)
        writer.writeheader()
        for item in comparativos:
            writer.writerow(item)


def gerar_resumo_estrategico(comparativos):
    if not comparativos:
        return {
            "premio_medio": None,
            "maior_premio": None,
            "menor_premio": None,
            "marca_posicionamento": "Sem dados suficientes",
        }

    premiums = [x["premium_pct"] for x in comparativos if x["premium_pct"] is not None]

    if not premiums:
        return {
            "premio_medio": None,
            "maior_premio": None,
            "menor_premio": None,
            "marca_posicionamento": "Sem dados suficientes",
        }

    premio_medio = sum(premiums) / len(premiums)
    maior_premio = max(premiums)
    menor_premio = min(premiums)

    if premio_medio > 0:
        posicionamento = "GreenCare está posicionada como marca premium frente à Mantecorp."
    elif premio_medio < 0:
        posicionamento = "GreenCare está posicionada abaixo da Mantecorp, indicando oportunidade comercial e possível subprecificação."
    else:
        posicionamento = "GreenCare está alinhada à Mantecorp em média."

    return {
        "premio_medio": premio_medio,
        "maior_premio": maior_premio,
        "menor_premio": menor_premio,
        "marca_posicionamento": posicionamento,
    }


def montar_relatorio_txt(comparativos):
    linhas = []

    linhas.append("=" * 88)
    linhas.append("INTELIGÊNCIA DE PRICING – GREENCARE VS MANTECORP")
    linhas.append("=" * 88)
    linhas.append("")

    for item in comparativos:
        linhas.append(f"SKU: {item['sku']}")
        linhas.append(f"Rede: {item['rede']}")
        linhas.append("-" * 80)
        linhas.append("")
        linhas.append(f"Mantecorp: {formatar_brl(item['mantecorp_price'])}")
        linhas.append(f"GreenCare: {formatar_brl(item['green_price'])}")
        linhas.append("")
        linhas.append(f"Mais barato: {'Mantecorp' if item['mantecorp_price'] < item['green_price'] else 'GreenCare'} - {formatar_brl(min(item['mantecorp_price'], item['green_price']))}")
        linhas.append(f"Mais caro: {'GreenCare' if item['green_price'] > item['mantecorp_price'] else 'Mantecorp'} - {formatar_brl(max(item['mantecorp_price'], item['green_price']))}")
        linhas.append(f"Diferença absoluta: {formatar_brl(item['delta_abs'])}")
        linhas.append(f"Diferença percentual: {formatar_pct(item['premium_pct'])}")
        linhas.append("")
        linhas.append(f"Prêmio GreenCare: {formatar_pct(item['premium_pct'])}")
        linhas.append(f"Status competitivo: {item['status']}")
        linhas.append("-" * 80)
        linhas.append("")

    resumo = gerar_resumo_estrategico(comparativos)

    linhas.append("=" * 88)
    linhas.append("RESUMO ESTRATÉGICO DO PORTFÓLIO")
    linhas.append("=" * 88)

    linhas.append(f"Prêmio médio GreenCare: {formatar_pct(resumo['premio_medio'])}")
    linhas.append(f"Maior prêmio observado: {formatar_pct(resumo['maior_premio'])}")
    linhas.append(f"Menor prêmio observado: {formatar_pct(resumo['menor_premio'])}")
    linhas.append("")
    linhas.append(resumo["marca_posicionamento"])
    linhas.append("=" * 88)

    return "\n".join(linhas)


def salvar_relatorio_txt(texto, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)


def analisar():
    print("=" * 88)
    print("INICIANDO ANÁLISE DE PRICING")
    print("=" * 88)

    registros = ler_csv_precos(ARQUIVO_ENTRADA)
    print(f"[ANALISADOR] Registros válidos carregados: {len(registros)}")

    comparativos = montar_comparativos(registros)
    print(f"[ANALISADOR] Comparativos montados: {len(comparativos)}")

    texto = montar_relatorio_txt(comparativos)
    salvar_relatorio_txt(texto, ARQUIVO_RELATORIO)
    print(f"[ANALISADOR] Relatório TXT salvo em: {ARQUIVO_RELATORIO}")

    salvar_comparativo_csv(comparativos, ARQUIVO_COMPARATIVO)
    print(f"[ANALISADOR] Comparativo CSV salvo em: {ARQUIVO_COMPARATIVO}")

    print("=" * 88)
    print("ANÁLISE FINALIZADA")
    print("=" * 88)


if __name__ == "__main__":
    analisar()
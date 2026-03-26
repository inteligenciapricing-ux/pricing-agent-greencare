import csv
import matplotlib.pyplot as plt
from collections import defaultdict

ARQUIVO_CSV = "outputs/comparativo_precos.csv"


def to_float(v):
    try:
        return float(v)
    except:
        return None


def carregar():
    rows = []
    with open(ARQUIVO_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["premium_pct"] = to_float(r.get("premium_pct"))
            rows.append(r)
    return rows


# =========================================
# GRAFICO 1 — PREÇO POR SKU
# =========================================
def grafico_sku(rows):
    data = defaultdict(lambda: {"green": [], "mantecorp": []})

    for r in rows:
        sku = r["sku"]
        g = to_float(r.get("green_price"))
        m = to_float(r.get("mantecorp_price"))

        if g:
            data[sku]["green"].append(g)
        if m:
            data[sku]["mantecorp"].append(m)

    skus = []
    green_avg = []
    mante_avg = []

    for sku, v in data.items():
        skus.append(sku[:20])
        green_avg.append(sum(v["green"]) / len(v["green"]))
        mante_avg.append(sum(v["mantecorp"]) / len(v["mantecorp"]))

    x = range(len(skus))

    plt.figure()
    plt.bar(x, green_avg)
    plt.bar(x, mante_avg, bottom=green_avg)

    plt.xticks(x, skus, rotation=20)
    plt.title("Preço médio por SKU")
    plt.tight_layout()
    plt.savefig("outputs/grafico_sku.png")
    plt.close()


# =========================================
# GRAFICO 2 — STATUS
# =========================================
def grafico_status(rows):
    contagem = defaultdict(int)

    for r in rows:
        contagem[r["status"]] += 1

    labels = list(contagem.keys())
    values = list(contagem.values())

    plt.figure()
    plt.pie(values, labels=labels, autopct='%1.0f%%')
    plt.title("Distribuição de status")
    plt.savefig("outputs/grafico_status.png")
    plt.close()


# =========================================
# GRAFICO 3 — REDE
# =========================================
def grafico_rede(rows):
    redes = defaultdict(list)

    for r in rows:
        redes[r["rede"]].append(r["premium_pct"])

    nomes = []
    medias = []

    for rede, vals in redes.items():
        vals = [v for v in vals if v is not None]
        if vals:
            nomes.append(rede)
            medias.append(sum(vals) / len(vals))

    plt.figure()
    plt.bar(nomes, medias)
    plt.title("Premium médio por rede")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig("outputs/grafico_rede.png")
    plt.close()


def main():
    print("Gerando gráficos...")
    rows = carregar()

    grafico_sku(rows)
    grafico_status(rows)
    grafico_rede(rows)

    print("Gráficos gerados em /outputs")


if __name__ == "__main__":
    main()
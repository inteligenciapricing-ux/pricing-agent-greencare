import os
import sys
import subprocess
from datetime import datetime


def rodar_comando(descricao, comando):
    print("=" * 80, flush=True)
    print(f"INICIANDO: {descricao}", flush=True)
    print("=" * 80, flush=True)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    processo = subprocess.Popen(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env
    )

    for linha in processo.stdout:
        print(linha, end="")

    processo.wait()

    print("=" * 80, flush=True)
    print(f"FINALIZADO: {descricao}", flush=True)
    print("=" * 80, flush=True)


def run():
    print("\n🚀 INICIANDO CICLO COMPLETO\n", flush=True)

    # 1. COLETA DE PREÇOS
    rodar_comando(
        "COLETA DE PREÇOS",
        [sys.executable, "-u", "scripts/price_scraper.py"]
    )

    # 2. ENVIO DO DASHBOARD (NOVO - CORRIGIDO)
    rodar_comando(
        "ENVIO DE RELATÓRIO",
        [sys.executable, "-u", "scripts/enviar_dashboard_email.py"]
    )

    print(
        f"\n✅ CICLO COMPLETO FINALIZADO EM {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n",
        flush=True
    )


if __name__ == "__main__":
    run()
"""
testar_trava.py — Teste automatizado completo da trava de segurança editorial e sanidade.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from validador_publicacao import (
    validar_arquivo_html,
    emitir_relatorio_validacao,
    verificar_sanidade_radar,
)

def main():
    pasta = Path(__file__).parent.resolve()

    print("\n" + "=" * 80)
    print("TESTE SANIDADE 1: RADAR COM ABA ESTRUTURAÇÃO VAZIA (DEVE REPROVAR)")
    print("=" * 80)
    html_mutilado = """<!DOCTYPE html>
<html><body>
<section class="tab-panel active" id="panel-participativo"><article class="dossier-card">Card 1</article></section>
<section class="tab-panel" id="panel-estruturacao"></section>
<section class="tab-panel" id="panel-leiloes"><article class="est-card">Leilão 1</article></section>
<section class="tab-panel" id="panel-sfn"><article class="dossier-card">SFN 1</article></section>
</body></html>"""
    viol_sanidade = verificar_sanidade_radar(html_mutilado, "radar.html")
    print(f"Violações de sanidade detectadas: {len(viol_sanidade)}")
    for v in viol_sanidade:
        print(f"  • {v['termo']}: {v['detalhe']}")

    print("\n" + "=" * 80)
    print("TESTE SANIDADE 2: RADAR_ATUAL.HTML REAL PREENCHIDO (DEVE APROVAR)")
    print("=" * 80)
    p_real = pasta / "radar_atual.html"
    aprov, viol, avis = validar_arquivo_html(p_real)
    emitir_relatorio_validacao(aprov, viol, avis, p_real.name)

    if len(viol_sanidade) > 0 and aprov:
        print("\n[SUCESSO] Trava de sanidade e segurança editorial 100% validada.")
        sys.exit(0)
    else:
        print("\n[FALHA] Resultado divergente do esperado.")
        sys.exit(1)

if __name__ == "__main__":
    main()

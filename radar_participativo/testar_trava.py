"""
testar_trava.py — Teste automatizado completo da trava de segurança editorial.
Valida:
1. Radar: Injeção de termos proibidos (decon, núcleo, segurabilidade, mpor composto) e 'em execução' em selo reprova.
2. Radar: 'em execução' em texto livre fora de selo NÃO reprova.
3. Clipping: Marca DECON e MPOR é permitida (NÃO reprova).
4. Clipping: Injeção de @mpor.gov.br ou processo SEI reprova.
5. Prova Real: Execução sobre clipping.html e radar.html da URL pública (ambos APROVADOS).
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from validador_publicacao import (
    validar_arquivo_html,
    emitir_relatorio_validacao,
    verificar_conteudo_html,
)

def main():
    pasta = Path(__file__).parent.resolve()

    print("\n" + "=" * 80)
    print("TESTE 1: RADAR COM INJEÇÃO PROPOSITAL (DEVE REPROVAR)")
    print("=" * 80)
    html_radar_injetado = """<!DOCTYPE html>
<html>
<body>
  <div class="card">
    <!-- Texto livre com 'em execução' fora de selo: NÃO deve reprovar -->
    <p>As obras de dragagem estão em execução pela autoridade portuária.</p>
    <!-- Selo de situação com 'Em Execução': DEVE reprovar -->
    <span class="deadline-pill status-ERRO">Em Execução</span>
    <!-- Termos proibidos no Radar -->
    <span>Portaria MPOR_FOCO emitida pela DECON do Núcleo com foco em segurabilidade.</span>
  </div>
</body>
</html>"""
    arq_radar_inj = pasta / "teste_radar_inj.html"
    arq_radar_inj.write_text(html_radar_injetado, encoding="utf-8")
    aprovado_r_inj, viol_r_inj, avisos_r_inj = validar_arquivo_html(arq_radar_inj)
    emitir_relatorio_validacao(aprovado_r_inj, viol_r_inj, avisos_r_inj, arq_radar_inj.name)
    arq_radar_inj.unlink()

    print("\n" + "=" * 80)
    print("TESTE 2: RADAR COM 'EM EXECUÇÃO' APENAS NO TEXTO LIVRE (DEVE APROVAR)")
    print("=" * 80)
    html_radar_livre = """<!DOCTYPE html>
<html>
<body>
  <div class="card">
    <p>O consórcio informou que a mobilização de canteiro está em execução.</p>
    <span class="deadline-pill status-OK">Contrato assinado em 17/05/2024</span>
    <p>A importação de trilhos temporariamente autorizada segue o cronograma.</p>
  </div>
</body>
</html>"""
    arq_radar_livre = pasta / "radar_texto_livre.html"
    arq_radar_livre.write_text(html_radar_livre, encoding="utf-8")
    aprovado_r_livre, viol_r_livre, avisos_r_livre = validar_arquivo_html(arq_radar_livre)
    emitir_relatorio_validacao(aprovado_r_livre, viol_r_livre, avisos_r_livre, arq_radar_livre.name)
    arq_radar_livre.unlink()

    print("\n" + "=" * 80)
    print("TESTE 3: CLIPPING COM MARCA DECON/MPOR (DEVE APROVAR)")
    print("=" * 80)
    html_clipping_marca = """<!DOCTYPE html>
<html>
<body>
  <header>
    <h1>Boletim Diário DECON / MPOR</h1>
    <p>Curadoria de notícias do Ministério de Portos e Aeroportos (MPOR).</p>
  </header>
  <article>
    <p>Matéria sobre núcleo portuário e seguros.</p>
  </article>
</body>
</html>"""
    arq_clip_marca = pasta / "clipping_marca.html"
    arq_clip_marca.write_text(html_clipping_marca, encoding="utf-8")
    aprovado_c_marca, viol_c_marca, avisos_c_marca = validar_arquivo_html(arq_clip_marca)
    emitir_relatorio_validacao(aprovado_c_marca, viol_c_marca, avisos_c_marca, arq_clip_marca.name)
    arq_clip_marca.unlink()

    print("\n" + "=" * 80)
    print("TESTE 4: CLIPPING COM DADOS PROIBIDOS (E-MAIL @MPOR E PROCESSO SEI) (DEVE REPROVAR)")
    print("=" * 80)
    html_clipping_vazamento = """<!DOCTYPE html>
<html>
<body>
  <p>Contato do servidor: fulano.tal@mpor.gov.br para esclarecimentos.</p>
  <p>Consulte os autos do processo SEI nº 50000.012345/2024-88 para mais dados.</p>
</body>
</html>"""
    arq_clip_vaz = pasta / "clipping_vazamento.html"
    arq_clip_vaz.write_text(html_clipping_vazamento, encoding="utf-8")
    aprovado_c_vaz, viol_c_vaz, avisos_c_vaz = validar_arquivo_html(arq_clip_vaz)
    emitir_relatorio_validacao(aprovado_c_vaz, viol_c_vaz, avisos_c_vaz, arq_clip_vaz.name)
    arq_clip_vaz.unlink()

    print("\n" + "=" * 80)
    print("TESTE 5: PROVA REAL — CLIPPING.HTML E RADAR.HTML DA URL PÚBLICA")
    print("=" * 80)
    headers = {"User-Agent": "Mozilla/5.0"}

    # Baixa radar.html público
    url_radar = "https://mdagavea.github.io/inteligencia-regulatoria/radar.html"
    req_r = urllib.request.Request(url_radar, headers=headers)
    with urllib.request.urlopen(req_r) as resp:
        conteudo_radar_pub = resp.read().decode("utf-8")
    arq_radar_pub = pasta / "radar.html"
    arq_radar_pub.write_text(conteudo_radar_pub, encoding="utf-8")

    # Baixa clipping.html público
    url_clip = "https://mdagavea.github.io/inteligencia-regulatoria/clipping.html"
    req_c = urllib.request.Request(url_clip, headers=headers)
    with urllib.request.urlopen(req_c) as resp:
        conteudo_clip_pub = resp.read().decode("utf-8")
    arq_clip_pub = pasta / "clipping.html"
    arq_clip_pub.write_text(conteudo_clip_pub, encoding="utf-8")

    # Roda a trava exatamente como no workflow
    aprov_r, viol_r, avis_r = validar_arquivo_html(arq_radar_pub)
    emitir_relatorio_validacao(aprov_r, viol_r, avis_r, arq_radar_pub.name)

    aprov_c, viol_c, avis_c = validar_arquivo_html(arq_clip_pub)
    emitir_relatorio_validacao(aprov_c, viol_c, avis_c, arq_clip_pub.name)

    print("\n" + "=" * 80)
    print("RESUMO DOS 5 TESTES:")
    print(f"  Teste 1 (Radar Injetado) -> Reprovou? {not aprovado_r_inj} ({len(viol_r_inj)} violações)")
    print(f"  Teste 2 (Radar Texto Livre 'em execução') -> Aprovou? {aprovado_r_livre}")
    print(f"  Teste 3 (Clipping com DECON/MPOR) -> Aprovou? {aprovado_c_marca}")
    print(f"  Teste 4 (Clipping com @mpor e SEI) -> Reprovou? {not aprovado_c_vaz} ({len(viol_c_vaz)} violações)")
    print(f"  Teste 5A (Radar da URL pública) -> Aprovou? {aprov_r}")
    print(f"  Teste 5B (Clipping da URL pública) -> Aprovou? {aprov_c}")
    print("=" * 80 + "\n")

    todos_ok = (not aprovado_r_inj and aprovado_r_livre and aprovado_c_marca and not aprovado_c_vaz and aprov_r and aprov_c)
    if todos_ok:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

import base64
import json
import subprocess
from pathlib import Path

REPO = "mdagavea/inteligencia-regulatoria"
URL_BASE_PAGES = "https://mdagavea.github.io/inteligencia-regulatoria"

INDEX_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hub de Inteligência Regulatória & Participação Social</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 24px;
    }
    .hub {
      max-width: 680px;
      width: 100%;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    }
    h1 { margin: 0 0 8px 0; font-size: 1.5rem; }
    p { margin: 0 0 24px 0; color: #94a3b8; font-size: 0.95rem; }
    .cards { display: flex; flex-direction: column; gap: 14px; }
    a.card {
      display: block;
      text-decoration: none;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 18px 20px;
      color: #f8fafc;
      transition: transform 0.15s, border-color 0.15s;
    }
    a.card:hover {
      transform: translateY(-2px);
      border-color: #38bdf8;
    }
    .card h2 { margin: 0 0 6px 0; font-size: 1.1rem; color: #38bdf8; }
    .card span { font-size: 0.88rem; color: #cbd5e1; }
  </style>
</head>
<body>
  <div class="hub">
    <h1>📊 Hub de Inteligência Regulatória & Financeira</h1>
    <p>Selecione o painel executivo que deseja acessar:</p>
    <div class="cards">
      <a class="card" href="./clipping.html">
        <h2>📰 Clipping Diário Executivo →</h2>
        <span>Curadoria diária de notícias (Infraestrutura & Outorgas, Seguros de Grandes Riscos, Carbono, Mercado de Capitais e Tecnologia/IA Aplicada).</span>
      </a>
      <a class="card" href="./historico/index.html">
        <h2>📚 Repositório Histórico de Clippings (Acervo por Data) →</h2>
        <span>Consulte qualquer edição diária anterior arquivada automaticamente por data.</span>
      </a>
      <a class="card" href="./radar.html">
        <h2>🏛️ Radar Brasil Participativo — Gestão & Dossiês Normativos →</h2>
        <span>Monitoramento completo de Consultas Públicas, Audiências, Tomadas de Subsídios, Planos Setoriais, Prazos e Kit de Estudo (DOU / SEI / PDFs).</span>
      </a>
    </div>
  </div>
</body>
</html>
"""


def _gh_api(method: str, endpoint: str, payload: dict = None):
    cmd = ["gh", "api", "-X", method, endpoint]
    if payload is not None:
        cmd.extend(["--input", "-"])
        p = subprocess.run(cmd, input=json.dumps(payload).encode("utf-8"), capture_output=True)
    else:
        p = subprocess.run(cmd, capture_output=True)
    out = p.stdout.decode("utf-8", errors="replace")
    err = p.stderr.decode("utf-8", errors="replace")
    return p.returncode, out, err


def enviar_arquivo_github(caminho_remoto: str, conteudo_str: str, mensagem_commit: str) -> bool:
    """Cria ou atualiza um arquivo no repositório via GitHub REST API."""
    endpoint = f"repos/{REPO}/contents/{caminho_remoto}"
    code, out, _ = _gh_api("GET", endpoint)
    sha_atual = None
    if code == 0:
        try:
            sha_atual = json.loads(out).get("sha")
        except Exception:
            pass

    b64 = base64.b64encode(conteudo_str.encode("utf-8")).decode("ascii")
    payload = {
        "message": mensagem_commit,
        "content": b64,
        "branch": "main"
    }
    if sha_atual:
        payload["sha"] = sha_atual

    code, _, err = _gh_api("PUT", endpoint, payload)
    if code != 0:
        print(f"   [Aviso GitHub API] Falha ao enviar {caminho_remoto}: {err[:150]}")
        return False
    return True


def garantir_github_pages_ativo():
    """Ativa o GitHub Pages na branch main caso ainda não esteja habilitado e dispara atualização."""
    code, _, _ = _gh_api("GET", f"repos/{REPO}/pages")
    if code != 0:
        _gh_api("POST", f"repos/{REPO}/pages", {
            "source": {"branch": "main", "path": "/"}
        })
    _gh_api("POST", f"repos/{REPO}/pages/builds")


def publicar_arquivo_html(caminho_local: Path, nome_remoto: str, titulo_log: str) -> str:
    """Publica um arquivo HTML local no GitHub Pages e retorna a URL pública."""
    conteudo = Path(caminho_local).read_text(encoding="utf-8")
    ok = enviar_arquivo_github(nome_remoto, conteudo, f"Atualiza {titulo_log}")
    # Garante também o index.html
    enviar_arquivo_github("index.html", INDEX_HTML, "Atualiza Hub index.html")
    garantir_github_pages_ativo()
    if ok:
        return f"{URL_BASE_PAGES}/{nome_remoto}"
    return ""

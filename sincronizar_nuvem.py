"""
Utilitário de Sincronização Bidirecional com a Nuvem (GitHub REST API via `gh api`)
Permite fazer PUSH (subir códigos e memórias para a nuvem), PULL (baixar atualizações da nuvem)
e RUN-CLOUD (disparar o workflow na nuvem) sem depender do executável `git.exe` instalado localmente.

Uso:
  python3.12 sincronizar_nuvem.py push ["Mensagem de commit"]
  python3.12 sincronizar_nuvem.py pull
  python3.12 sincronizar_nuvem.py status
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

REPO = "mdagavea/inteligencia-regulatoria"
BRANCH = "main"
RAIZ_LOCAL = Path(__file__).parent.resolve()

# Lista explícita de arquivos do projeto que devem ser sincronizados com o GitHub
ARQUIVOS_SINCRONIZADOS = [
    ".gitignore",
    "CLAUDE.md",
    "GEMINI.md",
    "requirements.txt",
    "sincronizar_nuvem.py",
    ".github/copilot-instructions.md",
    ".github/workflows/disparo_email.yml",
    ".github/workflows/clipping_diario_nuvem.yml",
    "clipping/coletor.py",
    "clipping/curador.py",
    "clipping/renderizador.py",
    "clipping/gerar_clipping.py",
    "clipping/executar_clipping.bat",
    "clipping/executar_automatico.bat",
    "clipping/INSTRUCOES.md",
    "clipping/MEMORIA_PROJETO.md",
    "clipping/HISTORICO_PROJETO.md",
    "clipping/2026-11-05_Passagem_Envio_Email_Clipping_para_Gemini.md",
    "clipping/termos_filtro.json",
    "clipping/log_descartados_filtro.txt",
    "radar_participativo/coletor_participativo.py",
    "radar_participativo/coletor_estruturacao_leiloes.py",
    "radar_participativo/coletor_sfn.py",
    "radar_participativo/curador_participativo.py",
    "radar_participativo/renderizador_participativo.py",
    "radar_participativo/publicador_web.py",
    "radar_participativo/gerar_radar.py",
    "radar_participativo/executar_radar.bat",
    "radar_participativo/termos_filtro.json",
    "radar_participativo/log_descartados_filtro.txt",
    "radar_participativo/historico_processos.json",
    "radar_participativo/INSTRUCOES.md",
    "radar_participativo/MEMORIA_PROJETO.md",
    "radar_participativo/REGRAS_ABA_ESTRUTURACAO.md",
    "radar_participativo/REGRAS_ABA_LEILOES.md",
    "radar_participativo/termos_selos_estruturacao.json",
    "radar_participativo/coletor_tcu.py",
    "radar_participativo/coletor_dou.py",
    "radar_participativo/validador_radar.py",
    "radar_participativo/validador_publicacao.py",
    "radar_participativo/testar_trava.py",
    "radar_participativo/HISTORICO_PROJETO.md",
    "radar_participativo/2026-10-28_Ajustes_Aba_Estruturacao_para_Gemini.md",
    "radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md",
]


def gh_api(method: str, endpoint: str, payload: dict = None):
    cmd = ["gh", "api", "-X", method, endpoint]
    if payload is not None:
        cmd.extend(["--input", "-"])
        p = subprocess.run(cmd, input=json.dumps(payload).encode("utf-8"), capture_output=True)
    else:
        p = subprocess.run(cmd, capture_output=True)
    out = p.stdout.decode("utf-8", errors="replace")
    err = p.stderr.decode("utf-8", errors="replace")
    return p.returncode, out, err


def push_para_nuvem(mensagem: str = "Sincroniza codigo-fonte e documentacao multi-agente com a nuvem"):
    print(f"[PUSH] Conectando ao repositório {REPO} ({BRANCH})...")
    code, out, err = gh_api("GET", f"repos/{REPO}/git/ref/heads/{BRANCH}")
    if code != 0:
        print(f"[ERRO] Não foi possível obter a referência da branch {BRANCH}: {err}")
        sys.exit(1)
    ref_data = json.loads(out)
    commit_sha_atual = ref_data["object"]["sha"]

    code, out, err = gh_api("GET", f"repos/{REPO}/git/commits/{commit_sha_atual}")
    if code != 0:
        print(f"[ERRO] Não foi possível obter o commit base: {err}")
        sys.exit(1)
    base_tree_sha = json.loads(out)["tree"]["sha"]

    tree_items = []
    enviados = []
    for rel_path in ARQUIVOS_SINCRONIZADOS:
        arq_local = RAIZ_LOCAL / rel_path
        if not arq_local.exists():
            continue
        conteudo = arq_local.read_text(encoding="utf-8")
        tree_items.append({
            "path": rel_path.replace("\\", "/"),
            "mode": "100644",
            "type": "blob",
            "content": conteudo,
        })
        enviados.append(rel_path)

    print(f"[PUSH] Criando árvore Git na nuvem com {len(tree_items)} arquivos...")
    code, out, err = gh_api("POST", f"repos/{REPO}/git/trees", {
        "base_tree": base_tree_sha,
        "tree": tree_items,
    })
    if code != 0:
        print(f"[ERRO] Falha ao criar árvore Git: {err}")
        sys.exit(1)
    new_tree_sha = json.loads(out)["sha"]

    if new_tree_sha == base_tree_sha:
        print("[OK] Nenhuma alteração pendente — a nuvem já está 100% idêntica aos arquivos locais.")
        return

    code, out, err = gh_api("POST", f"repos/{REPO}/git/commits", {
        "message": mensagem,
        "tree": new_tree_sha,
        "parents": [commit_sha_atual],
    })
    if code != 0:
        print(f"[ERRO] Falha ao criar commit na nuvem: {err}")
        sys.exit(1)
    new_commit_sha = json.loads(out)["sha"]

    code, out, err = gh_api("PATCH", f"repos/{REPO}/git/refs/heads/{BRANCH}", {
        "sha": new_commit_sha,
        "force": False,
    })
    if code != 0:
        print(f"[ERRO] Falha ao atualizar branch {BRANCH}: {err}")
        sys.exit(1)

    print(f"[SUCESSO] Commit {new_commit_sha[:8]} publicado em https://github.com/{REPO}")
    print(f"          {len(enviados)} arquivos sincronizados com a nuvem.")


def pull_da_nuvem():
    print(f"[PULL] Baixando arquivos atualizados de {REPO} ({BRANCH})...")
    code, out, err = gh_api("GET", f"repos/{REPO}/git/trees/{BRANCH}?recursive=1")
    if code != 0:
        print(f"[ERRO] Falha ao listar árvore remota: {err}")
        sys.exit(1)
    tree = json.loads(out).get("tree", [])

    baixados = 0
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item["path"]
        # Baixa arquivos de código, memória, histórico de clippings e radar
        deve_baixar = (
            path in ARQUIVOS_SINCRONIZADOS
            or path.startswith("historico/")
            or path in ("clipping.html", "radar.html")
        )
        if not deve_baixar:
            continue

        code_b, out_b, _ = gh_api("GET", f"repos/{REPO}/git/blobs/{item['sha']}")
        if code_b != 0:
            continue
        blob_data = json.loads(out_b)
        raw_bytes = base64.b64decode(blob_data.get("content", ""))

        destino = RAIZ_LOCAL / path
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(raw_bytes)
        baixados += 1

        # Se for um arquivo historico/clipping_AAAA-MM-DD.html, espelha também em clipping/historico/
        if path.startswith("historico/"):
            esp = RAIZ_LOCAL / "clipping" / path
            esp.parent.mkdir(parents=True, exist_ok=True)
            esp.write_bytes(raw_bytes)

    print(f"[SUCESSO] {baixados} arquivos sincronizados da nuvem para {RAIZ_LOCAL}.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    acao = (sys.argv[1] if len(sys.argv) > 1 else "push").lower()
    if acao == "push":
        msg = sys.argv[2] if len(sys.argv) > 2 else "Sincroniza codigo-fonte e documentacao multi-agente com a nuvem"
        push_para_nuvem(msg)
    elif acao == "pull":
        pull_da_nuvem()
    else:
        print("Uso: python3.12 sincronizar_nuvem.py [push|pull] [mensagem]")

import os
import sys
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
PASTA_PROJETO = Path(__file__).parent.resolve()
PASTA_RADAR = PASTA_PROJETO.parent / "radar_participativo"
load_dotenv(PASTA_PROJETO / ".env")

import coletor
import curador
import renderizador

def obter_novos_processos_participativos_48h(api_key, em_github_actions=False):
    """Atualiza o Radar Participativo em modo contínuo (incluindo encerrados 72h e contadores) e retorna os lançamentos 48h."""
    try:
        if not PASTA_RADAR.exists():
            return [], None
        if str(PASTA_RADAR) not in sys.path:
            sys.path.insert(0, str(PASTA_RADAR))
        import coletor_participativo
        import curador_participativo
        import renderizador_participativo
        import publicador_web

        candidatos = coletor_participativo.coletar_processos_brasil_participativo()
        dossies = curador_participativo.curar_processos_participativos(candidatos, PASTA_RADAR, api_key=api_key)

        # Renderiza e publica o painel contínuo do Radar automaticamente junto com o Clipping
        _, caminho_radar_local = renderizador_participativo.gerar_painel_radar_html(dossies, PASTA_RADAR)
        if em_github_actions:
            import shutil
            shutil.copyfile(caminho_radar_local, PASTA_PROJETO.parent / "radar.html")
        else:
            publicador_web.publicar_arquivo_html(caminho_radar_local, "radar.html", "Radar Brasil Participativo (Contínuo)")

        recentes = [
            d for d in dossies
            if d.get("status_ciclo") == "LANCADO_48H"
            or (d.get("status_ciclo") == "PRE_PUBLICACAO" and d.get("data_atualizacao_iso", "")[:10] >= coletor.datetime.now().strftime("%Y-%m-%d"))
        ]
        caminho_radar_uri = "https://mdagavea.github.io/inteligencia-regulatoria/radar.html"
        return recentes, caminho_radar_uri
    except Exception as e:
        print(f"   [Aviso] Não foi possível consultar/atualizar o Radar Participativo: {e}")
        return [], "https://mdagavea.github.io/inteligencia-regulatoria/radar.html"


def edicao_de_hoje_ja_existe(hoje_iso: str) -> bool:
    """Verifica se a edição de hoje já foi gerada (localmente, na raiz do repositório ou no GitHub Pages)."""
    nome_arq = f"clipping_{hoje_iso}.html"
    if (PASTA_PROJETO / "historico" / nome_arq).exists():
        return True
    if (PASTA_PROJETO.parent / "historico" / nome_arq).exists():
        return True
    try:
        if str(PASTA_RADAR) not in sys.path:
            sys.path.insert(0, str(PASTA_RADAR))
        import publicador_web
        code, _, _ = publicador_web._gh_api("GET", f"repos/{publicador_web.REPO}/contents/historico/{nome_arq}")
        if code == 0:
            return True
    except Exception:
        pass
    return False


def executar_fluxo(abrir_navegador=True, destinatarios_override=None, skip_if_exists=False):
    em_github_actions = os.getenv("GITHUB_ACTIONS", "").lower() == "true"
    if em_github_actions:
        abrir_navegador = False

    hoje_iso = coletor.datetime.now().strftime("%Y-%m-%d")
    if skip_if_exists and edicao_de_hoje_ja_existe(hoje_iso):
        print(f"[INFO] A edição de hoje (clipping_{hoje_iso}.html) já foi gerada e publicada. Encerrando sem duplicidade.")
        return

    print("=" * 60)
    print("INICIANDO GERADOR DE CLIPPING REGULATORIO & FINANCEIRO")
    print("=" * 60)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "":
        print("\n[Aviso] GEMINI_API_KEY não encontrada — executando em modo de contingência determinístico (sem IA).")
        api_key = None

    # Na segunda-feira (weekday == 0), acumula as últimas 72h (sexta, sábado e domingo)
    eh_segunda = coletor.datetime.now().weekday() == 0
    janela_tempo = "72h" if eh_segunda else "24h"
    print(f"\n[1/5] Coletando matérias e newsletters nas 5 verticais (janela: {janela_tempo})...")
    noticias_brutas = coletor.fetch_all_raw_news(when=janela_tempo)
    print(f"   -> {len(noticias_brutas)} materias brutas encontradas.")

    print("\n[2/5] Processando curadoria e deduplicação com a IA (Gemini)...")
    dados_curados = curador.curar_noticias_com_gemini(noticias_brutas, api_key=api_key)

    total_curadas = sum(len(itens) for itens in dados_curados.values())
    print(f"   -> Curadoria concluida: {total_curadas} fatos de impacto selecionados.")

    print("\n[3/5] Verificando lançamentos de hoje/véspera no Brasil Participativo...")
    processos_48h, caminho_radar_uri = obter_novos_processos_participativos_48h(api_key, em_github_actions=em_github_actions)
    print(f"   -> {len(processos_48h)} processo(s) participativo(s) relevante(s) nas últimas 48h.")

    print("\n[4/5] Gerando Dashboard HTML 2x2...")
    caminho_data, caminho_atual = renderizador.gerar_html_dashboard(
        dados_curados,
        PASTA_PROJETO,
        processos_recentes=processos_48h,
        caminho_radar_html=caminho_radar_uri
    )
    print(f"   -> Arquivo salvo: {caminho_data}")
    print(f"   -> Versão atualizada: {caminho_atual}")

    print("\n[5/5] Publicando versão Web e Repositório Histórico no GitHub Pages...")
    try:
        import json
        import shutil
        hoje = coletor.datetime.now()
        data_fmt = hoje.strftime("%d/%m/%Y")
        dest_env = os.getenv("EMAIL_DESTINATARIOS", "")
        lista_dest = destinatarios_override if destinatarios_override is not None else [
            e.strip() for e in dest_env.split(",") if e.strip()
        ]
        payload_email = None
        if lista_dest:
            corpo_email = renderizador.gerar_html_email_resumo(dados_curados, data_fmt, processos_recentes=processos_48h)
            payload_email = {
                "assunto": f"🧭 Clipping Diário Executivo DECON/MPOR — {data_fmt}",
                "destinatarios": lista_dest,
                "corpo_html": corpo_email,
                "timestamp": hoje.isoformat(),
            }

        nome_arq_hist = Path(caminho_data).name
        caminho_cat_hist = Path(caminho_data).parent / "index.html"

        # Se estiver rodando dentro do checkout do repositório no GitHub Actions, grava direto na árvore do repo
        if em_github_actions:
            raiz_repo = PASTA_PROJETO.parent
            (raiz_repo / "historico").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(caminho_atual, raiz_repo / "clipping.html")
            shutil.copyfile(caminho_data, raiz_repo / "historico" / nome_arq_hist)
            if caminho_cat_hist.exists():
                shutil.copyfile(caminho_cat_hist, raiz_repo / "historico" / "index.html")
            if payload_email:
                (raiz_repo / "email_dispatch.json").write_text(
                    json.dumps(payload_email, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            print("   -> Arquivos preparados na raiz do repositório para commit e envio em nuvem.")
        else:
            if str(PASTA_RADAR) not in sys.path:
                sys.path.insert(0, str(PASTA_RADAR))
            import publicador_web
            url_web = publicador_web.publicar_arquivo_html(caminho_atual, "clipping.html", "Clipping Diário Atual")
            conteudo_hist = Path(caminho_data).read_text(encoding="utf-8")
            publicador_web.enviar_arquivo_github(f"historico/{nome_arq_hist}", conteudo_hist, f"Arquiva {nome_arq_hist} no histórico")

            if caminho_cat_hist.exists():
                conteudo_cat = caminho_cat_hist.read_text(encoding="utf-8")
                publicador_web.enviar_arquivo_github("historico/index.html", conteudo_cat, "Atualiza catálogo histórico de clippings")
                publicador_web.garantir_github_pages_ativo()

            if url_web:
                print(f"   -> Link Web Atual: {url_web}")
                print(f"   -> Link Histórico do Dia: https://mdagavea.github.io/inteligencia-regulatoria/historico/{nome_arq_hist}")
                print(f"   -> Catálogo de Edições: https://mdagavea.github.io/inteligencia-regulatoria/historico/index.html")

            if payload_email:
                ok_mail = publicador_web.enviar_arquivo_github(
                    "email_dispatch.json",
                    json.dumps(payload_email, ensure_ascii=False, indent=2),
                    f"Dispara boletim por e-mail ({data_fmt})",
                )
                if ok_mail:
                    print(f"   -> Disparo de e-mail acionado para: {', '.join(lista_dest)}")
    except Exception as e:
        print(f"   [Aviso] Falha ao publicar no GitHub Pages / E-mail: {e}")

    if abrir_navegador:
        print("\n[+] Abrindo dashboard no seu navegador padrao...")
        try:
            os.startfile(caminho_atual)
        except Exception:
            webbrowser.open(Path(caminho_atual).as_uri())

    print("\n[CONCLUIDO COM SUCESSO]")

if __name__ == '__main__':
    headless = ("--headless" in sys.argv) or ("--no-browser" in sys.argv)
    skip_existing = ("--skip-if-exists" in sys.argv) and ("--force" not in sys.argv)
    executar_fluxo(abrir_navegador=not headless, skip_if_exists=skip_existing)

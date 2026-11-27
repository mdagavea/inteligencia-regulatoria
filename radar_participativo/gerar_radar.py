import datetime
import html
import os
import sys
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

PASTA_PROJETO = Path(__file__).parent.resolve()
load_dotenv(PASTA_PROJETO / ".env")

import coletor_participativo
import coletor_estruturacao_leiloes
import coletor_sfn
import coletor_dou
import curador_participativo
import renderizador_participativo
import publicador_web
import validador_publicacao


def _normalizar_url_dedup(url: str) -> str:
    if not url:
        return ""
    return url.strip().split("?", 1)[0].split("#", 1)[0].rstrip("/").lower()


def _inserir_aviso_falha_dou_html(caminho_html, falhas_dou: list) -> bool:
    """Insere banner visível de aviso de falha na leitura do DOU logo após o cabeçalho do Radar."""
    if not falhas_dou:
        return False
    arq = Path(caminho_html)
    if not arq.exists():
        return False
    conteudo = arq.read_text(encoding="utf-8")
    if "</header>" not in conteudo:
        return False

    itens_li = []
    for f_dou in falhas_dou:
        data_br = str(f_dou.get("data", "")).replace("-", "/")
        secao = html.escape(str(f_dou.get("secao", "DO1")))
        erro = html.escape(str(f_dou.get("erro", "Falha desconhecida")))
        itens_li.append(f"<li><strong>{html.escape(data_br)} ({secao}):</strong> {erro}</li>")

    bloco_aviso = (
        '\n    <div class="context-banner" id="aviso-falha-dou" role="alert" '
        'style="background:#fef2f2;border:1px solid #fecaca;border-left:5px solid #dc2626;margin-bottom:14px;">\n'
        '      <div class="context-banner-text" style="color:#7f1d1d;">\n'
        '        <strong>⚠️ Aviso de Leitura do Diário Oficial (DOU):</strong> '
        'Não foi possível ler a edição oficial do DOU na última tentativa:\n'
        '        <ul style="margin:6px 0 0 18px;padding:0;">\n'
        + "\n".join(f"          {li}" for li in itens_li)
        + '\n        </ul>\n'
        '        <div style="margin-top:4px;font-size:0.8rem;">'
        'O radar voltará a tentar ler automaticamente esses dias nas próximas execuções. '
        'Os demais painéis e atos já coletados seguem exibidos normalmente.</div>\n'
        '      </div>\n'
        '    </div>'
    )

    novo_conteudo = conteudo.replace("</header>", "</header>" + bloco_aviso, 1)
    arq.write_text(novo_conteudo, encoding="utf-8")
    return True


def executar_radar(abrir_navegador=True, publicar=True):
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 72)
    print("INICIANDO RADAR DE INTELIGÊNCIA REGULATÓRIA — 4 ABAS (PARTICIPAÇÃO, EVTEAS, LEILÕES & SFN)")
    print("=" * 72)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "":
        print("\n[Aviso] GEMINI_API_KEY não definida — executando o Radar em modo factual sem IA.")
        api_key = None

    print("\n[1/6] Aba 1: Consultando Brasil Participativo + Portais Próprios (ANTT e ANTAQ)...")
    candidatos = coletor_participativo.coletar_processos_brasil_participativo()
    dossies = curador_participativo.curar_processos_participativos(candidatos, PASTA_PROJETO, api_key=api_key)
    print(f"   -> {len(dossies)} processos participativos estratégicos aprovados.")

    print("\n[2/6] Aba 2: Coletando e curando Estruturação, EVTEAs & Contratações (Infra S.A., PNCP, BNDES, LabTrans)...")
    brutos_est = coletor_estruturacao_leiloes.coletar_tudo_aba_estruturacao()
    itens_estruturacao = curador_participativo.curar_estruturacao_e_licitacoes(brutos_est, PASTA_PROJETO, api_key=api_key)
    print(f"   -> {len(itens_estruturacao)} itens de estruturação/contratação analisados.")

    print("\n[3/6] Aba 3: Atualizando Radar de Leilões & Outorgas (ANTAQ, ANAC, ANTT, B3 & Nacionais)...")
    itens_leiloes = coletor_estruturacao_leiloes.coletar_radar_leiloes()
    print(f"   -> {len(itens_leiloes)} leilões estratégicos monitorados na carteira.")

    print("\n[4/6] Aba 4: Coletando e filtrando SFN, Seguros & Capitais (SUSEP e CVM via termos_filtro.json)...")
    dados_sfn = coletor_sfn.coletar_tudo_aba_sfn()
    dados_sfn = curador_participativo.enriquecer_sfn_com_ia_lote(dados_sfn, PASTA_PROJETO, api_key=api_key)
    print(f"   -> {len(dados_sfn['aprovados'])} processos no filtro temático (+ {len(dados_sfn['fora_do_filtro'])} retidos fora do filtro e gravados em log).")

    print("\n[4.5/6] Integrando Atos Oficiais do DOU (PPI, CMN, Debêntures, FMM & Deliberações ANTAQ)...")
    falhas_dou = []
    try:
        cands_sombra = coletor_dou.executar_varredura_consultas_modo_sombra()
        falhas_dou = coletor_dou.obter_falhas_leitura_dou()
        print(f"   -> Varredura de consultas de ministérios no DOU: {len(cands_sombra)} novo(s) candidato(s) hoje.")
        if falhas_dou:
            print(f"   [Aviso DOU] {len(falhas_dou)} dia(s) com falha na leitura do DOU nesta execução:")
            for f_dou in falhas_dou:
                print(f"      - {f_dou.get('data', '')} ({f_dou.get('secao', 'DO1')}): {f_dou.get('erro', '')}")
    except Exception as e:
        falhas_dou.append({
            "data": datetime.date.today().strftime("%d-%m-%Y"),
            "secao": "DO1",
            "erro": str(e),
        })
        print(f"   [Aviso Consultas DOU] Falha na varredura diária (seguindo com lista acumulada existente): {e}")

    try:
        cards_dou = coletor_dou.obter_cards_dou_por_aba(usar_cache_se_disponivel=True)
        if cards_dou.get("participativo"):
            urls_bp = {}
            for d_bp in dossies:
                pid_bp = str(d_bp.get("id", ""))
                for u_cand in [d_bp.get("url", ""), d_bp.get("url_principal", "")] + [
                    doc.get("url", "") for doc in (d_bp.get("documentos") or [])
                ]:
                    u_norm = _normalizar_url_dedup(u_cand)
                    if u_norm and u_norm not in urls_bp:
                        urls_bp[u_norm] = pid_bp

            for card_dou in cards_dou["participativo"]:
                if str(card_dou.get("id", "")).startswith("DOU_MIN_"):
                    urls_dou = [
                        _normalizar_url_dedup(u)
                        for u in ([card_dou.get("url", ""), card_dou.get("url_principal", "")] + [
                            doc.get("url", "") for doc in (card_dou.get("documentos") or [])
                        ])
                    ]
                    pid_dup = next((urls_bp[u] for u in urls_dou if u and u in urls_bp), None)
                    if pid_dup is not None:
                        print(f"   -> cartão DOU omitido: já no Brasil Participativo #{pid_dup}")
                        continue
                dossies.append(card_dou)
        if cards_dou.get("estruturacao"):
            itens_estruturacao = cards_dou["estruturacao"] + itens_estruturacao
        if cards_dou.get("leiloes"):
            itens_leiloes.extend(cards_dou["leiloes"])
        if cards_dou.get("sfn"):
            dados_sfn["aprovados"] = cards_dou["sfn"] + dados_sfn["aprovados"]
        print(f"   -> {len(cards_dou.get('estruturacao', []))} atos na Estruturação, {len(cards_dou.get('sfn', []))} atos no SFN integrados.")
    except Exception as e:
        print(f"   [Aviso DOU] Falha ao integrar atos do DOU: {e}")

    print("\n[5/6] Renderizando Painel Executivo Unificado em 4 Abas (radar_atual.html)...")
    _, caminho_atual = renderizador_participativo.gerar_painel_radar_html(
        dossies,
        PASTA_PROJETO,
        itens_estruturacao=itens_estruturacao,
        itens_leiloes=itens_leiloes,
        dados_sfn=dados_sfn,
    )
    if falhas_dou and _inserir_aviso_falha_dou_html(caminho_atual, falhas_dou):
        print(f"   -> Aviso de falha do DOU inserido no topo do painel ({len(falhas_dou)} dia(s)).")
    print(f"   -> Painel contínuo atualizado: {caminho_atual}")

    print("\n[6/6] Publicando versão Web no GitHub Pages (Link Contínuo)...")
    bloqueado_trava = False
    if publicar:
        url_web = publicador_web.publicar_arquivo_html(caminho_atual, "radar.html", "Radar de Inteligência Regulatória — 4 Abas")
        if url_web:
            print(f"   -> Link Web atualizado: {url_web}")
        elif publicador_web.ULTIMO_BLOQUEIO_OCORREU:
            bloqueado_trava = True
    else:
        aprovado, violacoes, avisos = validador_publicacao.validar_arquivo_html(caminho_atual)
        validador_publicacao.emitir_relatorio_validacao(aprovado, violacoes, avisos, Path(caminho_atual).name)
        if not aprovado:
            publicador_web.registrar_status_bloqueio_radar(False, violacoes)
            bloqueado_trava = True
            print("   [BLOQUEIO] Validação reprovada pela trava de segurança editorial (--no-publish).")
        else:
            print("   [--no-publish] Validação aprovada; publicação web desativada nesta execução.")

    if abrir_navegador:
        print("\n[+] Abrindo painel no navegador padrão...")
        try:
            os.startfile(caminho_atual)
        except Exception:
            webbrowser.open(Path(caminho_atual).as_uri())

    if bloqueado_trava:
        print("\n[ENCERRADO COM ERRO] Publicação bloqueada pela trava editorial. Verifique ULTIMO_BLOQUEIO_RADAR.txt.")
        sys.exit(1)

    print("\n[CONCLUÍDO COM SUCESSO]")
    return dossies


if __name__ == "__main__":
    abrir = "--no-browser" not in sys.argv
    publicar = "--no-publish" not in sys.argv
    executar_radar(abrir_navegador=abrir, publicar=publicar)

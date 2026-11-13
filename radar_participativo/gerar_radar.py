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


def executar_radar(abrir_navegador=True):
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
    try:
        cards_dou = coletor_dou.obter_cards_dou_por_aba(usar_cache_se_disponivel=True)
        if cards_dou.get("participativo"):
            dossies.extend(cards_dou["participativo"])
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
    print(f"   -> Painel contínuo atualizado: {caminho_atual}")

    print("\n[6/6] Publicando versão Web no GitHub Pages (Link Contínuo)...")
    url_web = publicador_web.publicar_arquivo_html(caminho_atual, "radar.html", "Radar de Inteligência Regulatória — 4 Abas")
    if url_web:
        print(f"   -> Link Web atualizado: {url_web}")

    print("\n[Modo Sombra] Executando varredura diária de consultas no DOU (somente local, não publicado)...")
    try:
        cands_sombra = coletor_dou.executar_varredura_consultas_modo_sombra()
        print(f"   -> {len(cands_sombra)} candidato(s) identificado(s) hoje no modo sombra.")
    except Exception as e:
        print(f"   [Aviso Modo Sombra] Falha na varredura diária (radar não interrompido): {e}")

    if abrir_navegador:
        print("\n[+] Abrindo painel no navegador padrão...")
        try:
            os.startfile(caminho_atual)
        except Exception:
            webbrowser.open(Path(caminho_atual).as_uri())

    print("\n[CONCLUÍDO COM SUCESSO]")
    return dossies


if __name__ == "__main__":
    abrir = "--no-browser" not in sys.argv
    executar_radar(abrir_navegador=abrir)

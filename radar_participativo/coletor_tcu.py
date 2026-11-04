"""
Coletor e Construtor de Cards do TCU (Controle Externo - IN 81/2018 e IN 91/2022)
=================================================================================
Regras inegociáveis implementadas neste módulo:
1. Nenhum número de acórdão, processo, data, sumário ou URL é digitado no código.
   Todos os dados vêm exclusivamente da coleta na API oficial do TCU gravada em
   `cache_acordaos_tcu.json`, com a URL exata da consulta e a data da coleta.
2. Consumo mínimo da API do TCU:
   - Consulta no máximo 1 vez por semana (intervalo >= 7 dias), nunca na rodada diária;
   - Consulta apenas projetos sem acórdão de mérito e processos com acórdão nos últimos 90 dias;
   - Pausa de 4 segundos entre requisições + preservação de cookie de sessão;
   - Limite máximo de 20 requisições HTTP por rodada;
   - Circuit breaker imediato: se o firewall (WAF) retornar HTML ("Requisição rejeitada"),
     interrompe todas as consultas ao TCU na rodada, mantém o último valor válido no cache
     e marca "não consultado nesta rodada" para projetos sem cache anterior.
3. Agrupamento por processo (PROC):
   - Para cada processo vinculado, exibe o acórdão de mérito principal em destaque
     e lista os demais acórdãos do processo em ordem cronológica.
   - Acórdãos de relação ("ACÓRDÃO DE RELAÇÃO" no título/tipo) aparecem marcados como
     "Acórdão de Relação" e nunca acionam destaque de "novo".
"""

import http.cookiejar
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PASTA_RADAR = Path(__file__).parent.resolve()
ARQUIVO_APELIDOS_TCU = PASTA_RADAR / "apelidos_projetos_tcu.json"
ARQUIVO_CACHE_TCU = PASTA_RADAR / "cache_acordaos_tcu.json"
ARQUIVO_TERMOS_SELOS = PASTA_RADAR / "termos_selos_estruturacao.json"

HEADERS_TCU = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://pesquisa.apps.tcu.gov.br/pesquisa/acordao-completo",
}


def strip_html(texto: Optional[str]) -> str:
    if not texto:
        return ""
    return re.sub(r"<[^>]+>", "", str(texto)).strip()


def parse_data_br(dt_str: str) -> Optional[date]:
    if not dt_str:
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", str(dt_str))
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def parse_data_iso(dt_iso: str) -> Optional[date]:
    if not dt_iso:
        return None
    try:
        return datetime.strptime(dt_iso[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def eh_acordao_relacao(doc: Dict) -> bool:
    titulo = strip_html(doc.get("TITULO")).upper()
    tipo = strip_html(doc.get("TIPO")).upper()
    return ("RELAÇÃO" in titulo) or ("RELACAO" in titulo) or ("RELAÇÃO" in tipo) or ("RELACAO" in tipo)


def extrair_sumario_efetivo(doc: Dict) -> Tuple[str, str]:
    """
    Retorna (texto_sumario, origem) priorizando o campo SUMARIO;
    quando vazio, aceita o bloco 'SUMÁRIO:' no início do VOTO (ou SUMARIO_VOTO já extraído).
    """
    sumario = strip_html(doc.get("SUMARIO")).strip()
    if sumario:
        return re.sub(r"\s+", " ", sumario), "SUMARIO"
    sumario_voto_cache = strip_html(doc.get("SUMARIO_VOTO")).strip()
    if sumario_voto_cache:
        return re.sub(r"\s+", " ", sumario_voto_cache), "VOTO(SUMÁRIO:)"
    voto = strip_html(doc.get("VOTO"))
    if voto:
        m = re.search(r"(SUM[ÁA]RIO\s*:\s*.{1,600})", voto, flags=re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip(), "VOTO(SUMÁRIO:)"
    return "", "VAZIO"


def texto_casa_apelido(texto: str, apelidos: List[str]) -> Optional[str]:
    if not texto:
        return None
    for ap in apelidos:
        padrao = r"(?<!\w)" + re.escape(ap) + r"(?!\w)"
        if re.search(padrao, texto, flags=re.IGNORECASE):
            return ap
    return None


def carregar_config_apelidos() -> Dict:
    if not ARQUIVO_APELIDOS_TCU.exists():
        return {"tipos_processo_aceitos": [], "projetos": {}}
    return json.loads(ARQUIVO_APELIDOS_TCU.read_text(encoding="utf-8"))


def carregar_cache_tcu() -> Dict:
    if not ARQUIVO_CACHE_TCU.exists():
        return {
            "ultima_consulta_tcu_iso": "",
            "intervalo_minimo_dias": 7,
            "max_consultas_por_rodada": 20,
            "pausa_segundos_entre_consultas": 4.0,
            "bloqueio_waf_ultima_rodada": False,
            "status_projetos": {},
            "acordaos": {},
        }
    return json.loads(ARQUIVO_CACHE_TCU.read_text(encoding="utf-8"))


def salvar_cache_tcu(cache: Dict) -> None:
    ARQUIVO_CACHE_TCU.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


class BloqueioWafTCUError(Exception):
    """Exceção lançada quando o WAF do TCU retorna 'Requisição rejeitada' (HTML) ou falha de rede."""


# Regra: só vale acórdão do Plenário (o mesmo número se repete nas Câmaras e em acórdãos de relação).
FILTRO_COLEGIADO_PLENARIO = 'COLEGIADO:"Plenário"'


def montar_filtro_acordao_plenario(numero, ano) -> str:
    """Ex.: NUMACORDAO:2316 ANOACORDAO:2025 COLEGIADO:"Plenário" (o urlencode é feito em _requisitar_api_tcu)."""
    return f'NUMACORDAO:{int(numero)} ANOACORDAO:{int(ano)} COLEGIADO:"Plenário"'


def _requisitar_api_tcu(opener: urllib.request.OpenerDirector, termo: str, inicio: int, pausa_s: float, filtro: str = FILTRO_COLEGIADO_PLENARIO) -> Tuple[str, Dict]:
    if pausa_s > 0:
        time.sleep(pausa_s)
    parametros = {
        "quantidade": "10",
        "inicio": str(inicio),
    }
    if termo:
        parametros["termo"] = termo
    if filtro:
        # Um único parâmetro "filtro": todos os campos juntos, separados por espaço.
        parametros["filtro"] = filtro
    params = urllib.parse.urlencode(parametros)
    url = f"https://pesquisa.apps.tcu.gov.br/rest/publico/base/acordao-completo/documento?{params}"
    req = urllib.request.Request(url, headers=HEADERS_TCU)
    try:
        with opener.open(req, timeout=20) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            corpo = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise BloqueioWafTCUError(f"Falha HTTP/rede na consulta ao TCU ({e})")

    if "text/html" in ctype or "<html" in corpo[:300].lower() or "rejeitada" in corpo[:600].lower():
        raise BloqueioWafTCUError("Firewall do TCU retornou página HTML 'Requisição rejeitada'")

    try:
        dados = json.loads(corpo)
    except Exception as e:
        raise BloqueioWafTCUError(f"Resposta da API do TCU não é JSON válido ({e})")

    return url, dados


def atualizar_cache_tcu_se_necessario(forcar: bool = False) -> Dict:
    """
    Atualiza `cache_acordaos_tcu.json` respeitando rigorosamente a política de consumo mínimo:
    - No máximo 1 vez por semana (intervalo >= 7 dias), exceto se `forcar=True`;
    - Consulta apenas projetos sem acórdão de mérito e processos com acórdão nos últimos 90 dias;
    - Limite estrito de 20 consultas por rodada e pausa entre consultas;
    - Se houver bloqueio de WAF ("Requisição rejeitada"), para imediatamente na rodada.
    """
    cache = carregar_cache_tcu()
    cfg = carregar_config_apelidos()
    hoje = date.today()
    hoje_iso = hoje.isoformat()

    ult_dt = parse_data_iso(cache.get("ultima_consulta_tcu_iso", ""))
    intervalo_min = int(cache.get("intervalo_minimo_dias", 7))
    max_consultas = int(cache.get("max_consultas_por_rodada", 20))
    pausa_s = float(cache.get("pausa_segundos_entre_consultas", 4.0))

    if not forcar and ult_dt is not None and (hoje - ult_dt).days < intervalo_min:
        return cache

    tipos_aceitos = set(cfg.get("tipos_processo_aceitos", []))
    projetos_cfg = cfg.get("projetos", {})
    acordaos_cache = cache.setdefault("acordaos", {})
    status_projetos = cache.setdefault("status_projetos", {})

    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    consultas_feitas = 0
    bloqueado_waf = False

    # 1. Identificar projetos sem acórdão de mérito e processos com acórdão nos últimos 90 dias
    for cod_proj, pinfo in projetos_cfg.items():
        if bloqueado_waf or consultas_feitas >= max_consultas:
            break

        acordaos_do_proj = [a for a in acordaos_cache.values() if a.get("codigo_projeto") == cod_proj]
        meritos_do_proj = [a for a in acordaos_do_proj if not eh_acordao_relacao(a)]

        # Se já tem acórdão de mérito, só consulta os processos cujo último acórdão tenha <= 90 dias
        if meritos_do_proj:
            procs_recentes = set()
            for a in acordaos_do_proj:
                dt_sess = parse_data_br(a.get("DATASESSAO", ""))
                if dt_sess and (hoje - dt_sess).days <= 90:
                    procs_recentes.add(a.get("PROC"))
            for proc_num in sorted(procs_recentes):
                if not proc_num or bloqueado_waf or consultas_feitas >= max_consultas:
                    break
                for idx in range(3):
                    if consultas_feitas >= max_consultas:
                        break
                    try:
                        consultas_feitas += 1
                        url_c, dados = _requisitar_api_tcu(opener, f'"{proc_num}"', idx, pausa_s)
                    except BloqueioWafTCUError as err:
                        print(f"   ⚠️ [TCU] {err}. Interrompendo consultas ao TCU nesta rodada.")
                        bloqueado_waf = True
                        break
                    docs = dados.get("documentos", [])
                    if not docs:
                        break
                    for d in docs:
                        if strip_html(d.get("PROC")) == proc_num and strip_html(d.get("TIPOPROCESSO")) in tipos_aceitos:
                            _gravar_doc_no_cache(acordaos_cache, d, cod_proj, url_c, hoje_iso, pinfo.get("apelidos_validacao_vinculo", []))
                    if idx + 1 >= (dados.get("quantidadeEncontrada") or 0):
                        break
            continue

        # Projeto sem acórdão de mérito: buscar pelos termos configurados
        encontrou_no_projeto = False
        for termo in pinfo.get("termos_busca_api", []):
            if bloqueado_waf or consultas_feitas >= max_consultas:
                break
            for idx in range(2):
                if consultas_feitas >= max_consultas:
                    break
                try:
                    consultas_feitas += 1
                    url_c, dados = _requisitar_api_tcu(opener, termo, idx, pausa_s)
                except BloqueioWafTCUError as err:
                    print(f"   ⚠️ [TCU] {err}. Interrompendo consultas ao TCU nesta rodada.")
                    bloqueado_waf = True
                    break
                docs = dados.get("documentos", [])
                if not docs:
                    break
                for d in docs:
                    if strip_html(d.get("TIPOPROCESSO")) not in tipos_aceitos:
                        continue
                    sum_txt, _ = extrair_sumario_efetivo(d)
                    ac_txt = strip_html(d.get("ACORDAO"))
                    ap_casado = texto_casa_apelido(f"{sum_txt} || {ac_txt}", pinfo.get("apelidos_validacao_vinculo", []))
                    if ap_casado:
                        _gravar_doc_no_cache(acordaos_cache, d, cod_proj, url_c, hoje_iso, pinfo.get("apelidos_validacao_vinculo", []))
                        encontrou_no_projeto = True
                if idx + 1 >= (dados.get("quantidadeEncontrada") or 0):
                    break

        if not bloqueado_waf:
            procs_proj = sorted({a.get("PROC") for a in acordaos_cache.values() if a.get("codigo_projeto") == cod_proj and a.get("PROC")})
            status_projetos[cod_proj] = {
                "status_consulta": "LOCALIZADO" if (encontrou_no_projeto or procs_proj) else "NAO_LOCALIZADO",
                "data_coleta_iso": hoje_iso,
                "termos_buscados": pinfo.get("termos_busca_api", []),
                "processos": procs_proj,
            }
        elif cod_proj not in status_projetos:
            status_projetos[cod_proj] = {
                "status_consulta": "NAO_CONSULTADO_NESTA_RODADA",
                "data_coleta_iso": hoje_iso,
                "termos_buscados": pinfo.get("termos_busca_api", []),
                "processos": [],
            }

    cache["bloqueio_waf_ultima_rodada"] = bloqueado_waf
    if not bloqueado_waf:
        cache["ultima_consulta_tcu_iso"] = hoje_iso
    salvar_cache_tcu(cache)
    return cache


def _gravar_doc_no_cache(acordaos_cache: Dict, d: Dict, cod_proj: str, url_c: str, data_iso: str, apelidos: List[str]) -> None:
    key = d.get("KEY")
    if not key:
        return
    sum_txt, sum_orig = extrair_sumario_efetivo(d)
    ac_txt = re.sub(r"\s+", " ", strip_html(d.get("ACORDAO"))).strip()
    ap = texto_casa_apelido(f"{sum_txt} || {ac_txt}", apelidos) or f"mesmo processo ({strip_html(d.get('PROC'))})"
    acordaos_cache[key] = {
        "KEY": key,
        "codigo_projeto": cod_proj,
        "NUMACORDAO": str(d.get("NUMACORDAO") or ""),
        "ANOACORDAO": str(d.get("ANOACORDAO") or ""),
        "COLEGIADO": strip_html(d.get("COLEGIADO")),
        "DATASESSAO": strip_html(d.get("DATASESSAO")),
        "PROC": strip_html(d.get("PROC")),
        "TIPOPROCESSO": strip_html(d.get("TIPOPROCESSO")),
        "TITULO": strip_html(d.get("TITULO")),
        "TIPO": strip_html(d.get("TIPO")),
        "RELATOR": strip_html(d.get("RELATOR")),
        "UNIDADETECNICA": strip_html(d.get("UNIDADETECNICA")),
        "URLARQUIVOPDF": strip_html(d.get("URLARQUIVOPDF")),
        "SUMARIO": strip_html(d.get("SUMARIO")),
        "SUMARIO_VOTO": sum_txt if sum_orig == "VOTO(SUMÁRIO:)" else "",
        "ACORDAO": ac_txt[:600],
        "url_consulta": url_c,
        "data_coleta_iso": data_iso,
        "apelido_casado": ap,
        "origem_sumario": sum_orig,
    }


def agrupar_acordaos_por_processo(codigo_projeto: Optional[str] = None) -> Dict[str, List[Dict]]:
    """
    Lê `cache_acordaos_tcu.json` e agrupa os acórdãos por número de processo (`PROC`),
    ordenados cronologicamente (do mais antigo ao mais recente).
    """
    cache = carregar_cache_tcu()
    acordaos = cache.get("acordaos", {})
    por_proc: Dict[str, List[Dict]] = {}
    for ac in acordaos.values():
        if codigo_projeto and ac.get("codigo_projeto") != codigo_projeto:
            continue
        proc = ac.get("PROC")
        if not proc:
            continue
        por_proc.setdefault(proc, []).append(ac)

    for proc, lista in por_proc.items():
        lista.sort(key=lambda x: parse_data_br(x.get("DATASESSAO", "")) or date.min)
    return por_proc


def obter_etapa_tcu_projeto(codigo_ativo: str) -> Dict:
    """
    Retorna os dados estruturados do campo 'Etapa TCU' para um card da Aba 3 (Leilões & Outorgas),
    montados exclusivamente a partir do `cache_acordaos_tcu.json`.
    """
    cache = carregar_cache_tcu()
    cfg = carregar_config_apelidos()
    projetos_cfg = cfg.get("projetos", {})

    # Projetos de rodovias/energia que não fazem parte do escopo TCU Portos/Aeroportos/Hidrovias
    if codigo_ativo not in projetos_cfg:
        return {"aplicavel": False}

    st_info = cache.get("status_projetos", {}).get(codigo_ativo, {})
    por_proc = agrupar_acordaos_por_processo(codigo_ativo)

    if not por_proc:
        status_c = st_info.get("status_consulta", "NAO_LOCALIZADO")
        if status_c == "NAO_CONSULTADO_NESTA_RODADA":
            return {
                "aplicavel": True,
                "status": "NAO_CONSULTADO_NESTA_RODADA",
                "rotulo_curto": "Não consultado nesta rodada",
                "termos_buscados": st_info.get("termos_buscados", []),
                "processos": [],
            }
        return {
            "aplicavel": True,
            "status": "NAO_LOCALIZADO",
            "rotulo_curto": "Não localizado",
            "termos_buscados": st_info.get("termos_buscados", projetos_cfg.get(codigo_ativo, {}).get("termos_busca_api", [])),
            "processos": [],
        }

    processos_formatados = []
    for proc_num, lista_ac in por_proc.items():
        meritos = [a for a in lista_ac if not eh_acordao_relacao(a)]
        ac_principal = meritos[0] if meritos else lista_ac[0]
        desdobramentos = [a for a in lista_ac if a.get("KEY") != ac_principal.get("KEY")]
        processos_formatados.append({
            "proc": proc_num,
            "tipo_processo": ac_principal.get("TIPOPROCESSO", ""),
            "acordao_principal": ac_principal,
            "desdobramentos": desdobramentos,
        })

    return {
        "aplicavel": True,
        "status": "ACORDAO_PROFERIDO",
        "rotulo_curto": "Acórdão proferido",
        "data_coleta_iso": st_info.get("data_coleta_iso", cache.get("ultima_consulta_tcu_iso", "")),
        "processos": processos_formatados,
    }


def gerar_cards_tcu_aba_estruturacao() -> List[Dict]:
    """
    Gera os cards de Controle Externo (TCU - tipo (e)) para a Aba 2 (Estruturação, EVTEAs & Contratações),
    agrupados por processo (PROC) e construídos 100% a partir de `cache_acordaos_tcu.json`.
    """
    cache = carregar_cache_tcu()
    cfg = carregar_config_apelidos()
    projetos_cfg = cfg.get("projetos", {})
    por_proc = agrupar_acordaos_por_processo()
    hoje = date.today()

    cards: List[Dict] = []
    for proc_num, lista_ac in por_proc.items():
        meritos = [a for a in lista_ac if not eh_acordao_relacao(a)]
        ac_principal = meritos[0] if meritos else lista_ac[0]
        cod_proj = ac_principal.get("codigo_projeto", "")
        nome_proj = projetos_cfg.get(cod_proj, {}).get("nome_projeto", cod_proj)

        # Determinar setor para filtro visual da Aba 2
        if cod_proj in ("GIG-GALEAO", "AMPLIAR-BLOCOS"):
            setor = "aeroportos"
            setor_nome = "✈️ Aeroportos"
        elif cod_proj == "HIDROVIA-PARAGUAI":
            setor = "hidrovias"
            setor_nome = "🚢 Hidrovias"
        else:
            setor = "portos"
            setor_nome = "⚓ Portos"

        # Último ato de mérito vs último ato geral (Acórdão de Relação não gera destaque de 'novo')
        ult_ac_geral = lista_ac[-1]
        ult_ac_merito = meritos[-1] if meritos else None
        dt_ult_merito = parse_data_br(ult_ac_merito.get("DATASESSAO", "")) if ult_ac_merito else None
        dt_ult_geral = parse_data_br(ult_ac_geral.get("DATASESSAO", "")) or date.min

        tem_merito_recente_90d = bool(dt_ult_merito and (hoje - dt_ult_merito).days <= 90)

        sumario_princ, orig_sum = extrair_sumario_efetivo(ac_principal)
        texto_base_princ = sumario_princ if sumario_princ else ac_principal.get("ACORDAO", "")

        num_princ = f"Acórdão {ac_principal['NUMACORDAO']}/{ac_principal['ANOACORDAO']}-{ac_principal['COLEGIADO']}"
        data_princ = ac_principal.get("DATASESSAO", "")
        tipo_proc = ac_principal.get("TIPOPROCESSO", "")
        unidade_tec = ac_principal.get("UNIDADETECNICA", "")

        # Montar histórico cronológico dos demais acórdãos do mesmo processo
        linhas_historico = []
        documentos_card = [
            {
                "rotulo": f"⚖️ {num_princ} ({data_princ}) — Mérito Principal",
                "url": ac_principal.get("URLARQUIVOPDF") or f"https://pesquisa.apps.tcu.gov.br/documento/acordao-completo/*/KEY:%22{ac_principal['KEY']}%22",
                "categoria": "TCU_ACORDAO",
            }
        ]

        for ac_item in lista_ac:
            if ac_item.get("KEY") == ac_principal.get("KEY"):
                continue
            eh_rel = eh_acordao_relacao(ac_item)
            marca_rel = " [ACÓRDÃO DE RELAÇÃO — sem destaque de novo]" if eh_rel else " [Desdobramento de Mérito]"
            sum_it, _ = extrair_sumario_efetivo(ac_item)
            resumo_it = sum_it if sum_it else ac_item.get("ACORDAO", "")
            num_it = f"Acórdão {ac_item['NUMACORDAO']}/{ac_item['ANOACORDAO']}-{ac_item['COLEGIADO']}"
            dt_it = ac_item.get("DATASESSAO", "")
            linhas_historico.append(f"• {dt_it} — {num_it}{marca_rel}: {resumo_it[:240]}")
            documentos_card.append({
                "rotulo": f"📄 {num_it} ({dt_it}){' • Relação' if eh_rel else ''}",
                "url": ac_item.get("URLARQUIVOPDF") or f"https://pesquisa.apps.tcu.gov.br/documento/acordao-completo/*/KEY:%22{ac_item['KEY']}%22",
                "categoria": "TCU_ACORDAO",
            })

        resumo_objeto = (
            f"Processo TC {proc_num} ({tipo_proc}) • Unidade Técnica: {unidade_tec} "
            f"• Acórdão de Mérito Principal: {num_princ} (Sessão de {data_princ}). "
            f"Texto oficial ({orig_sum}): \"{texto_base_princ}\""
        )

        destaque_cronologia = (
            "Histórico cronológico de deliberações no processo: " + " | ".join(linhas_historico)
            if linhas_historico
            else f"Deliberação única localizada no processo TC {proc_num}: {num_princ} ({data_princ})."
        )
        destaque_cronologia += (
            f" [Coleta automática na API do TCU em {ac_principal.get('data_coleta_iso')} • "
            f"Vínculo validado pelo termo '{ac_principal.get('apelido_casado')}']"
        )

        cards.append({
            "id": f"TCU_PROC_{re.sub(r'[^0-9]', '', proc_num)}",
            "prioridade": "D_TCU",
            "prioridade_escopo": "PRIORIDADE_A_DESTAQUE" if tem_merito_recente_90d else "PRIORIDADE_A",
            "prioridade_ordem": 1,
            "categoria_item": "CONTROLE_EXTERNO_TCU",
            "tipo_documento_codigo": "(e) controle externo (TCU)",
            "modalidade": f"(e) Controle Externo TCU • {tipo_proc}",
            "setor": setor,
            "setor_nome": setor_nome,
            "estruturador_sigla": "TCU Plenário",
            "estruturador_nome": f"Tribunal de Contas da União — {unidade_tec}",
            "numero_edital": f"TC {proc_num} • {num_princ}",
            "titulo": f"{nome_proj} — {tipo_proc} (TC {proc_num})",
            "titulo_executivo": f"TCU Plenário — TC {proc_num} ({num_princ}) — {nome_proj}",
            "objeto_resumo": resumo_objeto,
            "escopo_sintetico": resumo_objeto,
            "analise_riscos_segurabilidade": destaque_cronologia,
            "destaque_matriz_seguros": destaque_cronologia,
            "ficha_documental_verificada": True,
            "valor_estimado": 0.0,
            "valor_formatado": num_princ,
            "data_publicacao": dt_ult_geral.isoformat() if dt_ult_geral != date.min else "",
            "data_publicacao_br": f"Último ato: {ult_ac_geral.get('DATASESSAO', '')} (Mérito: {data_princ})",
            "data_fim_iso": "",
            "data_fim_br": f"🆕 Mérito recente ({ult_ac_merito.get('DATASESSAO', '')})" if tem_merito_recente_90d else f"TC {proc_num} ({data_princ})",
            "dias_restantes": None,
            "data_ultimo_ato_iso": dt_ult_geral.isoformat() if dt_ult_geral != date.min else "",
            "data_ultimo_ato_merito_iso": dt_ult_merito.isoformat() if dt_ult_merito else "",
            "tem_ato_novo_90d": tem_merito_recente_90d,
            "contem_acordao_relacao": any(eh_acordao_relacao(a) for a in lista_ac),
            "prazo_limite_br": f"TC {proc_num}",
            "status_certame": "EM_ANDAMENTO_TCU",
            "tem_matriz_seguros": False,
            "url": ac_principal.get("URLARQUIVOPDF") or f"https://pesquisa.apps.tcu.gov.br/documento/acordao-completo/*/KEY:%22{ac_principal['KEY']}%22",
            "documentos": documentos_card,
            "_validacao_tcu": {
                "proc": proc_num,
                "codigo_projeto": cod_proj,
                "keys_acordaos": [a.get("KEY") for a in lista_ac],
                "url_consulta": ac_principal.get("url_consulta", ""),
                "data_coleta_iso": ac_principal.get("data_coleta_iso", ""),
            },
        })

    return cards

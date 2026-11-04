"""
Validador Automático Pré-Renderização do Radar (Abas 2 e 3)
===========================================================
Executa checagem automática obrigatória antes de renderizar o painel HTML:
1. Para cards com selos por vertical (`selos_verticais`), confere se cada termo de selo
   existe em `termos_selos_estruturacao.json` e no texto extraído do documento;
2. Confere se o destaque/selo "novo" (`tem_ato_novo_90d`) só aparece quando a data do
   último ato de mérito está a até 90 dias da data da rodada (e nunca para Acórdão de Relação);
3. Para os cards do TCU (Aba 2) e para o campo `etapa_tcu` (Aba 3), confere contra o
   `cache_acordaos_tcu.json`:
   - existência da `KEY` no cache bruto da API;
   - correspondência exata do número do acórdão (`NUMACORDAO/ANOACORDAO`), processo (`PROC`) e data (`DATASESSAO`);
   - presença de URL oficial da consulta (`url_consulta`) e data da coleta (`data_coleta_iso`);
   - link apontando para o próprio acórdão (`URLARQUIVOPDF` ou `KEY`), nunca página genérica de busca;
   - confirmação do apelido do projeto (`apelidos_projetos_tcu.json`) em `SUMARIO`, `SUMARIO_VOTO` ou `ACORDAO`.

Qualquer card que falhar na validação é bloqueado (não vai para o HTML) e registrado em
`log_rejeitados_validador.txt`.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple

from coletor_tcu import (
    ARQUIVO_APELIDOS_TCU,
    ARQUIVO_CACHE_TCU,
    ARQUIVO_TERMOS_SELOS,
    carregar_cache_tcu,
    carregar_config_apelidos,
    eh_acordao_relacao,
    parse_data_br,
    parse_data_iso,
    texto_casa_apelido,
)

PASTA_RADAR = Path(__file__).parent.resolve()
ARQUIVO_LOG_REJEITADOS = PASTA_RADAR / "log_rejeitados_validador.txt"


def _carregar_termos_selos() -> Dict[str, List[str]]:
    if not ARQUIVO_TERMOS_SELOS.exists():
        return {}
    dados = json.loads(ARQUIVO_TERMOS_SELOS.read_text(encoding="utf-8"))
    if isinstance(dados, dict) and "selos" in dados:
        return {k: v.get("termos", []) for k, v in dados["selos"].items() if isinstance(v, dict)}
    return {k: v for k, v in dados.items() if isinstance(v, list)}


def _validar_acordao_contra_cache(key: str, cache_acordaos: Dict, projetos_cfg: Dict) -> List[str]:
    erros: List[str] = []
    if key not in cache_acordaos:
        erros.append(f"KEY '{key}' não existe em cache_acordaos_tcu.json")
        return erros

    ac = cache_acordaos[key]
    for campo_obrig in ("NUMACORDAO", "ANOACORDAO", "PROC", "DATASESSAO", "url_consulta", "data_coleta_iso"):
        if not str(ac.get(campo_obrig) or "").strip():
            erros.append(f"Acórdão {key} sem campo obrigatório '{campo_obrig}' no cache")

    url_pdf = str(ac.get("URLARQUIVOPDF") or "").strip()
    if not url_pdf or ("pesquisa.apps.tcu.gov.br/pesquisa" in url_pdf and "KEY" not in url_pdf):
        erros.append(f"Acórdão {key} possui URL inválida ou de busca genérica: '{url_pdf}'")

    cod_proj = ac.get("codigo_projeto", "")
    apelidos = projetos_cfg.get(cod_proj, {}).get("apelidos_validacao_vinculo", [])
    texto_alvo = f"{ac.get('SUMARIO', '')} || {ac.get('SUMARIO_VOTO', '')} || {ac.get('ACORDAO', '')}"
    # Para desdobramentos do mesmo processo já vinculado pelo acórdão principal, ou o próprio acórdão casa apelido,
    # ou outro acórdão do mesmo PROC no cache casa apelido.
    if not texto_casa_apelido(texto_alvo, apelidos):
        proc = ac.get("PROC", "")
        irmas_validas = [
             irm for irm in cache_acordaos.values()
            if irm.get("PROC") == proc
            and irm.get("codigo_projeto") == cod_proj
            and texto_casa_apelido(
                f"{irm.get('SUMARIO', '')} || {irm.get('SUMARIO_VOTO', '')} || {irm.get('ACORDAO', '')}",
                apelidos,
            )
        ]
        if not irmas_validas:
            erros.append(
                f"Acórdão {key} (TC {proc}) não contém nenhum apelido válido de '{cod_proj}' "
                f"em SUMARIO, SUMARIO_VOTO ou ACORDAO"
            )
    return erros


def validar_card_aba_estruturacao(
    card: Dict,
    hoje: date,
    termos_selos_cfg: Dict[str, List[str]],
    cache_acordaos: Dict,
    projetos_cfg: Dict,
) -> List[str]:
    erros: List[str] = []

    # 1. Validar destaque 'novo' (máximo 90 dias da data da rodada e nunca de Acórdão de Relação isolado)
    if card.get("tem_ato_novo_90d"):
        dt_ref_iso = card.get("data_ultimo_ato_merito_iso") or card.get("data_ultimo_ato_iso") or card.get("data_publicacao") or ""
        dt_ref = parse_data_iso(dt_ref_iso)
        if not dt_ref:
            erros.append("Card marcado com destaque 'novo' (tem_ato_novo_90d=True), mas sem data de último ato válida")
        elif (hoje - dt_ref).days > 90:
            erros.append(
                f"Card marcado com destaque 'novo', mas último ato ({dt_ref.isoformat()}) tem {(hoje - dt_ref).days} dias (> 90 dias)"
            )

    # 2. Validar selos por vertical (se presentes no card)
    selos_card = card.get("selos_verticais") or []
    texto_extraido = (
        f"{card.get('texto_extraido_documento', '')} "
        f"{card.get('objeto_resumo', '')} "
        f"{card.get('destaque_matriz_seguros', '')}"
    )
    for selo in selos_card:
        chave_selo = selo.get("chave") or selo.get("vertical")
        termo_casado = (selo.get("termo") or "").strip()
        if not chave_selo or chave_selo not in termos_selos_cfg:
            erros.append(f"Selo '{chave_selo}' não existe em termos_selos_estruturacao.json")
            continue
        lista_termos_validos = [t.lower() for t in termos_selos_cfg.get(chave_selo, [])]
        if termo_casado.lower() not in lista_termos_validos:
            erros.append(f"Termo de selo '{termo_casado}' não consta na lista oficial do selo '{chave_selo}'")
        if termo_casado and not re.search(re.escape(termo_casado), texto_extraido, flags=re.IGNORECASE):
            erros.append(f"Termo de selo '{termo_casado}' não foi localizado no texto extraído do card")

    # 3. Se for card de Controle Externo (TCU), conferir número, processo, URL e vínculo contra cache_acordaos_tcu.json
    if card.get("categoria_item") == "CONTROLE_EXTERNO_TCU" or card.get("_validacao_tcu"):
        meta_tcu = card.get("_validacao_tcu") or {}
        proc_card = meta_tcu.get("proc") or ""
        keys_card = meta_tcu.get("keys_acordaos") or []
        if not proc_card or not keys_card:
            erros.append("Card do TCU sem metadados obrigatórios de rastreabilidade (_validacao_tcu.proc / keys_acordaos)")
        for k in keys_card:
            erros.extend(_validar_acordao_contra_cache(k, cache_acordaos, projetos_cfg))
            if k in cache_acordaos:
                ac = cache_acordaos[k]
                if ac.get("PROC") != proc_card:
                    erros.append(
                        f"Processo do card ({proc_card}) diverge do processo gravado na API ({ac.get('PROC')}) para {k}"
                    )
                num_str = f"{ac.get('NUMACORDAO')}/{ac.get('ANOACORDAO')}"
                texto_card = f"{card.get('numero_edital', '')} {card.get('objeto_resumo', '')} {card.get('destaque_matriz_seguros', '')}"
                if num_str not in texto_card:
                    erros.append(f"Número do acórdão {num_str} ({k}) não bate com o texto do card")

    return erros


def validar_leiloes_etapa_tcu(
    leiloes: List[Dict],
    cache_acordaos: Dict,
    projetos_cfg: Dict,
) -> Tuple[List[Dict], List[str]]:
    """
    Valida o campo `etapa_tcu` de cada card da Aba 3 contra `cache_acordaos_tcu.json`.
    Se algum processo/acórdão em `etapa_tcu` falhar na checagem, o campo é revertido para
    'não localizado' e a falha é gravada no log.
    """
    logs_falha: List[str] = []
    for item in leiloes:
        etapa = item.get("etapa_tcu")
        if not etapa or not etapa.get("aplicavel"):
            continue
        if etapa.get("status") != "ACORDAO_PROFERIDO":
            continue

        erros_item: List[str] = []
        for p in etapa.get("processos", []):
            proc_num = p.get("proc", "")
            ac_princ = p.get("acordao_principal") or {}
            todos_ac = [ac_princ] + (p.get("desdobramentos") or [])
            for ac in todos_ac:
                k = ac.get("KEY", "")
                erros_item.extend(_validar_acordao_contra_cache(k, cache_acordaos, projetos_cfg))
                if k in cache_acordaos and cache_acordaos[k].get("PROC") != proc_num:
                    erros_item.append(f"Processo {proc_num} diverge do cache ({cache_acordaos[k].get('PROC')}) em {k}")

        if erros_item:
            logs_falha.append(
                f"[ABA 3 - ETAPA TCU BLOQUEADA] Card '{item.get('id')}' ({item.get('titulo')}): "
                + "; ".join(erros_item)
            )
            item["etapa_tcu"] = {
                "aplicavel": True,
                "status": "NAO_LOCALIZADO",
                "rotulo_curto": "Não localizado",
                "processos": [],
            }
    return leiloes, logs_falha


def executar_validacao_pre_painel(
    itens_estruturacao: List[Dict],
    itens_leiloes: List[Dict],
) -> Tuple[List[Dict], List[Dict], List[str]]:
    """
    Executa a validação completa antes da geração do HTML.
    Retorna `(itens_estruturacao_aprovados, itens_leiloes_aprovados, lista_erros)`.
    Grava automaticamente o relatório de auditoria em `log_rejeitados_validador.txt`.
    """
    hoje = date.today()
    termos_selos_cfg = _carregar_termos_selos()
    cache = carregar_cache_tcu()
    cache_acordaos = cache.get("acordaos", {})
    cfg_apelidos = carregar_config_apelidos()
    projetos_cfg = cfg_apelidos.get("projetos", {})

    aprovados_est: List[Dict] = []
    erros_totais: List[str] = []

    for card in itens_estruturacao:
        erros_card = validar_card_aba_estruturacao(card, hoje, termos_selos_cfg, cache_acordaos, projetos_cfg)
        if erros_card:
            msg = (
                f"[ABA 2 - CARD REJEITADO] ID='{card.get('id')}' | Título='{card.get('titulo')}' -> "
                + " | ".join(erros_card)
            )
            erros_totais.append(msg)
        else:
            aprovados_est.append(card)

    aprovados_leiloes, erros_leiloes = validar_leiloes_etapa_tcu(itens_leiloes, cache_acordaos, projetos_cfg)
    erros_totais.extend(erros_leiloes)

    # Gravar log auditável da rodada
    cabecalho = [
        f"# Log de Validação Automática Pré-Painel — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"# Cards Aba 2 analisados: {len(itens_estruturacao)} | Aprovados: {len(aprovados_est)} | Rejeitados: {len(itens_estruturacao) - len(aprovados_est)}",
        f"# Cards Aba 3 analisados: {len(itens_leiloes)} | Falhas Etapa TCU: {len(erros_leiloes)}",
        "-" * 90,
    ]
    if erros_totais:
        conteudo_log = "\n".join(cabecalho + erros_totais) + "\n"
    else:
        conteudo_log = "\n".join(cabecalho + ["[OK] Nenhum card rejeitado — 100% dos itens passaram na validação automática."]) + "\n"

    ARQUIVO_LOG_REJEITADOS.write_text(conteudo_log, encoding="utf-8")
    return aprovados_est, aprovados_leiloes, erros_totais

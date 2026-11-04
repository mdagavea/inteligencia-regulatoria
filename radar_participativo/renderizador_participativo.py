import os
from datetime import datetime
from pathlib import Path

TEMPLATE_RADAR_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Radar de Inteligência Regulatória ({data_formatada})</title>
  <style>
    :root {{
      --bg: #f1f5f9;
      --card-bg: #ffffff;
      --text-main: #0f172a;
      --text-secondary: #334155;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --primary: #0f172a;

      --color-infra: #0284c7;
      --bg-infra: #e0f2fe;
      --color-seguros: #7c3aed;
      --bg-seguros: #f3e8ff;
      --color-carbono: #059669;
      --bg-carbono: #d1fae5;
      --color-divida: #d97706;
      --bg-divida: #fef3c7;

      --urgent-color: #dc2626;
      --urgent-bg: #fee2e2;
      --new-color: #1d4ed8;
      --new-bg: #dbeafe;
      --pre-color: #b45309;
      --pre-bg: #fef3c7;
      --open-color: #047857;
      --open-bg: #d1fae5;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      margin: 0;
      padding: 20px 28px;
      line-height: 1.5;
    }}

    .container {{
      max-width: 1420px;
      margin: 0 auto;
    }}

    header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #ffffff;
      padding: 22px 28px;
      border-radius: 14px;
      margin-bottom: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    }}

    .header-title-area h1 {{
      margin: 0;
      font-size: 1.42rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .header-title-area p {{
      margin: 5px 0 0 0;
      color: #cbd5e1;
      font-size: 0.87rem;
    }}

    .header-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .date-badge {{
      font-size: 0.84rem;
      font-weight: 600;
      color: #e2e8f0;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.2);
      padding: 6px 14px;
      border-radius: 20px;
    }}

    .portal-link-btn {{
      font-size: 0.82rem;
      font-weight: 600;
      color: #0f172a;
      background: #38bdf8;
      text-decoration: none;
      padding: 7px 14px;
      border-radius: 20px;
      transition: opacity 0.15s;
    }}

    .portal-link-btn:hover {{
      opacity: 0.9;
    }}

    /* Abas Executivas Principais (4 Pilares do Radar) */
    .tabs-nav {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 18px;
      background: #e2e8f0;
      padding: 6px;
      border-radius: 14px;
    }}

    @media (max-width: 1180px) {{
      .tabs-nav {{ grid-template-columns: repeat(2, 1fr); }}
    }}

    @media (max-width: 720px) {{
      .tabs-nav {{ grid-template-columns: 1fr; }}
    }}

    .tab-btn {{
      background: rgba(255, 255, 255, 0.65);
      border: 1px solid transparent;
      border-radius: 10px;
      padding: 12px 16px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      text-align: left;
      transition: all 0.16s ease;
      color: #334155;
    }}

    .tab-btn:hover {{
      background: #ffffff;
      color: #0f172a;
    }}

    .tab-btn.active {{
      background: #0f172a;
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.18);
    }}

    .tab-btn-left {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}

    .tab-btn-title {{
      font-size: 0.95rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 7px;
    }}

    .tab-btn-sub {{
      font-size: 0.75rem;
      color: #64748b;
      font-weight: 500;
    }}

    .tab-btn.active .tab-btn-sub {{
      color: #cbd5e1;
    }}

    .tab-count-pill {{
      font-size: 0.78rem;
      font-weight: 800;
      padding: 4px 11px;
      border-radius: 20px;
      background: #cbd5e1;
      color: #0f172a;
      white-space: nowrap;
    }}

    .tab-btn.active .tab-count-pill {{
      background: #38bdf8;
      color: #0f172a;
    }}

    .tab-panel {{
      display: none;
    }}

    .tab-panel.active {{
      display: block;
    }}

    /* Banner Contextual Portaria de Riscos e Segurabilidade */
    .context-banner {{
      background: linear-gradient(90deg, #eff6ff 0%, #f5f3ff 100%);
      border: 1px solid #bfdbfe;
      border-left: 5px solid #2563eb;
      border-radius: 12px;
      padding: 13px 18px;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .context-banner-text {{
      font-size: 0.85rem;
      color: #1e293b;
      line-height: 1.45;
    }}

    .context-banner-text strong {{
      color: #1e3a8a;
    }}

    /* KPI Strip */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-bottom: 18px;
    }}

    @media (max-width: 960px) {{
      .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}

    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      cursor: pointer;
      transition: transform 0.12s, box-shadow 0.12s;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 4px 10px rgba(0,0,0,0.06);
    }}

    .kpi-info span {{
      display: block;
      font-size: 0.76rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
    }}

    .kpi-info strong {{
      font-size: 1.65rem;
      font-weight: 800;
      color: var(--text-main);
      line-height: 1.2;
    }}

    .kpi-icon {{
      font-size: 1.55rem;
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    /* Barra de Filtros */
    .filter-bar {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 18px;
      margin-bottom: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }}

    .filter-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }}

    .filter-label {{
      font-size: 0.76rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-right: 4px;
    }}

    .filter-btn {{
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      color: #334155;
      padding: 5px 12px;
      border-radius: 18px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }}

    .filter-btn:hover {{
      background: #e2e8f0;
    }}

    .filter-btn.active {{
      background: #0f172a;
      color: #ffffff;
      border-color: #0f172a;
    }}

    .search-input {{
      padding: 6px 12px;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      font-size: 0.83rem;
      min-width: 240px;
      outline: none;
    }}

    .search-input:focus {{
      border-color: #0284c7;
      box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
    }}

    /* Lista de Cards */
    .dossier-list {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}

    @media (max-width: 1080px) {{
      .dossier-list {{ grid-template-columns: 1fr; }}
    }}

    .dossier-card, .est-card, .leilao-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      transition: box-shadow 0.15s;
      position: relative;
    }}

    .dossier-card:hover, .est-card:hover, .leilao-card:hover {{
      box-shadow: 0 6px 16px rgba(0,0,0,0.07);
    }}

    .dossier-card.vertical-infra {{ border-left: 5px solid var(--color-infra); }}
    .dossier-card.vertical-seguros {{ border-left: 5px solid var(--color-seguros); }}
    .dossier-card.vertical-carbono {{ border-left: 5px solid var(--color-carbono); }}
    .dossier-card.vertical-divida {{ border-left: 5px solid var(--color-divida); }}

    .est-card.cat-PRIORIDADE_A_MPOR {{ border-left: 5px solid #0284c7; }}
    .est-card.cat-PRIORIDADE_B_COMPARACAO {{ border-left: 5px solid #7c3aed; }}
    .est-card.cat-PRIORIDADE_C_ART102 {{ border-left: 5px solid #059669; }}
    .badge-destaque {{ background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }}

    .leilao-card.setor-portos_hidrovias {{ border-left: 5px solid #0284c7; }}
    .leilao-card.setor-aeroportos {{ border-left: 5px solid #6366f1; }}
    .leilao-card.setor-rodovias_ferrovias {{ border-left: 5px solid #d97706; }}
    .leilao-card.setor-nacional_energia_clima {{ border-left: 5px solid #059669; }}

    .card-top-meta {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .badges-left {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }}

    .badge {{
      font-size: 0.72rem;
      font-weight: 700;
      padding: 3px 9px;
      border-radius: 6px;
      letter-spacing: 0.02em;
    }}

    .badge-infra {{ background: var(--bg-infra); color: var(--color-infra); }}
    .badge-seguros {{ background: var(--bg-seguros); color: var(--color-seguros); }}
    .badge-carbono {{ background: var(--bg-carbono); color: var(--color-carbono); }}
    .badge-divida {{ background: var(--bg-divida); color: var(--color-divida); }}
    .badge-risco {{ background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }}

    .badge-orgao {{
      background: #f1f5f9;
      color: #1e293b;
      border: 1px solid #cbd5e1;
    }}

    .badge-modalidade {{
      background: #f8fafc;
      color: #475569;
      border: 1px solid #e2e8f0;
    }}

    .deadline-pill {{
      font-size: 0.75rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      white-space: nowrap;
    }}

    .status-LANCADO_48H {{ background: var(--new-bg); color: var(--new-color); border: 1px solid #93c5fd; }}
    .status-PRAZO_URGENTE {{ background: var(--urgent-bg); color: var(--urgent-color); border: 1px solid #fca5a5; }}
    .status-ABERTO {{ background: var(--open-bg); color: var(--open-color); border: 1px solid #6ee7b7; }}
    .status-PRE_PUBLICACAO {{ background: var(--pre-bg); color: var(--pre-color); border: 1px solid #fcd34d; }}
    .status-ENCERRADO_RECENTE {{ background: #e2e8f0; color: #334155; border: 1px solid #94a3b8; font-weight: 700; }}

    .fase-EDITAL_PUBLICADO {{ background: #dcfce7; color: #166534; border: 1px solid #86efac; }}
    .fase-AVALIACAO_TCU_AJUSTES {{ background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }}
    .fase-ESTRUTURACAO_AUDIENCIA {{ background: #e0f2fe; color: #075985; border: 1px solid #7dd3fc; }}
    .fase-SUSPENSO {{ background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }}
    .fase-REALIZADO_RECENTE {{ background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}

    .dossier-card[data-status="ENCERRADO_RECENTE"] {{
      background: #f1f5f9;
      opacity: 0.56;
      filter: grayscale(75%);
      border: 1px dashed #94a3b8;
      border-left: 5px solid #64748b !important;
      box-shadow: none;
      transition: opacity 0.2s ease, filter 0.2s ease, background 0.2s ease;
    }}

    .dossier-card[data-status="ENCERRADO_RECENTE"]:hover {{
      opacity: 0.92;
      filter: grayscale(15%);
      background: #f8fafc;
    }}

    .dossier-card[data-status="ENCERRADO_RECENTE"] .dossier-section,
    .dossier-card[data-status="ENCERRADO_RECENTE"] .dates-row,
    .dossier-card[data-status="ENCERRADO_RECENTE"] .incidencia-box {{
      background: transparent;
    }}

    .dossier-card[data-status="ENCERRADO_RECENTE"] .process-title {{
      color: #475569;
      text-decoration: line-through;
      text-decoration-color: #94a3b8;
    }}

    .countdown-mono {{
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.01em;
    }}

    .process-title {{
      font-size: 1.03rem;
      font-weight: 700;
      color: #0f172a;
      text-decoration: none;
      line-height: 1.35;
      margin: 0;
    }}

    .process-title:hover {{
      color: #0284c7;
      text-decoration: underline;
    }}

    .dates-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      font-size: 0.78rem;
      color: var(--text-muted);
      background: #f8fafc;
      padding: 6px 10px;
      border-radius: 6px;
      border: 1px solid #f1f5f9;
    }}

    .dates-row strong {{
      color: var(--text-secondary);
    }}

    .val-highlight {{
      color: #0f172a !important;
      background: #e0f2fe;
      padding: 1px 7px;
      border-radius: 4px;
      font-weight: 700;
    }}

    .dossier-box {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 0.86rem;
    }}

    .dossier-section {{
      background: #ffffff;
    }}

    .dossier-label {{
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
      margin-bottom: 2px;
    }}

    .dossier-text {{
      margin: 0;
      color: var(--text-secondary);
      line-height: 1.45;
    }}

    .incidencia-box {{
      background: #f8fafc;
      border-left: 3px solid #475569;
      padding: 8px 12px;
      border-radius: 0 6px 6px 0;
    }}

    .incidencia-box-seguros {{
      background: #faf5ff;
      border-left: 3px solid #7c3aed;
      padding: 8px 12px;
      border-radius: 0 6px 6px 0;
    }}

    .docs-area {{
      margin-top: auto;
      padding-top: 10px;
      border-top: 1px dashed var(--border);
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      align-items: center;
    }}

    .doc-btn {{
      font-size: 0.75rem;
      font-weight: 600;
      text-decoration: none;
      padding: 5px 10px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.12s;
    }}

    .doc-btn-primary {{
      background: #0f172a;
      color: #ffffff;
    }}

    .doc-btn-primary:hover {{
      background: #1e293b;
    }}

    .doc-btn-dou {{
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }}

    .doc-btn-sei {{
      background: #f0fdf4;
      color: #15803d;
      border: 1px solid #bbf7d0;
    }}

    .doc-btn-pdf {{
      background: #fff7ed;
      color: #c2410c;
      border: 1px solid #fed7aa;
    }}

    .doc-btn-matriz {{
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fca5a5;
      font-weight: 700;
    }}

    .doc-btn-secondary {{
      background: #f1f5f9;
      color: #334155;
      border: 1px solid #cbd5e1;
    }}

    .doc-btn:hover {{
      transform: translateY(-1px);
    }}

    .empty-state {{
      grid-column: 1 / -1;
      text-align: center;
      padding: 40px;
      background: var(--card-bg);
      border-radius: 12px;
      border: 1px dashed var(--border);
      color: var(--text-muted);
    }}

    footer {{
      text-align: center;
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 26px;
      padding-bottom: 14px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="header-title-area">
        <h1>🏛️ Radar de Inteligência Regulatória</h1>
        <p>Monitoramento integrado do Ciclo de Outorgas: Participação Social (Brasil Participativo), Estruturação/EVTEAs (Infra S.A., BNDES, PNCP) e Leilões (ANTAQ, ANAC, ANTT, B3)</p>
      </div>
      <div class="header-meta">
        <span class="date-badge">Atualizado em {data_formatada}</span>
        <a class="portal-link-btn" style="background:#f8fafc; color:#0f172a;" href="https://mdagavea.github.io/inteligencia-regulatoria/clipping.html">📰 Clipping Diário</a>
        <a class="portal-link-btn" href="https://brasilparticipativo.presidencia.gov.br/processes" target="_blank">Brasil Participativo ↗</a>
      </div>
    </header>

    <!-- Navegação Principal em 3 Abas Executivas -->
    <nav class="tabs-nav" aria-label="Seções do Radar">
      <button class="tab-btn active" id="btn-tab-participativo" onclick="selecionarAba('participativo')">
        <div class="tab-btn-left">
          <span class="tab-btn-title">🏛️ 1. Consultas & Participação Social</span>
          <span class="tab-btn-sub">Brasil Participativo • Consultas, Audiências e Pré-Publicação</span>
        </div>
        <span class="tab-count-pill">{kpi_total} ativos</span>
      </button>

      <button class="tab-btn" id="btn-tab-estruturacao" onclick="selecionarAba('estruturacao')">
        <div class="tab-btn-left">
          <span class="tab-btn-title">📐 2. Estruturação, EVTEAs & Contratações</span>
          <span class="tab-btn-sub">DNIT, BNDES, Infra S.A. & PNCP (Escopo, Riscos & Seguros na Fonte)</span>
        </div>
        <span class="tab-count-pill">{est_total} verificados</span>
      </button>

      <button class="tab-btn" id="btn-tab-leiloes" onclick="selecionarAba('leiloes')">
        <div class="tab-btn-left">
          <span class="tab-btn-title">🔔 3. Radar de Leilões & Outorgas</span>
          <span class="tab-btn-sub">Portos/Hidrovias (ANTAQ), Aeroportos (ANAC), Rodovias (ANTT) & B3</span>
        </div>
        <span class="tab-count-pill">{leil_total} na carteira</span>
      </button>

      <button class="tab-btn" id="btn-tab-sfn" onclick="selecionarAba('sfn')">
        <div class="tab-btn-left">
          <span class="tab-btn-title">🛡️ 4. SFN, Seguros & Capitais</span>
          <span class="tab-btn-sub">SUSEP, CVM, BCB, PREVIC, SRE/MF & ANBIMA (Fora do Brasil Participativo)</span>
        </div>
        <span class="tab-count-pill">{sfn_total_aprovados} no filtro</span>
      </button>
    </nav>

    <!-- =================================================================== -->
    <!-- ABA 1: PROCESSOS PARTICIPATIVOS & NORMATIVOS (BRASIL PARTICIPATIVO) -->
    <!-- =================================================================== -->
    <section class="tab-panel active" id="panel-participativo">
      <div class="kpi-grid">
        <div class="kpi-card" onclick="filtrarStatus('TODOS')">
          <div class="kpi-info">
            <span>Total no Radar</span>
            <strong>{kpi_total}</strong>
          </div>
          <div class="kpi-icon" style="background: #f1f5f9; color: #0f172a;">📋</div>
        </div>
        <div class="kpi-card" onclick="filtrarStatus('LANCADO_48H')">
          <div class="kpi-info">
            <span>Lançados (Últimas 48h)</span>
            <strong style="color: var(--new-color);">{kpi_lancados_48h}</strong>
          </div>
          <div class="kpi-icon" style="background: var(--new-bg); color: var(--new-color);">🆕</div>
        </div>
        <div class="kpi-card" onclick="filtrarStatus('PRAZO_URGENTE')">
          <div class="kpi-info">
            <span>Prazo Crítico (≤ 7 dias)</span>
            <strong style="color: var(--urgent-color);">{kpi_urgentes}</strong>
          </div>
          <div class="kpi-icon" style="background: var(--urgent-bg); color: var(--urgent-color);">🚨</div>
        </div>
        <div class="kpi-card" onclick="filtrarStatus('PRE_PUBLICACAO')">
          <div class="kpi-info">
            <span>Radar Pré-Publicação</span>
            <strong style="color: var(--pre-color);">{kpi_pre}</strong>
          </div>
          <div class="kpi-icon" style="background: var(--pre-bg); color: var(--pre-color);">📡</div>
        </div>
      </div>

      <div class="filter-bar">
        <div class="filter-group" id="status-filters">
          <span class="filter-label">Status:</span>
          <button class="filter-btn active" data-status="TODOS" onclick="filtrarStatus('TODOS')">Todos (<span id="cnt-todos">{kpi_total}</span>)</button>
          <button class="filter-btn" data-status="LANCADO_48H" onclick="filtrarStatus('LANCADO_48H')">🆕 Lançados 48h (<span id="cnt-48h">{kpi_lancados_48h}</span>)</button>
          <button class="filter-btn" data-status="PRAZO_URGENTE" onclick="filtrarStatus('PRAZO_URGENTE')">🚨 Prazo ≤ 7d (<span id="cnt-urg">{kpi_urgentes}</span>)</button>
          <button class="filter-btn" data-status="ABERTO" onclick="filtrarStatus('ABERTO')">🟢 Prazo Regular (<span id="cnt-abe">{kpi_abertos_regulares}</span>)</button>
          <button class="filter-btn" data-status="PRE_PUBLICACAO" onclick="filtrarStatus('PRE_PUBLICACAO')">📡 Pré-Publicação (<span id="cnt-pre">{kpi_pre}</span>)</button>
          <button class="filter-btn" data-status="ENCERRADO_RECENTE" onclick="filtrarStatus('ENCERRADO_RECENTE')">⏹️ Prazo Vencido 72h (<span id="cnt-enc">{kpi_encerrados}</span>)</button>
        </div>

        <div class="filter-group" id="vertical-filters">
          <span class="filter-label">Vertical:</span>
          <button class="filter-btn active" data-vertical="TODAS" onclick="filtrarVertical('TODAS')">Todas</button>
          <button class="filter-btn" data-vertical="infra" onclick="filtrarVertical('infra')">Infraestrutura & Outorgas</button>
          <button class="filter-btn" data-vertical="seguros" onclick="filtrarVertical('seguros')">Seguros & Garantias</button>
          <button class="filter-btn" data-vertical="carbono" onclick="filtrarVertical('carbono')">Clima & Sustentabilidade</button>
          <button class="filter-btn" data-vertical="divida" onclick="filtrarVertical('divida')">Finanças & Crédito</button>
        </div>

        <input type="text" id="search-box" class="search-input" placeholder="🔍 Filtrar por órgão, sigla, tema..." oninput="aplicarFiltros()">
      </div>

      <div class="dossier-list" id="dossier-container">
        {cards_html}
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- ABA 2: ESTRUTURAÇÃO, EVTEAS & CONTRATAÇÕES ESTRATÉGICAS             -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-estruturacao">
      <div class="context-banner">
        <div class="context-banner-text">
          <strong>📋 Escopo Documental Verificado na Fonte:</strong> Monitoramento factual de contratações de <strong>EVTEA, estudos de viabilidade e modelagem de concessão/PPP/arrendamento</strong> com acesso direto aos PDFs oficiais (Termo de Referência, Especificações Técnicas, Matriz de Riscos e Contratos) — organizado em <strong>Prioridade A (Portos, Aeroportos e Hidrovias)</strong> e <strong>Prioridade B (Comparação Federal: Rodovias e Ferrovias estruturadas por Infra S.A. e BNDES)</strong>.
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card" onclick="filtrarCategoriaEst('TODAS')">
          <div class="kpi-info">
            <span>Total Verificado</span>
            <strong>{est_total}</strong>
          </div>
          <div class="kpi-icon" style="background: #f1f5f9; color: #0f172a;">📐</div>
        </div>
        <div class="kpi-card" onclick="filtrarCategoriaEst('PRIORIDADE_A_MPOR')">
          <div class="kpi-info">
            <span>Prioridade A (Portos & Hidrovias)</span>
            <strong style="color: #0284c7;">{est_kpi_evtea}</strong>
          </div>
          <div class="kpi-icon" style="background: #e0f2fe; color: #0284c7;">⚓</div>
        </div>
        <div class="kpi-card" onclick="filtrarCategoriaEst('PRIORIDADE_B_COMPARACAO')">
          <div class="kpi-info">
            <span>Prioridade B (Comparação Federal)</span>
            <strong style="color: #7c3aed;">{est_kpi_seguros}</strong>
          </div>
          <div class="kpi-icon" style="background: #f3e8ff; color: #7c3aed;">🛣️</div>
        </div>
        <div class="kpi-card" onclick="filtrarCategoriaEst('PROPOSTAS_ABERTAS')">
          <div class="kpi-info">
            <span>Editais com Propostas Abertas</span>
            <strong style="color: #059669;">{est_kpi_carteira}</strong>
          </div>
          <div class="kpi-icon" style="background: #d1fae5; color: #059669;">⏳</div>
        </div>
      </div>

      <div class="filter-bar">
        <div class="filter-group" id="est-cat-filters">
          <span class="filter-label">Recorte:</span>
          <button class="filter-btn active" data-est-cat="TODAS" onclick="filtrarCategoriaEst('TODAS')">Todos ({est_total})</button>
          <button class="filter-btn" data-est-cat="PRIORIDADE_A_MPOR" onclick="filtrarCategoriaEst('PRIORIDADE_A_MPOR')">⚓ Prioridade A — Portos, Aeroportos & Hidrovias ({est_kpi_evtea})</button>
          <button class="filter-btn" data-est-cat="PRIORIDADE_B_COMPARACAO" onclick="filtrarCategoriaEst('PRIORIDADE_B_COMPARACAO')">⚖️ Prioridade B — Comparação Federal ({est_kpi_seguros})</button>
          <button class="filter-btn" data-est-cat="PROPOSTAS_ABERTAS" onclick="filtrarCategoriaEst('PROPOSTAS_ABERTAS')">⏳ Editais com Propostas Abertas ({est_kpi_carteira})</button>
        </div>

        <input type="text" id="search-box-est" class="search-input" placeholder="🔍 Filtrar por Araruama, Tapajós, Santos, RN, RLE 016/2026..." oninput="aplicarFiltrosEst()">
      </div>

      <div class="dossier-list" id="est-container">
        {cards_estruturacao_html}
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- ABA 3: RADAR DE LEILÕES & OUTORGAS (MPOR, ANTAQ, ANAC, ANTT & B3)   -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-leiloes">
      <div class="kpi-grid">
        <div class="kpi-card" onclick="filtrarSetorLeilao('TODOS'); filtrarFaseLeilao('TODAS');">
          <div class="kpi-info">
            <span>Projetos na Carteira</span>
            <strong>{leil_total}</strong>
          </div>
          <div class="kpi-icon" style="background: #f1f5f9; color: #0f172a;">🔔</div>
        </div>
        <div class="kpi-card" onclick="filtrarFaseLeilao('EDITAL_PUBLICADO')">
          <div class="kpi-info">
            <span>Edital Publicado / B3</span>
            <strong style="color: #047857;">{leil_kpi_edital}</strong>
          </div>
          <div class="kpi-icon" style="background: #d1fae5; color: #047857;">📢</div>
        </div>
        <div class="kpi-card" onclick="filtrarFaseLeilao('AVALIACAO_TCU_AJUSTES')">
          <div class="kpi-info">
            <span>No TCU / Ajustes Pré-Edital</span>
            <strong style="color: #b45309;">{leil_kpi_tcu}</strong>
          </div>
          <div class="kpi-icon" style="background: #fef3c7; color: #b45309;">⚖️</div>
        </div>
        <div class="kpi-card" onclick="filtrarSetorLeilao('MPOR_FOCO')">
          <div class="kpi-info">
            <span>Carteira MPor (Portos/Hidro/Aero)</span>
            <strong style="color: #0284c7;">{leil_kpi_mpor}</strong>
          </div>
          <div class="kpi-icon" style="background: #e0f2fe; color: #0284c7;">⚓</div>
        </div>
      </div>

      <div class="filter-bar">
        <div class="filter-group" id="leilao-setor-filters">
          <span class="filter-label">Setor:</span>
          <button class="filter-btn active" data-setor="TODOS" onclick="filtrarSetorLeilao('TODOS')">Todos ({leil_total})</button>
          <button class="filter-btn" data-setor="MPOR_FOCO" onclick="filtrarSetorLeilao('MPOR_FOCO')">🏛️ Universo MPor ({leil_kpi_mpor})</button>
          <button class="filter-btn" data-setor="portos_hidrovias" onclick="filtrarSetorLeilao('portos_hidrovias')">⚓ Portos & Hidrovias</button>
          <button class="filter-btn" data-setor="aeroportos" onclick="filtrarSetorLeilao('aeroportos')">✈️ Aeroportos</button>
          <button class="filter-btn" data-setor="rodovias_ferrovias" onclick="filtrarSetorLeilao('rodovias_ferrovias')">🛣️ Rodovias & Ferrovias</button>
          <button class="filter-btn" data-setor="nacional_energia_clima" onclick="filtrarSetorLeilao('nacional_energia_clima')">⚡ Relevância Nacional (Energia/Clima)</button>
        </div>

        <div class="filter-group" id="leilao-fase-filters">
          <span class="filter-label">Fase:</span>
          <button class="filter-btn active" data-fase="TODAS" onclick="filtrarFaseLeilao('TODAS')">Todas</button>
          <button class="filter-btn" data-fase="EDITAL_PUBLICADO" onclick="filtrarFaseLeilao('EDITAL_PUBLICADO')">📢 Edital Publicado</button>
          <button class="filter-btn" data-fase="AVALIACAO_TCU_AJUSTES" onclick="filtrarFaseLeilao('AVALIACAO_TCU_AJUSTES')">⚖️ No TCU / Ajustes</button>
          <button class="filter-btn" data-fase="ESTRUTURACAO_AUDIENCIA" onclick="filtrarFaseLeilao('ESTRUTURACAO_AUDIENCIA')">📐 Em Estruturação</button>
        </div>

        <input type="text" id="search-box-leilao" class="search-input" placeholder="🔍 Filtrar por MUC04, Itajaí, Tecon, Galeão..." oninput="aplicarFiltrosLeilao()">
      </div>

      <div class="dossier-list" id="leilao-container">
        {cards_leiloes_html}
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- ABA 4: SFN, SEGUROS & CAPITAIS (SUSEP, CVM, BCB, PREVIC, ANBIMA)    -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-sfn">
      <div class="context-banner">
        <div class="context-banner-text">
          <strong>🛡️ Regulação do Sistema Financeiro, Seguros & Mercado de Capitais (Fora do Brasil Participativo):</strong> Monitoramento 100% factual (sem IA obrigatória) das consultas e audiências públicas em portais próprios de <strong>SUSEP/CNSP, CVM, BCB, PREVIC, SRE/MF e ANBIMA (autorregulação)</strong>. Exibe na vitrine principal apenas os processos aderentes ao filtro temático do Radar e mantém transparência total na gaveta inferior sobre os processos ativos de outros temas.
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-info">
            <span>No Filtro Temático</span>
            <strong style="color: #0284c7;">{sfn_total_aprovados}</strong>
          </div>
          <div class="kpi-icon" style="background: #e0f2fe; color: #0284c7;">🛡️</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-info">
            <span>Prazo Aberto / Ativos</span>
            <strong style="color: #059669;">{sfn_kpi_abertos}</strong>
          </div>
          <div class="kpi-icon" style="background: #d1fae5; color: #059669;">🟢</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-info">
            <span>Prazo Crítico (≤ 7 dias)</span>
            <strong style="color: var(--urgent-color);">{sfn_kpi_urgentes}</strong>
          </div>
          <div class="kpi-icon" style="background: var(--urgent-bg); color: var(--urgent-color);">🚨</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-info">
            <span>Retidos Fora do Filtro</span>
            <strong style="color: #64748b;">{sfn_total_fora}</strong>
          </div>
          <div class="kpi-icon" style="background: #f1f5f9; color: #475569;">🔎</div>
        </div>
      </div>

      {painel_fontes_sfn_html}

      <div class="dossier-list" id="sfn-container">
        {cards_sfn_html}
      </div>

      {gaveta_fora_filtro_sfn_html}
    </section>

    <footer>
      Radar de Inteligência Regulatória • Integração Brasil Participativo (GraphQL), ANTT (ParticipANTT), ANTAQ, SUSEP (SAFE/SCP), CVM, Infra S.A., PNCP, BNDES & Curadoria Gemini
    </footer>
  </div>

  <script>
    let statusAtual = 'TODOS';
    let verticalAtual = 'TODAS';
    let catEstAtual = 'TODAS';
    let setorLeilaoAtual = 'TODOS';
    let faseLeilaoAtual = 'TODAS';

    function selecionarAba(aba) {{
      ['participativo', 'estruturacao', 'leiloes', 'sfn'].forEach(nome => {{
        const btn = document.getElementById('btn-tab-' + nome);
        const panel = document.getElementById('panel-' + nome);
        if (btn) btn.classList.toggle('active', nome === aba);
        if (panel) panel.classList.toggle('active', nome === aba);
      }});
      if (history.replaceState) {{
        history.replaceState(null, null, '#' + aba);
      }}
    }}

    // Suporte a deep-link por hash (#estruturacao, #leiloes ou #sfn)
    window.addEventListener('DOMContentLoaded', () => {{
      const h = (window.location.hash || '').replace('#', '').trim();
      if (['participativo', 'estruturacao', 'leiloes', 'sfn'].includes(h)) {{
        selecionarAba(h);
      }}
    }});

    // Filtros Aba 1
    function filtrarStatus(st) {{
      statusAtual = st;
      document.querySelectorAll('#status-filters .filter-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-status') === st);
      }});
      aplicarFiltros();
    }}

    function filtrarVertical(vert) {{
      verticalAtual = vert;
      document.querySelectorAll('#vertical-filters .filter-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-vertical') === vert);
      }});
      aplicarFiltros();
    }}

    function aplicarFiltros() {{
      const termo = (document.getElementById('search-box').value || '').toLowerCase().trim();
      const cards = document.querySelectorAll('.dossier-card');
      cards.forEach(card => {{
        if (card.getAttribute('data-expired-purge') === '1') {{
          card.style.display = 'none';
          return;
        }}
        const st = card.getAttribute('data-status');
        const vt = card.getAttribute('data-vertical');
        const texto = card.innerText.toLowerCase();

        const matchStatus = (statusAtual === 'TODOS') || (st === statusAtual);
        const matchVertical = (verticalAtual === 'TODAS') || (vt === verticalAtual);
        const matchTexto = (!termo) || texto.includes(termo);

        card.style.display = (matchStatus && matchVertical && matchTexto) ? 'flex' : 'none';
      }});
    }}

    // Filtros Aba 2 (Estruturação & Contratações)
    function filtrarCategoriaEst(cat) {{
      catEstAtual = cat;
      document.querySelectorAll('#est-cat-filters .filter-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-est-cat') === cat);
      }});
      aplicarFiltrosEst();
    }}

    function aplicarFiltrosEst() {{
      const termo = (document.getElementById('search-box-est').value || '').toLowerCase().trim();
      const cards = document.querySelectorAll('.est-card');
      cards.forEach(card => {{
        const c = card.getAttribute('data-est-cat');
        const aberta = card.getAttribute('data-proposta-aberta') === '1';
        const texto = card.innerText.toLowerCase();
        let matchCat = false;
        if (catEstAtual === 'TODAS') {{
          matchCat = true;
        }} else if (catEstAtual === 'PROPOSTAS_ABERTAS') {{
          matchCat = aberta;
        }} else {{
          matchCat = (c === catEstAtual);
        }}
        const matchTexto = (!termo) || texto.includes(termo);
        card.style.display = (matchCat && matchTexto) ? 'flex' : 'none';
      }});
    }}

    // Filtros Aba 3 (Leilões)
    function filtrarSetorLeilao(setor) {{
      setorLeilaoAtual = setor;
      document.querySelectorAll('#leilao-setor-filters .filter-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-setor') === setor);
      }});
      aplicarFiltrosLeilao();
    }}

    function filtrarFaseLeilao(fase) {{
      faseLeilaoAtual = fase;
      document.querySelectorAll('#leilao-fase-filters .filter-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.getAttribute('data-fase') === fase);
      }});
      aplicarFiltrosLeilao();
    }}

    function aplicarFiltrosLeilao() {{
      const termo = (document.getElementById('search-box-leilao').value || '').toLowerCase().trim();
      const cards = document.querySelectorAll('.leilao-card');
      cards.forEach(card => {{
        const s = card.getAttribute('data-setor');
        const f = card.getAttribute('data-fase');
        const texto = card.innerText.toLowerCase();

        let matchSetor = false;
        if (setorLeilaoAtual === 'TODOS') {{
          matchSetor = true;
        }} else if (setorLeilaoAtual === 'MPOR_FOCO') {{
          matchSetor = ['portos_hidrovias', 'aeroportos'].includes(s);
        }} else {{
          matchSetor = (s === setorLeilaoAtual);
        }}

        const matchFase = (faseLeilaoAtual === 'TODAS') || (f === faseLeilaoAtual);
        const matchTexto = (!termo) || texto.includes(termo);

        card.style.display = (matchSetor && matchFase && matchTexto) ? 'flex' : 'none';
      }});
    }}

    function pad2(n) {{
      return String(n).padStart(2, '0');
    }}

    function atualizarContadoresTempoReal() {{
      const agora = new Date();
      const cards = document.querySelectorAll('.dossier-card');
      let mudancaStatus = false;

      cards.forEach(card => {{
        const st = card.getAttribute('data-status');
        if (st === 'PRE_PUBLICACAO') return;

        const isoDate = card.getAttribute('data-deadline-iso');
        const fimBr = card.getAttribute('data-fim-br') || '';
        const pill = card.querySelector('.deadline-pill');
        if (!isoDate || !pill) return;

        const limite = new Date(isoDate + 'T23:59:59-03:00');
        const diffMs = limite - agora;

        if (diffMs > 0) {{
          const totalMin = Math.floor(diffMs / 60000);
          const dias = Math.floor(totalMin / 1440);
          const horas = Math.floor((totalMin % 1440) / 60);
          const mins = totalMin % 60;

          const relogio = `${{dias}}d ${{pad2(horas)}}h ${{pad2(mins)}}m`;
          if (st === 'LANCADO_48H') {{
            pill.innerHTML = `🆕 Lançado • <span class="countdown-mono">⏳ ${{relogio}}</span> (até ${{fimBr}})`;
          }} else if (dias <= 7) {{
            if (st !== 'PRAZO_URGENTE') {{
              card.setAttribute('data-status', 'PRAZO_URGENTE');
              pill.className = 'deadline-pill status-PRAZO_URGENTE';
              mudancaStatus = true;
            }}
            pill.innerHTML = `🚨 Urgente • <span class="countdown-mono">⏳ ${{relogio}}</span> (até ${{fimBr}})`;
          }} else {{
            pill.innerHTML = `🟢 Aberto • <span class="countdown-mono">⏳ ${{relogio}}</span> (até ${{fimBr}})`;
          }}
        }} else {{
          const horasVencido = Math.floor(Math.abs(diffMs) / 3600000);
          const diasVencido = Math.floor(horasVencido / 24);
          if (horasVencido <= 72) {{
            if (st !== 'ENCERRADO_RECENTE') {{
              card.setAttribute('data-status', 'ENCERRADO_RECENTE');
              pill.className = 'deadline-pill status-ENCERRADO_RECENTE';
              mudancaStatus = true;
            }}
            const txtTempo = diasVencido >= 1 ? `há ${{diasVencido}}d` : `há ${{horasVencido}}h`;
            pill.innerHTML = `⏹️ Prazo Vencido ${{txtTempo}} (em ${{fimBr}})`;
          }} else {{
            if (card.getAttribute('data-expired-purge') !== '1') {{
              card.setAttribute('data-expired-purge', '1');
              mudancaStatus = true;
            }}
          }}
        }}
      }});

      // Atualiza também os contadores regressivos da Aba 2 (Estruturação / Licitações)
      document.querySelectorAll('.est-card').forEach(card => {{
        const isoDate = card.getAttribute('data-deadline-iso');
        const fimBr = card.getAttribute('data-fim-br') || '';
        const pill = card.querySelector('.est-deadline-pill');
        if (!isoDate || !pill) return;
        const limite = new Date(isoDate + 'T18:00:00-03:00');
        const diffMs = limite - agora;
        if (diffMs > 0) {{
          const totalMin = Math.floor(diffMs / 60000);
          const dias = Math.floor(totalMin / 1440);
          const horas = Math.floor((totalMin % 1440) / 60);
          pill.innerHTML = `⏳ Propostas: <span class="countdown-mono">${{dias}}d ${{pad2(horas)}}h</span> (até ${{fimBr}})`;
        }}
      }});

      if (mudancaStatus) {{
        aplicarFiltros();
      }}
    }}

    atualizarContadoresTempoReal();
    setInterval(atualizarContadoresTempoReal, 30000);
  </script>
</body>
</html>
"""

NOMES_VERTICAIS = {
    "infra": "Infraestrutura & Outorgas",
    "seguros": "Seguros & Garantias",
    "carbono": "Clima & Sustentabilidade",
    "divida": "Finanças & Crédito"
}

NOMES_CATEGORIAS_EST = {
    "PRIORIDADE_A_MPOR": ("⚓ Prioridade A — Portos, Aeroportos & Hidrovias", "badge-infra"),
    "PRIORIDADE_B_COMPARACAO": ("⚖️ Prioridade B — EVTEA & Modelagem Federal (Comparação)", "badge-seguros"),
    "PRIORIDADE_C_ART102": ("🛡️ Prioridade C — Obra Setor MPor • Art. 102 Lei 14.133", "badge-carbono"),
}

NOMES_FASES_LEILAO = {
    "EDITAL_PUBLICADO": "📢 Edital Publicado / Em Andamento",
    "AVALIACAO_TCU_AJUSTES": "⚖️ No TCU / Ajustes Pré-Edital",
    "ESTRUTURACAO_AUDIENCIA": "📐 Em Estruturação / Pós-Audiência",
    "SUSPENSO": "⏸️ Certame Suspenso",
    "REALIZADO_RECENTE": "✅ Realizado Recentemente",
}


def _inicio_anterior_a_publicacao(inicio_br: str, pub_br: str) -> bool:
    try:
        d_ini = datetime.strptime(inicio_br, "%d/%m/%Y").date()
        d_pub = datetime.strptime(pub_br, "%d/%m/%Y").date()
        return d_ini < d_pub
    except Exception:
        return False


def formatar_badge_prazo(item: dict) -> str:
    st = item["status_ciclo"]
    dias = item.get("dias_restantes")
    fim_br = item.get("data_fim_br", "—")

    if st == "PRE_PUBLICACAO":
        return "📡 Pré-Publicação (Rascunho na API)"
    if st == "LANCADO_48H":
        if dias is not None and dias >= 0:
            return f"🆕 Lançado Agora • {dias}d restantes (até {fim_br})"
        return "🆕 Lançado nas últimas 48h"
    if st == "PRAZO_URGENTE":
        if dias == 0:
            return f"🚨 Encerra HOJE ({fim_br})"
        if dias == 1:
            return f"🚨 Encerra AMANHÃ ({fim_br})"
        return f"🚨 Vence em {dias} dias ({fim_br})"
    if st == "ABERTO":
        if dias is not None:
            return f"🟢 Aberto • {dias} dias restantes (até {fim_br})"
        return "🟢 Aberto para contribuições"
    return f"⏹️ Encerrado em {fim_br}"


def renderizar_botoes_documentos(item: dict) -> str:
    botoes = [
        f'<a class="doc-btn doc-btn-primary" href="{item["url"]}" target="_blank" rel="noopener noreferrer">🌐 Abrir Processo no Portal ↗</a>'
    ]

    for doc in item.get("documentos", [])[:6]:
        cat = doc.get("categoria", "DOCUMENTO")
        url = doc.get("url", "#")
        rotulo = doc.get("rotulo", "Documento")

        if cat == "DOU":
            classe = "doc-btn-dou"
        elif cat == "SEI":
            classe = "doc-btn-sei"
            if "processo" not in rotulo.lower() and "sei" not in rotulo.lower():
                rotulo = f"🗂️ SEI: {rotulo}"
        elif cat == "MATRIZ_RISCO":
            classe = "doc-btn-matriz"
        elif cat in ("ANEXO_PDF", "MINUTA", "NOTA_TECNICA", "SUBSIDIO", "TERMO_REFERENCIA", "ETP", "ORCAMENTO_LOTE"):
            classe = "doc-btn-pdf"
        else:
            classe = "doc-btn-secondary"

        botoes.append(f'<a class="doc-btn {classe}" href="{url}" target="_blank" rel="noopener noreferrer">{rotulo}</a>')

    return "\n          ".join(botoes)


def _renderizar_cards_estruturacao(itens_estruturacao: list) -> str:
    if not itens_estruturacao:
        return '<div class="empty-state">Nenhuma licitação ou estruturação encontrada no momento.</div>'

    blocos = []
    for it in itens_estruturacao:
        cat = it.get("categoria_item", "PRIORIDADE_A_MPOR")
        rotulo_cat, classe_badge = NOMES_CATEGORIAS_EST.get(cat, ("📐 Estruturação & EVTEA", "badge-infra"))
        prio = it.get("prioridade_escopo", "")
        fim_iso = it.get("data_fim_iso", "")
        fim_br = it.get("data_fim_br", "Fluxo Contínuo")
        dias = it.get("dias_restantes")

        proposta_aberta = "1" if (dias is not None and dias >= 0) else "0"
        if dias is not None and dias >= 0:
            classe_prazo = "status-PRAZO_URGENTE" if dias <= 7 else "status-ABERTO"
            texto_prazo = f"⏳ Propostas: {dias}d restantes (até {fim_br})"
        else:
            classe_prazo = "status-LANCADO_48H"
            texto_prazo = f"📅 {fim_br}"

        badge_destaque = '<span class="badge badge-destaque">⭐ Destaque Prioritário</span>' if prio == "PRIORIDADE_A_DESTAQUE" else ""

        botoes = []
        for idx, doc in enumerate(it.get("documentos", [])[:9]):
            c_doc = doc.get("categoria", "DOCUMENTO")
            u_doc = doc.get("url", "#")
            r_doc = doc.get("rotulo", "Documento")
            if idx == 0 and c_doc in ("EDITAL", "SEI"):
                cls = "doc-btn-primary"
            elif c_doc == "MATRIZ_RISCO":
                cls = "doc-btn-matriz"
            elif c_doc == "SEI":
                cls = "doc-btn-sei"
            elif c_doc == "DOU":
                cls = "doc-btn-dou"
            elif c_doc in ("TERMO_REFERENCIA", "ETP", "ORCAMENTO_LOTE", "MINUTA_CONTRATO"):
                cls = "doc-btn-pdf"
            else:
                cls = "doc-btn-secondary"
            botoes.append(f'<a class="doc-btn {cls}" href="{u_doc}" target="_blank" rel="noopener noreferrer">{r_doc}</a>')

        botoes_html = "\n          ".join(botoes)
        titulo_exib = it.get("titulo_executivo") or it.get("titulo", "")
        texto_riscos_html = (it.get("analise_riscos_segurabilidade") or "").replace("\n", "<br>")

        blocos.append(f"""
      <article class="est-card cat-{cat}" data-est-cat="{cat}" data-proposta-aberta="{proposta_aberta}" data-deadline-iso="{fim_iso}" data-fim-br="{fim_br}">
        <div class="card-top-meta">
          <div class="badges-left">
            <span class="badge {classe_badge}">{rotulo_cat}</span>
            <span class="badge badge-orgao">🏛️ {it.get('estruturador_sigla', 'Estruturador')}</span>
            {badge_destaque}
          </div>
          <span class="deadline-pill est-deadline-pill {classe_prazo}">{texto_prazo}</span>
        </div>

        <a class="process-title" href="{it['url']}" target="_blank" rel="noopener noreferrer">{titulo_exib}</a>

        <div class="dates-row">
          <span><strong>Valor Estimado / Contratado:</strong> <span class="val-highlight">{it.get('valor_formatado', 'N/I')}</span></span>
          <span><strong>Instrumento:</strong> {it.get('modalidade', 'Licitação')}</span>
          <span><strong>Data / Marco:</strong> {it.get('data_publicacao_br', 'Recente')}</span>
        </div>

        <div class="docs-area">
          {botoes_html}
        </div>
      </article>""")

    return "\n".join(blocos)


def _renderizar_cards_leiloes(itens_leiloes: list) -> str:
    if not itens_leiloes:
        return '<div class="empty-state">Nenhum leilão cadastrado no radar.</div>'

    blocos = []
    for l in itens_leiloes:
        setor = l.get("setor", "portos_hidrovias")
        fase = l.get("fase_leilao", "EDITAL_PUBLICADO")
        rotulo_fase = NOMES_FASES_LEILAO.get(fase, fase)

        if setor in ("portos_hidrovias", "aeroportos"):
            cls_setor = "badge-infra"
        elif setor == "rodovias_ferrovias":
            cls_setor = "badge-divida"
        else:
            cls_setor = "badge-carbono"

        botoes = []
        for idx, doc in enumerate(l.get("documentos", [])[:5]):
            cls = "doc-btn-primary" if idx == 0 else "doc-btn-secondary"
            botoes.append(f'<a class="doc-btn {cls}" href="{doc["url"]}" target="_blank" rel="noopener noreferrer">{doc["rotulo"]}</a>')
        botoes_html = "\n          ".join(botoes)

        blocos.append(f"""
      <article class="leilao-card setor-{setor}" data-setor="{setor}" data-fase="{fase}">
        <div class="card-top-meta">
          <div class="badges-left">
            <span class="badge {cls_setor}">{l.get('setor_nome', 'Infraestrutura')}</span>
            <span class="badge badge-orgao">🏛️ {l.get('orgao_sigla', 'Governo Federal')}</span>
            <span class="badge badge-modalidade">🔖 {l.get('codigo_ativo', 'OUTORGA')}</span>
          </div>
          <span class="deadline-pill fase-{fase}">{rotulo_fase}</span>
        </div>

        <a class="process-title" href="{l['url']}" target="_blank" rel="noopener noreferrer">{l['titulo']}</a>

        <div class="dates-row">
          <span><strong>CAPEX / Investimento:</strong> <span class="val-highlight">{l.get('capex_estimado', 'Sob consulta')}</span></span>
          <span><strong>Prazo Concessão:</strong> {l.get('prazo_concessao', '—')}</span>
          <span><strong>Cronograma:</strong> {l.get('data_evento_br', '—')} ({l.get('local_certame', 'B3')})</span>
        </div>

        <div class="docs-area">
          {botoes_html}
        </div>
      </article>""")

    return "\n".join(blocos)


def _renderizar_aba_sfn(dados_sfn: dict) -> tuple:
    """Renderiza a barra de origens monitoradas, os cards aprovados pelo filtro e a gaveta transparente dos retidos fora do filtro."""
    aprovados = (dados_sfn or {}).get("aprovados") or []
    fora_filtro = (dados_sfn or {}).get("fora_do_filtro") or []
    fontes = (dados_sfn or {}).get("fontes_monitoradas") or []

    pilulas_fontes = []
    for f in fontes:
        cor = "#047857" if f.get("status") == "ATIVO_AUTOMATICO" else "#334155"
        bg = "#ecfdf5" if f.get("status") == "ATIVO_AUTOMATICO" else "#f8fafc"
        icone = "✅" if f.get("status") == "ATIVO_AUTOMATICO" else "🔗"
        pilulas_fontes.append(
            f'<a href="{f.get("url", "#")}" target="_blank" rel="noopener noreferrer" '
            f'style="text-decoration:none;background:{bg};border:1px solid #cbd5e1;color:{cor};padding:6px 12px;border-radius:18px;font-size:0.76rem;font-weight:600;">'
            f'{icone} <strong>{f.get("sigla", "")}:</strong> {f.get("rotulo", "")} ↗</a>'
        )
    painel_fontes_html = f"""
      <div class="filter-bar" style="margin-bottom:16px;padding:12px 16px;">
        <div class="filter-group" style="flex-wrap:wrap;gap:8px;">
          <span class="filter-label">Origens SFN & Seguros:</span>
          {''.join(pilulas_fontes)}
        </div>
      </div>"""

    blocos_aprovados = []
    if not aprovados:
        blocos_aprovados.append('<div class="empty-state">Nenhuma consulta pública ativa no SFN casou com o filtro temático hoje.</div>')
    else:
        for it in aprovados:
            vert = it.get("vertical", "seguros")
            nome_vert = NOMES_VERTICAIS.get(vert, "Seguros & Garantias")
            st = it.get("status_ciclo", "ABERTO")
            badge_prazo = formatar_badge_prazo(it)
            botoes_docs = renderizar_botoes_documentos({
                "url": it.get("url_principal", "#"),
                "documentos": it.get("documentos", []),
            })
            obs_html = f'<div class="dossier-section"><div class="dossier-label">📎 Observações Oficiais / Contato da Área</div><p class="dossier-text">{it.get("observacoes") or ""} {("• E-mail: " + it["email_area"]) if it.get("email_area") else ""}</p></div>' if (it.get("observacoes") or it.get("email_area")) else ""
            resumo_ia_html = f'<div class="dossier-section"><div class="dossier-label">🤖 Resumo Factual Sintético</div><p class="dossier-text">{it["resumo_ia"]}</p></div>' if it.get("resumo_ia") else ""

            blocos_aprovados.append(f"""
      <article class="dossier-card vertical-{vert}" data-deadline-iso="{it.get('data_fim_iso', '')}" data-fim-br="{it.get('data_fim_br', '—')}">
        <div class="card-top-meta">
          <div class="badges-left">
            <span class="badge badge-{vert}">{nome_vert}</span>
            <span class="badge badge-orgao">🏛️ {it.get('entidade', 'SFN')}</span>
            <span class="badge badge-modalidade">🎯 Filtro: {it.get('termo_casado', '')}</span>
          </div>
          <span class="deadline-pill status-{st}">{badge_prazo}</span>
        </div>

        <a class="process-title" href="{it.get('url_principal', '#')}" target="_blank" rel="noopener noreferrer">{it.get('modalidade_numero', '')} — {it.get('entidade_nome', '')}</a>

        <div class="dates-row">
          <span><strong>Entidade:</strong> {it.get('entidade', '')}</span>
          <span><strong>Abertura:</strong> {it.get('data_inicio_br', '—')}</span>
          <span><strong>Prazo Final:</strong> <strong>{it.get('data_fim_br', '—')}</strong></span>
        </div>

        <div class="dossier-box">
          <div class="dossier-section">
            <div class="dossier-label">📌 Ementa / Objeto Literal (Texto Oficial da Fonte)</div>
            <p class="dossier-text">{it.get('ementa', '')}</p>
          </div>
          {resumo_ia_html}
          {obs_html}
        </div>

        <div class="docs-area">
          {botoes_docs}
        </div>
      </article>""")

    gaveta_html = ""
    if fora_filtro:
        linhas_fora = []
        for f_it in fora_filtro:
            linhas_fora.append(f"""
          <div style="padding:10px 14px;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
            <div>
              <strong style="color:#0f172a;font-size:0.86rem;">[{f_it.get('entidade')}] {f_it.get('modalidade_numero')}</strong>
              <span style="background:#f1f5f9;color:#475569;padding:2px 8px;border-radius:10px;font-size:0.74rem;margin-left:6px;">Motivo: {f_it.get('motivo_exclusao')}</span>
              <div style="color:#475569;font-size:0.8rem;margin-top:3px;">{f_it.get('ementa', '')[:220]}</div>
            </div>
            <div style="white-space:nowrap;font-size:0.78rem;">
              <span style="color:#64748b;margin-right:8px;">Prazo: {f_it.get('data_fim_br')}</span>
              <a href="{f_it.get('url_principal', '#')}" target="_blank" rel="noopener noreferrer" style="color:#0284c7;font-weight:700;text-decoration:none;">Conferir na Fonte ↗</a>
            </div>
          </div>""")

        gaveta_html = f"""
      <details style="margin-top:20px;background:#ffffff;border:1px solid #cbd5e1;border-radius:12px;overflow:hidden;">
        <summary style="padding:14px 18px;cursor:pointer;font-weight:700;color:#334155;font-size:0.88rem;background:#f8fafc;">
          🔎 Transparência do Filtro: {len(fora_filtro)} processo(s) ativo(s) em SUSEP/CVM fora do filtro temático (clique para inspecionar)
        </summary>
        <div>
          {''.join(linhas_fora)}
        </div>
      </details>"""

    return painel_fontes_html, "\n".join(blocos_aprovados), gaveta_html


def gerar_painel_radar_html(
    dossies: list,
    pasta_saida,
    itens_estruturacao: list = None,
    itens_leiloes: list = None,
    dados_sfn: dict = None,
) -> tuple:
    pasta_path = Path(pasta_saida)

    # Caso chamado pelo gerar_clipping.py sem passar explicitamente as abas 2, 3 e 4, coleta e cura automaticamente
    if itens_estruturacao is None or itens_leiloes is None or dados_sfn is None:
        try:
            import coletor_estruturacao_leiloes
            import curador_participativo
            import coletor_sfn
            if itens_estruturacao is None:
                brutos_est = coletor_estruturacao_leiloes.coletar_tudo_aba_estruturacao()
                itens_estruturacao = curador_participativo.curar_estruturacao_e_licitacoes(brutos_est, pasta_path)
            if itens_leiloes is None:
                itens_leiloes = coletor_estruturacao_leiloes.coletar_radar_leiloes()
            if dados_sfn is None:
                dados_sfn = coletor_sfn.coletar_tudo_aba_sfn()
                dados_sfn = curador_participativo.enriquecer_sfn_com_ia_lote(dados_sfn, pasta_path)
        except Exception as e:
            print(f"   [Aviso] Coleta complementar Abas 2/3/4: {e}")
            itens_estruturacao = itens_estruturacao or []
            itens_leiloes = itens_leiloes or []
            dados_sfn = dados_sfn or {"aprovados": [], "fora_do_filtro": [], "fontes_monitoradas": []}

    hoje = datetime.now()
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    data_formatada = f"{hoje.day:02d} de {meses[hoje.month]} de {hoje.year} às {hoje.strftime('%H:%M')}"

    # KPIs Aba 1 (Participativo)
    kpi_total = len(dossies)
    kpi_lancados_48h = sum(1 for d in dossies if d["status_ciclo"] == "LANCADO_48H")
    kpi_urgentes = sum(1 for d in dossies if d["status_ciclo"] == "PRAZO_URGENTE")
    kpi_abertos_regulares = sum(1 for d in dossies if d["status_ciclo"] == "ABERTO")
    kpi_pre = sum(1 for d in dossies if d["status_ciclo"] == "PRE_PUBLICACAO")
    kpi_encerrados = sum(1 for d in dossies if d["status_ciclo"] == "ENCERRADO_RECENTE")

    # KPIs Aba 2 (Estruturação & Contratações)
    est_total = len(itens_estruturacao)
    est_kpi_evtea = sum(1 for e in itens_estruturacao if e.get("categoria_item") == "PRIORIDADE_A_MPOR")
    est_kpi_seguros = sum(1 for e in itens_estruturacao if e.get("categoria_item") == "PRIORIDADE_B_COMPARACAO")
    est_kpi_carteira = sum(
        1 for e in itens_estruturacao
        if e.get("dias_restantes") is not None and e.get("dias_restantes") >= 0
    )

    # KPIs Aba 3 (Leilões)
    leil_total = len(itens_leiloes)
    leil_kpi_edital = sum(1 for l in itens_leiloes if l.get("fase_leilao") == "EDITAL_PUBLICADO")
    leil_kpi_tcu = sum(1 for l in itens_leiloes if l.get("fase_leilao") == "AVALIACAO_TCU_AJUSTES")
    leil_kpi_mpor = sum(1 for l in itens_leiloes if l.get("setor") in ("portos_hidrovias", "aeroportos"))

    cards_html_list = []
    if not dossies:
        cards_html_list.append('<div class="empty-state">Nenhum processo participativo ativo encontrado para os filtros atuais.</div>')
    else:
        for d in dossies:
            vert = d.get("vertical", "infra")
            nome_vert = NOMES_VERTICAIS.get(vert, "Infraestrutura & Outorgas")
            st = d["status_ciclo"]
            badge_prazo = formatar_badge_prazo(d)
            botoes_docs = renderizar_botoes_documentos(d)
            fim_iso = d.get("data_fim_iso", "")
            fim_br = d.get("data_fim_br", "—")
            ini_br = d.get("data_inicio_br", "—")
            pub_br = d.get("data_publicacao_br", "—")
            rotulo_pub = "Cadastro no Portal" if _inicio_anterior_a_publicacao(ini_br, pub_br) else "Publicação"

            cards_html_list.append(f"""
      <article class="dossier-card vertical-{vert}" data-status="{st}" data-vertical="{vert}" data-deadline-iso="{fim_iso}" data-fim-br="{fim_br}">
        <div class="card-top-meta">
          <div class="badges-left">
            <span class="badge badge-{vert}">{nome_vert}</span>
            <span class="badge badge-orgao">🏛️ {d.get('orgao_sigla', 'Governo Federal')}</span>
            <span class="badge badge-modalidade">{d.get('modalidade_exibicao', 'Processo')}</span>
          </div>
          <span class="deadline-pill status-{st}">{badge_prazo}</span>
        </div>

        <a class="process-title" href="{d['url']}" target="_blank" rel="noopener noreferrer">{d['titulo']}</a>

        <div class="dates-row">
          <span><strong>ID:</strong> #{d['id']}</span>
          <span><strong>{rotulo_pub}:</strong> {pub_br}</span>
          <span><strong>Janela de Contribuição:</strong> {ini_br} até {fim_br}</span>
        </div>

        <div class="dossier-box">
          <div class="dossier-section">
            <div class="dossier-label">📌 Objeto Normativo / O que está em discussão</div>
            <p class="dossier-text">{d.get('objeto_normativo', '')}</p>
          </div>
          <div class="incidencia-box">
            <div class="dossier-label">🎯 Ponto de Atenção & Oportunidade de Incidência</div>
            <p class="dossier-text">{d.get('pontos_atencao', '')}</p>
          </div>
        </div>

        <div class="docs-area">
          {botoes_docs}
        </div>
      </article>""")

    cards_estruturacao_html = _renderizar_cards_estruturacao(itens_estruturacao)
    cards_leiloes_html = _renderizar_cards_leiloes(itens_leiloes)
    painel_fontes_sfn_html, cards_sfn_html, gaveta_fora_filtro_sfn_html = _renderizar_aba_sfn(dados_sfn)

    sfn_aprovados_lista = (dados_sfn or {}).get("aprovados") or []
    sfn_fora_lista = (dados_sfn or {}).get("fora_do_filtro") or []
    sfn_total_aprovados = len(sfn_aprovados_lista)
    sfn_total_fora = len(sfn_fora_lista)
    sfn_kpi_abertos = sum(1 for x in sfn_aprovados_lista if (x.get("dias_restantes") is None or x.get("dias_restantes") >= 0))
    sfn_kpi_urgentes = sum(1 for x in sfn_aprovados_lista if x.get("status_ciclo") == "PRAZO_URGENTE")

    html_final = TEMPLATE_RADAR_HTML.format(
        data_formatada=data_formatada,
        kpi_total=kpi_total,
        kpi_lancados_48h=kpi_lancados_48h,
        kpi_urgentes=kpi_urgentes,
        kpi_abertos_regulares=kpi_abertos_regulares,
        kpi_pre=kpi_pre,
        kpi_encerrados=kpi_encerrados,
        cards_html="\n".join(cards_html_list),
        est_total=est_total,
        est_kpi_evtea=est_kpi_evtea,
        est_kpi_seguros=est_kpi_seguros,
        est_kpi_carteira=est_kpi_carteira,
        cards_estruturacao_html=cards_estruturacao_html,
        leil_total=leil_total,
        leil_kpi_edital=leil_kpi_edital,
        leil_kpi_tcu=leil_kpi_tcu,
        leil_kpi_mpor=leil_kpi_mpor,
        cards_leiloes_html=cards_leiloes_html,
        sfn_total_aprovados=sfn_total_aprovados,
        sfn_total_fora=sfn_total_fora,
        sfn_kpi_abertos=sfn_kpi_abertos,
        sfn_kpi_urgentes=sfn_kpi_urgentes,
        painel_fontes_sfn_html=painel_fontes_sfn_html,
        cards_sfn_html=cards_sfn_html,
        gaveta_fora_filtro_sfn_html=gaveta_fora_filtro_sfn_html,
    )

    caminho_atual = os.path.join(pasta_saida, "radar_atual.html")
    with open(caminho_atual, "w", encoding="utf-8") as f:
        f.write(html_final)

    return caminho_atual, caminho_atual

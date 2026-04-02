import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA (Otimizado para Mobile)
st.set_page_config(
    page_title="Richie Finance OS", 
    layout="wide", 
    initial_sidebar_state="collapsed", # Começa fechado para ganhar espaço no celular
    page_icon="🚀"
)

# Estilo CSS para melhorar o toque (Touch) e visual mobile
st.markdown("""
    <style>
    /* Estiliza botões para ocupar largura total e serem fáceis de clicar */
    .stButton button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    /* Ajusta o tamanho das métricas para não quebrar no celular */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; }
    /* Remove espaçamentos excessivos no topo */
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO E CARREGAMENTO
conn = st.connection("supabase", type="sql")

@st.cache_data(ttl=10)
def carregar_dados_pai():
    df = conn.query("SELECT * FROM fluxo_caixa_pai ORDER BY data_vencimento ASC;")
    if not df.empty:
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'])
        df['mes_ano'] = df['data_vencimento'].dt.strftime('%m/%Y')
    return df

@st.cache_data(ttl=10)
def carregar_investimentos():
    df = conn.query("SELECT * FROM investimentos ORDER BY data ASC;")
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
    return df

# 4. CARREGAMENTO INICIAL
df_pai_geral = carregar_dados_pai()
df_inv = carregar_investimentos()

# 5. SINCRONIZAÇÃO E CABEÇALHO
col_tit, col_sync = st.columns([3, 1])
with col_tit:
    st.title("🚀 Richie Finance")
with col_sync:
    if st.button("🔄"):
        st.cache_data.clear()
        st.rerun()

# 6. ABAS PRINCIPAIS
tab_pai, tab_inv, tab_cartoes = st.tabs(["🏦 Contas Pai", "📈 Invest", "💳 Cartões"])

# ==========================================
# ABA 1: GESTÃO DO PAI (SALDO ACUMULADO)
# ==========================================
with tab_pai:
    if not df_pai_geral.empty:
        # --- SELEÇÃO DE MÊS (SIDEBAR COM BOTÕES) ---
        lista_meses_cron = sorted(df_pai_geral['mes_ano'].unique(), 
                                 key=lambda x: datetime.strptime(x, '%m/%Y'))
        
        with st.sidebar:
            st.subheader("📅 Histórico")
            meses_botoes = lista_meses_cron[::-1] # Recentes primeiro
            
            if 'mes_selecionado' not in st.session_state:
                st.session_state.mes_selecionado = meses_botoes[0]

            for mes in meses_botoes:
                if st.button(mes, key=f"side_{mes}", use_container_width=True):
                    st.session_state.mes_selecionado = mes
        
        mes_ref = st.session_state.mes_selecionado

        # --- LÓGICA DE SALDO ROLADO ---
        idx_atual = lista_meses_cron.index(mes_ref)
        meses_anteriores = lista_meses_cron[:idx_atual]
        
        df_passado = df_pai_geral[df_pai_geral['mes_ano'].isin(meses_anteriores)]
        saldo_anterior = df_passado[df_passado['tipo_movimento'] == 'Entrada']['custo'].sum() - \
                         df_passado[df_passado['tipo_movimento'] == 'Saída']['custo'].sum()

        df_mes = df_pai_geral[df_pai_geral['mes_ano'] == mes_ref]
        entradas_mes = df_mes[df_mes['tipo_movimento'] == 'Entrada']['custo'].sum()
        saidas_mes = df_mes[df_mes['tipo_movimento'] == 'Saída']['custo'].sum()
        disponivel_final = saldo_anterior + entradas_mes - saidas_mes

        # --- MÉTRICAS (EM GRADE 2x2 PARA MOBILE) ---
        st.write(f"### Resumo de **{mes_ref}**")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("⬅️ Saldo Ant.", f"R${saldo_anterior:,.2f}")
        m_col2.metric("➕ Entradas", f"R${entradas_mes:,.2f}")
        
        m_col3, m_col4 = st.columns(2)
        # Delta de gastos vs mês anterior
        delta_saidas = 0
        if idx_atual > 0:
            mes_ant = lista_meses_cron[idx_atual - 1]
            saidas_ant = df_pai_geral[(df_pai_geral['mes_ano'] == mes_ant) & (df_pai_geral['tipo_movimento'] == 'Saída')]['custo'].sum()
            delta_saidas = saidas_mes - saidas_ant
        
        m_col3.metric("💸 Saídas", f"R${saidas_mes:,.2f}", f"{delta_saidas:,.2f}", delta_color="inverse")
        m_col4.metric("💰 Disponível", f"R${disponivel_final:,.2f}")

        # --- ADICIONAR CONTA (EXPANDER PARA ECONOMIZAR ESPAÇO) ---
        with st.expander("➕ Novo Lançamento"):
            with st.form("form_mobile", clear_on_submit=True):
                v_det = st.text_input("O que é?")
                v_val = st.number_input("Valor", min_value=0.0, step=0.01)
                v_cat = st.selectbox("Categoria", ["Aluguel Granatto", "Du", "PUC", "Nubank", "Gás", "Condomínio", "Limpeza", "Compras", "PIX", "Outros"])
                v_tipo = st.radio("Tipo", ["Saída", "Entrada"], horizontal=True)
                v_data = st.date_input("Data")
                v_pago = st.checkbox("Pago?", value=True)
                if st.form_submit_button("Salvar"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO fluxo_caixa_pai (data_vencimento, detalhes_despesa, categoria, custo, pago, tipo_movimento) VALUES (:d, :det, :c, :v, :p, :t)"),
                                  {"d": v_data, "det": v_det, "c": v_cat, "v": v_val, "p": v_pago, "t": v_tipo})
                        s.commit()
                    st.cache_data.clear()
                    st.rerun()

        # --- EDITOR DE DADOS (EXTRATO) ---
        st.write("### 📝 Extrato Detalhado")
        df_edit = df_mes[['id', 'detalhes_despesa', 'custo', 'pago', 'categoria', 'tipo_movimento']].copy()
        
        dados_editados = st.data_editor(
            df_edit,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            disabled=["id"],
            column_config={
                "pago": st.column_config.CheckboxColumn("✔"),
                "custo": st.column_config.NumberColumn("R$", format="%.2f", width="small"),
                "detalhes_despesa": st.column_config.TextColumn("Detalhe"),
                "categoria": st.column_config.SelectboxColumn("Cat", options=["Aluguel Granatto", "Du", "PUC", "Nubank", "Gás", "Condomínio", "Limpeza", "Compras", "PIX", "Outros"])
            }
        )

        if st.button("💾 Salvar Alterações"):
            ids_finais = set(dados_editados['id'].dropna())
            ids_iniciais = set(df_edit['id'])
            
            with conn.session as s:
                # 1. Deletar removidos
                for id_del in (ids_iniciais - ids_finais):
                    s.execute(text("DELETE FROM fluxo_caixa_pai WHERE id = :i"), {"i": id_del})
                # 2. Atualizar existentes
                for _, row in dados_editados.iterrows():
                    if pd.notna(row['id']):
                        s.execute(text("UPDATE fluxo_caixa_pai SET detalhes_despesa=:d, custo=:v, pago=:p, categoria=:c, tipo_movimento=:t WHERE id=:i"),
                                  {"d": row['detalhes_despesa'], "v": row['custo'], "p": row['pago'], "c": row['categoria'], "t": row['tipo_movimento'], "i": row['id']})
                s.commit()
            st.success("Sincronizado!")
            st.cache_data.clear()
            st.rerun()

# ==========================================
# ABA 2: INVESTIMENTOS (PREÇO MÉDIO)
# ==========================================
with tab_inv:
    st.header("📈 Patrimônio")
    if not df_inv.empty:
        portfolio = {}
        for _, row in df_inv.iterrows():
            tk, tp, q, pr = row['ticker'], row['tipo'], float(row['quantidade']), float(row['preco'])
            if tk not in portfolio: portfolio[tk] = {'qtd': 0.0, 'custo': 0.0, 'pm': 0.0}
            if tp == 'Compra':
                portfolio[tk]['custo'] += (q * pr)
                portfolio[tk]['qtd'] += q
                if portfolio[tk]['qtd'] > 0: portfolio[tk]['pm'] = portfolio[tk]['custo'] / portfolio[tk]['qtd']
            elif tp == 'Venda':
                if portfolio[tk]['qtd'] > 0:
                    custo_venda = q * portfolio[tk]['pm']
                    portfolio[tk]['qtd'] -= q
                    portfolio[tk]['custo'] -= custo_venda

        resumo = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
        resumo.columns = ['Ticker', 'Qtd', 'Investido', 'PM']
        resumo = resumo[resumo['Qtd'] > 0.000001]
        st.dataframe(resumo, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados.")

# ==========================================
# ABA 3: CARTÕES
# ==========================================
with tab_cartoes:
    st.header("💳 Cartões")
    st.info("Área futura.")

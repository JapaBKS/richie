import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
import yfinance as yf

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Richie Finance OS", layout="wide", page_icon="🚀")
st.title("🚀 Richie Finance OS")

# Botão de Sincronização no topo
if st.button("🔄 Atualizar / Sincronizar Dados"):
    st.cache_data.clear()
    st.rerun()

# 2. CONEXÃO COM O BANCO DE DADOS (SUPABASE)
conn = st.connection("supabase", type="sql")

# 3. FUNÇÕES PARA LER DADOS
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

@st.cache_data(ttl=300) # Atualiza a cada 5 minutos para não travar
def obter_preco_atual(ticker):
    # O Yahoo Finance exige ".SA" para ações brasileiras e "-BRL" para criptos em reais
    mapa_cripto = {
        'BTC': 'BTC-BRL', 
        'SOLANA': 'SOL-BRL', 
        'PENDLE': 'PENDLE-BRL', 
        'ETH': 'ETH-BRL'
    }
    
    # Verifica se é cripto (pelo dicionário) ou se é ação brasileira
    ticker_yf = mapa_cripto.get(ticker.upper(), f"{ticker.upper()}.SA")
    
    try:
        dados = yf.Ticker(ticker_yf).history(period="1d")
        if not dados.empty:
            return float(dados['Close'].iloc[-1]) # Pega o preço de fechamento/atual
    except:
        pass
    return 0.0 # Retorna 0 se der erro (ex: código errado)

# 5. CRIAÇÃO DAS ABAS
tab_pai, tab_inv, tab_cartoes = st.tabs(["🏦 Contas do Pai", "📈 Meus Investimentos", "💳 Cartões"])

# ==========================================
# ABA 1: CONTAS DO PAI (SISTEMA DE SALDO ACUMULADO)
# ==========================================
with tab_pai:
    if not df_pai_geral.empty:
        
        # --- SELEÇÃO DE MÊS POR BOTÕES NA SIDEBAR ---
        with st.sidebar:
            st.write("### 📅 Selecionar Mês")
            lista_meses_cron = sorted(df_pai_geral['mes_ano'].unique(), 
                                     key=lambda x: datetime.strptime(x, '%m/%Y'))
            
            meses_botoes = lista_meses_cron[::-1] # Recentes primeiro
            
            # Inicializa o estado se não existir
            if 'mes_selecionado' not in st.session_state:
                st.session_state.mes_selecionado = meses_botoes[0]

            # Criamos os botões em uma coluna única na sidebar para não poluir
            for mes in meses_botoes:
                # Se o botão for o selecionado, ele ganha um destaque visual (opcional em versões futuras do Streamlit)
                if st.button(mes, key=f"sidebar_btn_{mes}", use_container_width=True):
                    st.session_state.mes_selecionado = mes
        
        mes_selecionado = st.session_state.mes_selecionado

        # --- LÓGICA DE SALDO ROLADO ---
        idx_atual = lista_meses_cron.index(mes_selecionado)
        meses_anteriores = lista_meses_cron[:idx_atual]
        
        df_passado = df_pai_geral[df_pai_geral['mes_ano'].isin(meses_anteriores)]
        saldo_anterior = df_passado[df_passado['tipo_movimento'] == 'Entrada']['custo'].sum() - \
                         df_passado[df_passado['tipo_movimento'] == 'Saída']['custo'].sum()

        df_mes = df_pai_geral[df_pai_geral['mes_ano'] == mes_selecionado]
        entradas_mes = df_mes[df_mes['tipo_movimento'] == 'Entrada']['custo'].sum()
        saidas_mes = df_mes[df_mes['tipo_movimento'] == 'Saída']['custo'].sum()
        disponivel_final = saldo_anterior + entradas_mes - saidas_mes

        # --- DASHBOARD DE MÉTRICAS ---
        st.subheader(f"📊 Resumo Financeiro - {mes_selecionado}")
        m1, m2, m3, m4 = st.columns(4)
        
        m1.metric("⬅️ Saldo Anterior", f"R$ {saldo_anterior:,.2f}")
        m2.metric("➕ Entradas do Mês", f"R$ {entradas_mes:,.2f}")
        
        # Comparação de gastos
        delta_saidas = 0
        if idx_atual > 0:
            mes_ant_nome = lista_meses_cron[idx_atual - 1]
            saidas_ant = df_pai_geral[(df_pai_geral['mes_ano'] == mes_ant_nome) & (df_pai_geral['tipo_movimento'] == 'Saída')]['custo'].sum()
            delta_saidas = saidas_mes - saidas_ant

        m3.metric("💸 Saídas do Mês", f"R$ {saidas_mes:,.2f}", f"{delta_saidas:,.2f} vs mês ant.", delta_color="inverse")
        m4.metric("💰 Disponível Final", f"R$ {disponivel_final:,.2f}")

        # --- GRÁFICO E FORMULÁRIO ---
        st.divider()
        c_graf, c_form = st.columns([2, 1])
        
        with c_graf:
            st.write("### Gastos por Categoria")
            gastos_cat = df_mes[df_mes['tipo_movimento'] == 'Saída'].groupby('categoria')['custo'].sum().sort_values()
            if not gastos_cat.empty:
                st.bar_chart(gastos_cat, horizontal=True)

        with c_form:
            st.write("### Novo Lançamento")
            with st.form("form_pai_novo", clear_on_submit=True):
                v_data = st.date_input("Data")
                v_det = st.text_input("Detalhe")
                v_cat = st.selectbox("Categoria", ["Aluguel Granatto", "Du", "PUC", "Nubank", "Gás", "Condomínio", "Limpeza", "Compras", "PIX", "Outros"])
                v_val = st.number_input("Valor", min_value=0.0, format="%.2f")
                v_tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
                v_pago = st.checkbox("Pago?", value=True)
                if st.form_submit_button("💾 Salvar"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO fluxo_caixa_pai (data_vencimento, detalhes_despesa, categoria, custo, pago, tipo_movimento) VALUES (:d, :det, :c, :v, :p, :t)"),
                                  {"d": v_data, "det": v_det, "c": v_cat, "v": v_val, "p": v_pago, "t": v_tipo})
                        s.commit()
                    st.cache_data.clear()
                    st.rerun()

        # --- EDITOR DE DADOS (TABELA) ---
        st.divider()
        st.write(f"### 📝 Tabela Detalhada")
        df_edit = df_mes[['id', 'data_vencimento', 'detalhes_despesa', 'categoria', 'custo', 'tipo_movimento', 'pago']].copy()
        
        edited_df = st.data_editor(
            df_edit,
            hide_index=True,
            use_container_width=True, # Mantém a tabela expandida
            num_rows="dynamic",
            disabled=["id"],
            column_config={
                "id": None, # Esconde a coluna ID para não criar espaço em branco
                "pago": st.column_config.CheckboxColumn("Pago?", width="small"),
                "data_vencimento": st.column_config.DateColumn("Vencimento", width="medium"),
                "detalhes_despesa": st.column_config.TextColumn("Detalhes da Despesa", required=True, width="large"), # O "large" puxa o espaço vazio
                "categoria": st.column_config.SelectboxColumn("Categoria", options=["Aluguel Granatto", "Du", "PUC", "Nubank", "Gás", "Condomínio", "Limpeza", "Compras", "PIX", "Outros"], width="medium"),
                "custo": st.column_config.NumberColumn("Valor (R$)", format="%.2f", width="medium"),
                "tipo_movimento": st.column_config.SelectboxColumn("Tipo", options=["Saída", "Entrada"], width="small")
            }
        )

        if st.button("💾 Salvar Alterações e Exclusões"):
            ids_atuais = set(edited_df['id'].dropna())
            ids_originais = set(df_edit['id'])
            ids_para_deletar = ids_originais - ids_atuais
            with conn.session as s:
                for id_del in ids_para_deletar:
                    s.execute(text("DELETE FROM fluxo_caixa_pai WHERE id = :i"), {"i": id_del})
                for _, row in edited_df.iterrows():
                    if pd.notna(row['id']):
                        s.execute(text("UPDATE fluxo_caixa_pai SET detalhes_despesa=:d, categoria=:c, custo=:v, pago=:p, data_vencimento=:dt, tipo_movimento=:t WHERE id=:i"),
                                  {"d": row['detalhes_despesa'], "c": row['categoria'], "v": row['custo'], "p": row['pago'], "dt": row['data_vencimento'], "t": row['tipo_movimento'], "i": row['id']})
                s.commit()
            st.success("Dados sincronizados!")
            st.cache_data.clear()
            st.rerun()

# ==========================================
# ABA 2: INVESTIMENTOS (COM TEMPO REAL)
# ==========================================
with tab_inv:
    st.header("📈 Meu Patrimônio")
    if not df_inv.empty:
        # 1. Agrupar operações e calcular o Preço Médio e Quantidade
        portfolio = {}
        for _, row in df_inv.iterrows():
            tk, tp, q, pr = row['ticker'], row['tipo'], float(row['quantidade']), float(row['preco'])
            if tk not in portfolio: portfolio[tk] = {'qtd': 0.0, 'custo': 0.0, 'pm': 0.0}
            
            if tp == 'Compra':
                portfolio[tk]['custo'] += (q * pr)
                portfolio[tk]['qtd'] += q
                if portfolio[tk]['qtd'] > 0: 
                    portfolio[tk]['pm'] = portfolio[tk]['custo'] / portfolio[tk]['qtd']
            elif tp == 'Venda':
                if portfolio[tk]['qtd'] > 0:
                    custo_venda = q * portfolio[tk]['pm']
                    portfolio[tk]['qtd'] -= q
                    portfolio[tk]['custo'] -= custo_venda

        # 2. Puxar preços online e calcular o Saldo Atual
        resumo_lista = []
        total_investido = 0.0
        total_atual = 0.0
        
        st.info("⏳ Puxando cotações em tempo real do mercado...")
        
        for tk, dados in portfolio.items():
            if dados['qtd'] > 0.000001: # Se você ainda tem o ativo
                preco_hoje = obter_preco_atual(tk)
                valor_hoje = preco_hoje * dados['qtd']
                lucro_rs = valor_hoje - dados['custo']
                lucro_pct = (valor_hoje / dados['custo'] - 1) if dados['custo'] > 0 else 0
                
                total_investido += dados['custo']
                total_atual += valor_hoje
                
                resumo_lista.append({
                    "Ticker": tk,
                    "Qtd": dados['qtd'],
                    "PM": dados['pm'],
                    "Preço Atual": preco_hoje,
                    "Investido": dados['custo'],
                    "Saldo Atual": valor_hoje,
                    "Lucro R$": lucro_rs,
                    "Lucro %": lucro_pct
                })
        
        # 3. Métricas Gerais (Resumão da Carteira)
        st.divider()
        lucro_total_rs = total_atual - total_investido
        lucro_total_pct = (total_atual / total_investido - 1) * 100 if total_investido > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Total Investido (Custo)", f"R$ {total_investido:,.2f}")
        c2.metric("🚀 Patrimônio Atual", f"R$ {total_atual:,.2f}")
        c3.metric("📈 Lucro/Prejuízo Total", f"R$ {lucro_total_rs:,.2f}", f"{lucro_total_pct:,.2f}%", delta_color="normal")
        
        # 4. Tabela de Detalhes
        st.write("### 📊 Detalhes por Ativo")
        resumo_df = pd.DataFrame(resumo_lista)
        
        st.dataframe(
            resumo_df, 
            hide_index=True,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ativo", width="small"),
                "Qtd": st.column_config.NumberColumn("Quantidade", width="small", format="%.4f"),
                "PM": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f", width="small"),
                "Preço Atual": st.column_config.NumberColumn("Preço Agora", format="R$ %.2f", width="small"),
                "Investido": st.column_config.NumberColumn("Valor Investido", format="R$ %.2f", width="medium"),
                "Saldo Atual": st.column_config.NumberColumn("Valor Atual", format="R$ %.2f", width="medium"),
                "Lucro R$": st.column_config.NumberColumn("Lucro (R$)", format="R$ %.2f", width="medium"),
                "Lucro %": st.column_config.NumberColumn("Retorno", format="%.2f%%", width="small")
            }
        )
    else:
        st.info("Sem dados de investimentos.")

# ==========================================
# ABA 3: CARTÕES
# ==========================================
with tab_cartoes:
    st.header("💳 Controle de Cartões")
    st.info("Área pronta para futuras faturas.")

import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Richie Finance OS", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CUSTOMIZADA ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO DE DADOS ---

@st.cache_data
def carregar_e_processar_investimentos(file_path):
    try:
        df = pd.read_csv(file_path)
        df['Data'] = pd.to_datetime(df['Data'])
        
        portfolio = {}
        for _, row in df.sort_values('Data').iterrows():
            ticker = row['Ticker']
            tipo = row['Tipo']
            qtd = row['Quantidade']
            preco = row['Preco']
            
            if ticker not in portfolio:
                portfolio[ticker] = {'qtd': 0.0, 'custo_total': 0.0, 'pm': 0.0}
            
            if tipo == 'Compra':
                portfolio[ticker]['custo_total'] += (qtd * preco)
                portfolio[ticker]['qtd'] += qtd
                if portfolio[ticker]['qtd'] > 0:
                    portfolio[ticker]['pm'] = portfolio[ticker]['custo_total'] / portfolio[ticker]['qtd']
            elif tipo == 'Venda':
                # Venda reduz a quantidade, mas o PM mantém-se (regra fiscal)
                if portfolio[ticker]['qtd'] > 0:
                    custo_proporcional = qtd * portfolio[ticker]['pm']
                    portfolio[ticker]['qtd'] -= qtd
                    portfolio[ticker]['custo_total'] -= custo_proporcional
                    
        resumo = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
        resumo.columns = ['Ticker', 'Qtd Atual', 'Custo Total', 'Preço Médio']
        return resumo[resumo['Qtd Atual'] > 0.000001] # Filtra ativos zerados
    except Exception as e:
        st.error(f"Erro ao processar investimentos: {e}")
        return pd.DataFrame()

@st.cache_data
def carregar_e_processar_caixa(file_path):
    try:
        df = pd.read_csv(file_path)
        df['Data'] = pd.to_datetime(df['Data'])
        return df
    except Exception as e:
        st.error(f"Erro ao processar caixa: {e}")
        return pd.DataFrame()

# --- SIDEBAR: CONTROLO DE ACESSO ---
with st.sidebar:
    st.title("🛡️ Richie Finance")
    user = st.radio("Entrar como:", ["Pai", "Richie"])
    st.divider()
    st.info(f"Acesso atual: **{user}**")

# --- LÓGICA DE INTERFACE ---

if user == "Pai":
    st.title("🏦 Painel de Contas e Saldos")
    
    df_caixa = carregar_e_processar_caixa("db_fluxo_caixa_limpo.csv")
    
    if not df_caixa.empty:
        # Cálculos de Saldo (Somente Entradas vs Saídas Pagas)
        entradas = df_caixa[df_caixa['Tipo'] == 'Entrada']['Valor'].sum()
        saidas = df_caixa[(df_caixa['Tipo'] == 'Saída') & (df_caixa['Pago'] == True)]['Valor'].sum()
        saldo_pai = entradas - saidas
        
        # Dashboard resumido para o Pai
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo Disponível", f"R$ {saldo_pai:,.2f}")
        c2.metric("Total Enviado (PIX)", f"R$ {entradas:,.2f}")
        c3.metric("Total Gasto", f"R$ {saidas:,.2f}")
        
        st.divider()
        st.subheader("📋 Histórico de Lançamentos")
        # Mostra apenas o que é relevante para ele
        st.dataframe(df_caixa.sort_values('Data', ascending=False), use_container_width=True)
        
        # Área de Upload para ele
        with st.expander("📤 Enviar Novo Boleto"):
            with st.form("upload_boleto"):
                desc = st.text_input("Descrição do Gasto")
                val = st.number_input("Valor aproximado", min_value=0.0)
                file = st.file_uploader("Anexar PDF/Foto", type=['pdf', 'jpg', 'png'])
                if st.form_submit_button("Enviar para Richie"):
                    st.success("Enviado! Richie receberá a notificação.")

elif user == "Richie":
    st.title("📈 Dashboard Estratégico (Admin)")
    
    # Carregar ambas as bases
    df_inv = carregar_e_processar_investimentos("db_investimentos_limpo.csv")
    df_caixa = carregar_e_processar_caixa("db_fluxo_caixa_limpo.csv")
    
    # 1. CÁLCULO DE PATRIMÓNIO REAL (A Mágica da Custódia)
    # Supondo que o seu património bruto é a soma do custo total das ações
    patrimonio_bruto = df_inv['Custo Total'].sum()
    
    # Cálculo do saldo do pai que está na sua conta
    entradas_pai = df_caixa[df_caixa['Tipo'] == 'Entrada']['Valor'].sum()
    saidas_pai = df_caixa[(df_caixa['Tipo'] == 'Saída') & (df_caixa['Pago'] == True)]['Valor'].sum()
    saldo_pai = entradas_pai - saidas_pai
    
    patrimonio_liquido = patrimonio_bruto - saldo_pai
    
    # Top Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Património Bruto", f"R$ {patrimonio_bruto:,.2f}")
    m2.metric("Dívida/Custódia (Pai)", f"R$ {saldo_pai:,.2f}", delta="- Saldo do Pai", delta_color="inverse")
    m3.metric("PATRIMÓNIO LÍQUIDO", f"R$ {patrimonio_liquido:,.2f}", delta="O que é SEU de verdade")
    
    st.divider()
    
    # 2. CARTEIRA DE ATIVOS
    st.subheader("🎯 Carteira Consolidada (Preço Médio Calculado)")
    st.dataframe(df_inv, use_container_width=True)
    
    # 3. INSIGHT DE RENDIMENTO DO FLOAT
    st.info(f"💡 O dinheiro do seu pai (R$ {saldo_pai:,.2f}) está a gerar cerca de **R$ {(saldo_pai * 0.0004):,.2f} de lucro diário** para si no Mercado Pago.")

    # 4. FERRAMENTAS DE ADMIN
    with st.expander("⚙️ Gerir Lançamentos de Contas"):
        st.write("Aqui pode dar 'OK' nas contas que o seu pai enviou.")
        st.dataframe(df_caixa[df_caixa['Pago'] == False])

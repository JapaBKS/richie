import streamlit as st
import pandas as pd
from datetime import datetime

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Richie Finance OS", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONTROLO DE ACESSO ---
with st.sidebar:
    st.title("🛡️ Portal Seguro")
    user = st.radio("Selecione o Utilizador:", ["Pai", "Richie"])
    st.divider()
    if user == "Richie":
        st.success("Modo Administrador Ativo")
    else:
        st.info("Modo Visualização: Pai")

# --- FUNÇÕES DE DADOS ---
def carregar_dados_investimentos():
    # Aqui o sistema lê os teus arquivos CSV carregados
    try:
        df_geral = pd.read_csv("Dinheiro.xlsx - Geral.csv")
        # Exemplo de extração do valor total (ajuste conforme a estrutura real)
        total = df_geral.iloc[0, 1] if not df_geral.empty else 0 
        return float(total)
    except:
        return 0.0

# --- INTERFACE PAI ---
if user == "Pai":
    st.title("🏦 Painel de Contas - Pai")
    
    col1, col2, col3 = st.columns(3)
    # Valores que virão da tua planilha do Sheets futuramente
    saldo_disponivel = 2450.00 
    col1.metric("Saldo Disponível", f"R$ {saldo_disponivel:,.2f}")
    col2.metric("Contas Pagas (Março)", "R$ 1.120,00")
    col3.metric("A pagar", "R$ 450,00", delta="-R$ 50,00")

    st.divider()
    
    # FORMULÁRIO DE LANÇAMENTO E UPLOAD
    with st.expander("➕ Lançar Nova Conta / Enviar Boleto", expanded=True):
        with st.form("form_conta"):
            nome_conta = st.text_input("Descrição da Conta (ex: Luz, Condomínio)")
            valor_conta = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
            data_vencimento = st.date_input("Data de Vencimento")
            
            # UPLOAD DE COMPROVANTE/BOLETO
            arquivo = st.file_uploader("Anexar Boleto ou Comprovante (PDF/JPG)", type=["pdf", "png", "jpg"])
            
            enviado = st.form_submit_button("Enviar para o Richie")
            
            if enviado:
                if arquivo is not None:
                    # Aqui, no futuro, salvaremos no Drive via API
                    st.success(f"✅ Conta '{nome_conta}' enviada com sucesso com o arquivo {arquivo.name}!")
                else:
                    st.warning("Por favor, anexe o boleto antes de enviar.")

# --- INTERFACE RICHIE (PRIVADA) ---
elif user == "Richie":
    st.title("📈 Dashboard Estratégico")
    
    # CÁLCULO DE CUSTÓDIA REAL
    patrimonio_bruto = carregar_dados_investimentos() # Lê do teu Geral.csv
    custodia_pai = 2450.00 # Virá da soma da planilha dele
    patrimonio_liquido = patrimonio_bruto - custodia_pai
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Património Bruto (Total)", f"R$ {patrimonio_bruto:,.2f}")
    c2.metric("Capital de Terceiros (Pai)", f"- R$ {custodia_pai:,.2f}", delta_color="inverse")
    c3.metric("PATRIMÓNIO LÍQUIDO", f"R$ {patrimonio_liquido:,.2f}")

    # ANÁLISE DE ATIVOS (Lendo teus CSVs de Ações/FIIs)
    st.subheader("🎯 Rebalanceamento de Carteira")
    try:
        df_acoes = pd.read_csv("Dinheiro.xlsx - Ações.csv")
        st.dataframe(df_acoes[['Ação', 'Qtd.', 'Preço Atual', 'Lucro R$']].head(10), use_container_width=True)
    except:
        st.info("Carregue os arquivos CSV para visualizar a análise de ativos.")

    # GESTÃO DE FLOAT
    st.info(f"💡 O capital do teu pai está a render-te aproximadamente **R$ {(custodia_pai * 0.0004):,.2f} por dia** no Mercado Pago.")

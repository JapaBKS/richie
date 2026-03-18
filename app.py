import streamlit as st
import pandas as pd

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema Financeiro Richie", layout="wide")

# 1. AUTENTICAÇÃO SIMPLES (Para começar)
st.sidebar.title("🔐 Acesso")
usuario = st.sidebar.selectbox("Quem está a aceder?", ["Selecionar", "Pai", "Richie"])

if usuario == "Pai":
    st.title(f"👋 Olá, Pai")
    st.subheader("Contas e Saldo")
    
    # Simulação de dados (Aqui ligaremos à tua Google Sheet depois)
    # No futuro, usaremos st.connection("gsheets")
    st.info("Aqui verá apenas as suas contas pagas e o saldo disponível.")
    
    # Exemplo de Dashboard para ele
    col1, col2 = st.columns(2)
    col1.metric("Saldo com o Richie", "R$ 2.450,00")
    col2.metric("Contas este mês", "4", delta="-2")

elif usuario == "Richie":
    st.title("📊 Painel Estratégico - Richie")
    
    # ABA PRIVADA QUE O PAI NÃO VÊ
    with st.expander("💼 Ver Meu Património Real", expanded=True):
        # Aqui o sistema lê os teus CSVs
        # Exemplo: df_geral = pd.read_csv("Dinheiro.xlsx - Geral.csv")
        
        patrimonio_total = 38000.00  # Valor vindo do teu Geral.csv
        custodia_pai = 2450.00       # Valor vindo da planilha dele
        liquido_real = patrimonio_total - custodia_pai
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Património Total", f"R$ {patrimonio_total:,.2f}")
        c2.metric("Custódia (Pai)", f"- R$ {custodia_pai:,.2f}", delta_color="inverse")
        c3.metric("Líquido REAL", f"R$ {liquido_real:,.2f}")

    st.divider()
    st.subheader("Análise de Rebalanceamento")
    st.write("Dados extraídos das tuas planilhas de Ações e FIIs...")

else:
    st.warning("Por favor, selecione um utilizador na barra lateral para continuar.")

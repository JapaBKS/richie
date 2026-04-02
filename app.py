import streamlit as st

st.set_page_config(page_title="Richie Finance OS", layout="wide")

st.title("🚀 Richie Finance: Conectado à Nuvem!")

# A conexão mágica
conn = st.connection("supabase", type="sql")

st.subheader("🏦 Tabela de Fluxo de Caixa (Pai)")

try:
    # Puxa os dados direto do seu Supabase
    df_caixa = conn.query("SELECT * FROM fluxo_caixa_pai ORDER BY data_vencimento DESC")
    
    if df_caixa.empty:
        st.warning("A tabela está conectada, mas ainda está vazia. Precisamos importar os dados!")
    else:
        st.success(f"Sucesso! O sistema encontrou {len(df_caixa)} lançamentos na nuvem.")
        st.dataframe(df_caixa, use_container_width=True)
        
        # Um gostinho do que o sistema vai fazer sozinho:
        total_saidas = df_caixa[df_caixa['tipo_movimento'] == 'Saída']['custo'].sum()
        st.metric("Total de Saídas Registradas", f"R$ {total_saidas:,.2f}")

except Exception as e:
    st.error(f"Erro ao ler os dados: {e}")

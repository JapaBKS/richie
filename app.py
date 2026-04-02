import streamlit as st
import pandas as pd

st.set_page_config(page_title="Migrador Supabase", layout="wide")
st.title("🚚 O Camião de Mudanças: CSV -> Nuvem")
st.write("Arrasta os teus ficheiros antigos para aqui e envia-os para a tua nova Base de Dados.")

# --- LIGAÇÃO À BASE DE DADOS ---
try:
    conn = st.connection("supabase", type="sql")
    st.success("✅ Ligação ao Supabase estabelecida com sucesso!")
except Exception as e:
    st.error(f"⚠️ Erro ao ligar. Verifica os 'Secrets' no Streamlit: {e}")
    st.stop()

# --- FUNÇÃO DE LIMPEZA DE MOEDA ---
def limpar_moeda(val):
    if pd.isna(val) or str(val).lower() == 'nan': return 0.0
    val = str(val).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
    try: return float(val)
    except: return 0.0

col1, col2 = st.columns(2)

# ==========================================
# MÓDULO 1: HISTÓRICO DE INVESTIMENTOS
# ==========================================
with col1:
    st.subheader("📈 1. Migrar Investimentos")
    ficheiro_inv = st.file_uploader("Anexa o ficheiro 'negociacoes.CSV'", type=['csv'])
    
    if ficheiro_inv is not None:
        # Ler e limpar diretamente do ficheiro enviado no ecrã
        df_inv = pd.read_csv(ficheiro_inv, sep=';', header=None, names=['data', 'tipo', 'ticker', 'quantidade', 'preco', 'extra'], on_bad_lines='skip')
        df_inv['preco'] = df_inv['preco'].apply(limpar_moeda)
        df_inv['quantidade'] = df_inv['quantidade'].apply(limpar_moeda)
        df_inv['data'] = pd.to_datetime(df_inv['data'], dayfirst=True, errors='coerce')
        df_inv = df_inv.dropna(subset=['data'])[['data', 'tipo', 'ticker', 'quantidade', 'preco']]
        
        st.info(f"Ficheiro lido! Pronto a enviar: {len(df_inv)} registos.")
        
        if st.button("📤 Enviar Ações/Cripto para a Nuvem"):
            with st.spinner("A enviar..."):
                df_inv.to_sql('investimentos', con=conn.engine, if_exists='append', index=False)
                st.success("✅ Investimentos migrados para sempre!")

# ==========================================
# MÓDULO 2: HISTÓRICO DO PAI (Fluxo de Caixa)
# ==========================================
with col2:
    st.subheader("🏦 2. Migrar Contas do Pai")
    ficheiro_pai = st.file_uploader("Anexa o ficheiro 'pai.csv'", type=['csv'])
    
    if ficheiro_pai is not None:
        # Ler ignorando as colunas extra do Excel (focando só no que importa)
        df_caixa = pd.read_csv(ficheiro_pai, sep=';', header=None, names=['data_vencimento', 'detalhes_despesa', 'categoria', 'custo', 'pago', 'tipo_movimento'], on_bad_lines='skip')
        
        df_caixa['custo'] = df_caixa['custo'].apply(limpar_moeda)
        df_caixa['data_vencimento'] = pd.to_datetime(df_caixa['data_vencimento'], dayfirst=True, errors='coerce')
        df_caixa['pago'] = df_caixa['pago'].map({'TRUE': True, 'True': True, True: True, 'FALSE': False, 'False': False, False: False})
        df_caixa = df_caixa.dropna(subset=['data_vencimento'])
        
        st.info(f"Ficheiro lido! Pronto a enviar: {len(df_caixa)} registos.")
        
        if st.button("📤 Enviar Contas do Pai para a Nuvem"):
            with st.spinner("A enviar..."):
                df_caixa.to_sql('fluxo_caixa_pai', con=conn.engine, if_exists='append', index=False)
                st.success("✅ Contas do Pai migradas para sempre!")

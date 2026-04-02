import streamlit as st
import pandas as pd
from sqlalchemy import text # Necessário para o comando INSERT

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Richie Finance OS", layout="wide", page_icon="🚀")
st.title("🚀 Richie Finance OS")

# 2. LIGAÇÃO AO BANCO DE DADOS (SUPABASE)
conn = st.connection("supabase", type="sql")

# 3. FUNÇÕES PARA LER DADOS (Com Cache para ser rápido)
@st.cache_data(ttl=10) # Atualiza a cada 10 segundos
def carregar_caixa_pai():
    df = conn.query("SELECT * FROM fluxo_caixa_pai ORDER BY data_vencimento DESC;")
    if not df.empty:
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'])
    return df

@st.cache_data(ttl=10)
def carregar_investimentos():
    df = conn.query("SELECT * FROM investimentos ORDER BY data ASC;")
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
    return df

# 4. CRIAÇÃO DAS ABAS (TABS)
tab_pai, tab_inv, tab_cartoes = st.tabs(["🏦 Contas do Pai", "📈 Meus Investimentos", "💳 Despesas Cartão (Em Breve)"])

# ==========================================
# ABA 1: CONTAS DO PAI
# ==========================================
with tab_pai:
    st.header("Fluxo de Caixa - Pai")
    
    # --- FORMULÁRIO PARA ADICIONAR NOVA CONTA ---
    with st.expander("➕ Adicionar Nova Despesa / Entrada", expanded=False):
        with st.form("form_novo_gasto_pai", clear_on_submit=True):
            st.write("Preenche os dados para guardar na nuvem:")
            
            c1, c2, c3 = st.columns(3)
            nova_data = c1.date_input("Data de Vencimento")
            novo_detalhe = c2.text_input("Detalhes da Despesa (ex: Aluguel)")
            # Podes adicionar mais categorias a esta lista depois!
            nova_categoria = c3.selectbox("Categoria", ["Aluguel Granatto", "Du", "PUC", "Nubank", "Gás", "Condomínio", "Limpeza", "Compras", "Outros"])
            
            c4, c5, c6 = st.columns(3)
            novo_custo = c4.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
            novo_tipo = c5.selectbox("Tipo de Movimento", ["Saída", "Entrada"])
            novo_pago = c6.checkbox("Esta conta já foi paga?")
            
            btn_salvar = st.form_submit_button("💾 Salvar na Nuvem")
            
            # Lógica para enviar para o Supabase
            if btn_salvar:
                if novo_detalhe == "":
                    st.error("⚠️ Por favor, preenche os Detalhes da Despesa.")
                elif novo_custo <= 0:
                    st.error("⚠️ O valor deve ser maior que zero.")
                else:
                    with conn.session as s:
                        # O comando SQL que insere os dados em segurança
                        comando_sql = text('''
                            INSERT INTO fluxo_caixa_pai (data_vencimento, detalhes_despesa, categoria, custo, pago, tipo_movimento)
                            VALUES (:data_v, :detalhes, :cat, :custo, :pago, :tipo)
                        ''')
                        s.execute(comando_sql, {
                            "data_v": nova_data,
                            "detalhes": novo_detalhe,
                            "cat": nova_categoria,
                            "custo": novo_custo,
                            "pago": novo_pago,
                            "tipo": novo_tipo
                        })
                        s.commit()
                    st.success("✅ Gasto guardado com sucesso!")
                    st.cache_data.clear() # Força o app a ler a nuvem novamente
                    st.rerun() # Atualiza o ecrã na hora

    # --- VISUALIZAÇÃO DOS DADOS ---
    df_pai = carregar_caixa_pai()
    
    if not df_pai.empty:
        # Miniaturas de Resumo
        total_saidas = df_pai[df_pai['tipo_movimento'] == 'Saída']['custo'].sum()
        pendentes = df_pai[(df_pai['pago'] == False) & (df_pai['tipo_movimento'] == 'Saída')]['custo'].sum()
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("💸 Total de Saídas (Histórico)", f"R$ {total_saidas:,.2f}")
        col_m2.metric("🚨 Total Pendente (Falta Pagar)", f"R$ {pendentes:,.2f}")
        
        # Tabela Bonita
        st.dataframe(
            df_pai[['data_vencimento', 'detalhes_despesa', 'categoria', 'custo', 'tipo_movimento', 'pago']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma conta encontrada. Adiciona a primeira no botão acima!")

# ==========================================
# ABA 2: INVESTIMENTOS
# ==========================================
with tab_inv:
    st.header("O meu Património")
    
    try:
        df_inv = carregar_investimentos()
        if not df_inv.empty:
            # Lógica Automática de Preço Médio!
            portfolio = {}
            for _, row in df_inv.iterrows():
                ticker = row['ticker']
                tipo = row['tipo']
                qtd = float(row['quantidade'])
                preco = float(row['preco'])
                
                if ticker not in portfolio:
                    portfolio[ticker] = {'qtd': 0.0, 'custo_total': 0.0, 'pm': 0.0}
                    
                if tipo == 'Compra':
                    portfolio[ticker]['custo_total'] += (qtd * preco)
                    portfolio[ticker]['qtd'] += qtd
                    if portfolio[ticker]['qtd'] > 0:
                        portfolio[ticker]['pm'] = portfolio[ticker]['custo_total'] / portfolio[ticker]['qtd']
                elif tipo == 'Venda':
                    if portfolio[ticker]['qtd'] > 0:
                        custo_proporcional = qtd * portfolio[ticker]['pm']
                        portfolio[ticker]['qtd'] -= qtd
                        portfolio[ticker]['custo_total'] -= custo_proporcional
                        
            # Criar tabela resumo
            resumo = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
            resumo.columns = ['Ticker', 'Qtd Atual', 'Custo Total', 'Preço Médio']
            resumo = resumo[resumo['Qtd Atual'] > 0.000001] # Filtra o que já foi todo vendido
            
            st.subheader("📊 Resumo da Carteira (Preço Médio)")
            st.dataframe(resumo, use_container_width=True, hide_index=True)
            
            st.subheader("📝 Histórico de Transações")
            st.dataframe(df_inv[['data', 'tipo', 'ticker', 'quantidade', 'preco', 'valor']], use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não importaste o ficheiro de investimentos para a nuvem.")
            
    except Exception as e:
        st.error(f"Erro a ler investimentos: {e}")

# ==========================================
# ABA 3: CARTÕES
# ==========================================
with tab_cartoes:
    st.header("Controlo de Faturas de Cartão")
    st.info("Estrutura criada na base de dados! No próximo passo vamos importar as tuas faturas para aqui para separarmos os gastos do teu pai dos teus.")

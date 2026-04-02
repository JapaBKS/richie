import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Richie Finance OS", layout="wide", page_icon="🚀")
st.title("🚀 Richie Finance OS")

# Botão para limpar o cache manualmente
if st.button("🔄 Atualizar / Sincronizar Dados"):
    st.cache_data.clear()
    st.rerun()

# 2. CONEXÃO COM O BANCO DE DADOS (SUPABASE)
conn = st.connection("supabase", type="sql")

# 3. FUNÇÕES PARA LER DADOS
@st.cache_data(ttl=10)
def carregar_dados_pai():
    df = conn.query("SELECT * FROM fluxo_caixa_pai ORDER BY data_vencimento DESC;")
    if not df.empty:
        df['data_vencimento'] = pd.to_datetime(df['data_vencimento'])
        # Criar coluna auxiliar de Mês/Ano para filtros
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

# 5. CRIAÇÃO DAS ABAS
tab_pai, tab_inv, tab_cartoes = st.tabs(["🏦 Contas do Pai", "📈 Meus Investimentos", "💳 Despesas Cartão"])

# ==========================================
# ABA 1: CONTAS DO PAI
# ==========================================
with tab_pai:
    if not df_pai_geral.empty:
        # --- FILTROS NA SIDEBAR (APENAS PARA ESTA ABA) ---
        lista_meses = sorted(df_pai_geral['mes_ano'].unique(), key=lambda x: datetime.strptime(x, '%m/%Y'), reverse=True)
        mes_selecionado = st.sidebar.selectbox("Selecione o Mês de Análise", lista_meses)

        # --- LÓGICA DE MÉTRICAS (Mês Atual vs Anterior) ---
        df_mes_atual = df_pai_geral[df_pai_geral['mes_ano'] == mes_selecionado]
        
        entradas_atuais = df_mes_atual[df_mes_atual['tipo_movimento'] == 'Entrada']['custo'].sum()
        saidas_atuais = df_mes_atual[df_mes_atual['tipo_movimento'] == 'Saída']['custo'].sum()
        disponivel_mes = entradas_atuais - saidas_atuais

        # Cálculo do Delta (Comparação com mês anterior na lista)
        delta_saidas = 0
        try:
            idx_atual = lista_meses.index(mes_selecionado)
            if idx_atual < len(lista_meses) - 1:
                mes_anterior = lista_meses[idx_atual + 1]
                saidas_anteriores = df_pai_geral[(df_pai_geral['mes_ano'] == mes_anterior) & (df_pai_geral['tipo_movimento'] == 'Saída')]['custo'].sum()
                delta_saidas = saidas_atuais - saidas_anteriores
        except:
            pass

        # --- EXIBIÇÃO DE MÉTRICAS ---
        st.subheader(f"Resumo de {mes_selecionado}")
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Disponível no Mês", f"R$ {disponivel_mes:,.2f}", help="Soma de Entradas - Saídas (mesmo as não pagas)")
        m2.metric("💸 Total Saídas", f"R$ {saidas_atuais:,.2f}", f"{delta_saidas:,.2f} vs mês ant.", delta_color="inverse")
        
        saldo_acumulado = df_pai_geral[df_pai_geral['tipo_movimento'] == 'Entrada']['custo'].sum() - df_pai_geral[df_pai_geral['tipo_movimento'] == 'Saída']['custo'].sum()
        m3.metric("🏦 Saldo Geral (Histórico)", f"R$ {saldo_acumulado:,.2f}")

        # --- GRÁFICO DE CATEGORIAS ---
        st.divider()
        col_graf, col_form = st.columns([2, 1])
        
        with col_graf:
            st.write("### Gastos por Categoria")
            gastos_cat = df_mes_atual[df_mes_atual['tipo_movimento'] == 'Saída'].groupby('categoria')['custo'].sum().sort_values(ascending=True)
            if not gastos_cat.empty:
                st.bar_chart(gastos_cat, horizontal=True)
            else:
                st.info("Sem saídas registradas neste mês.")

        with col_form:
            # --- FORMULÁRIO PARA ADICIONAR NOVA CONTA ---
            st.write("### Adicionar Conta")
            with st.form("form_novo_gasto_pai", clear_on_submit=True):
                nova_data = st.date_input("Data")
                novo_detalhe = st.text_input("Detalhe (ex: Aluguel)")
                nova_cat = st.selectbox("Categoria", ["Aluguel Granatto", "Du", "PUC", "Nubank", "Gás", "Condomínio", "Limpeza", "Compras", "PIX", "Outros"])
                novo_valor = st.number_input("Valor", min_value=0.0, step=0.01)
                novo_tipo = st.selectbox("Tipo", ["Saída", "Entrada"])
                novo_pago = st.checkbox("Pago?")
                
                if st.form_submit_button("💾 Salvar na Nuvem"):
                    with conn.session as s:
                        s.execute(text('''
                            INSERT INTO fluxo_caixa_pai (data_vencimento, detalhes_despesa, categoria, custo, pago, tipo_movimento)
                            VALUES (:dv, :dd, :ca, :cu, :pa, :ti)
                        '''), {"dv": nova_data, "dd": novo_detalhe, "ca": nova_cat, "cu": novo_valor, "pa": novo_pago, "ti": novo_tipo})
                        s.commit()
                    st.success("Salvo!")
                    st.cache_data.clear()
                    st.rerun()

        # --- TABELA INTERATIVA (EDIÇÃO) ---
        st.divider()
        st.write(f"### 📝 Editar Lançamentos de {mes_selecionado}")
        st.caption("Dê um duplo clique na célula para alterar. Clique fora da tabela e depois no botão abaixo para salvar.")
        
        df_editavel = df_mes_atual[['id', 'data_vencimento', 'detalhes_despesa', 'categoria', 'custo', 'tipo_movimento', 'pago']].copy()
        
        # O data_editor permite alterar os dados como se fosse Excel
        dados_editados = st.data_editor(
            df_editavel,
            hide_index=True,
            use_container_width=True,
            disabled=["id"],
            column_config={
                "pago": st.column_config.CheckboxColumn("Pago?"),
                "custo": st.column_config.NumberColumn("Valor (R$)", format="%.2f"),
                "data_vencimento": st.column_config.DateColumn("Data")
            }
        )

        if st.button("💾 Confirmar Alterações na Nuvem"):
            with conn.session as s:
                for _, row in dados_editados.iterrows():
                    s.execute(text('''
                        UPDATE fluxo_caixa_pai 
                        SET detalhes_despesa=:d, categoria=:c, custo=:v, pago=:p, data_vencimento=:dt
                        WHERE id=:i
                    '''), {"d": row['detalhes_despesa'], "c": row['categoria'], "v": row['custo'], "p": row['pago'], "dt": row['data_vencimento'], "i": row['id']})
                s.commit()
            st.success("Banco de Dados Atualizado!")
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("Nenhum dado encontrado no Fluxo de Caixa.")

# ==========================================
# ABA 2: INVESTIMENTOS
# ==========================================
with tab_inv:
    st.header("📈 Meu Patrimônio")
    if not df_inv.empty:
        # Lógica de Preço Médio
        portfolio = {}
        for _, row in df_inv.iterrows():
            ticker, tipo, qtd, preco = row['ticker'], row['tipo'], float(row['quantidade']), float(row['preco'])
            if ticker not in portfolio: portfolio[ticker] = {'qtd': 0.0, 'custo_total': 0.0, 'pm': 0.0}
            
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

        resumo = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
        resumo.columns = ['Ticker', 'Qtd Atual', 'Custo Total', 'Preço Médio']
        resumo = resumo[resumo['Qtd Atual'] > 0.000001]
        
        st.subheader("📊 Resumo da Carteira")
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        
        with st.expander("📄 Ver Histórico Completo"):
            st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.info("Importe seus investimentos para visualizar o preço médio.")

# ==========================================
# ABA 3: CARTÕES
# ==========================================
with tab_cartoes:
    st.header("💳 Controle de Cartões")
    st.info("Área pronta para receber a lógica de faturas no próximo passo.")

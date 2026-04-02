import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Richie Finance OS", layout="wide", page_icon="🚀")
st.title("🚀 Richie Finance OS")

# Botão de Sincronização
if st.button("🔄 Atualizar / Sincronizar Dados"):
    st.cache_data.clear()
    st.rerun()

# 2. CONEXÃO COM O BANCO DE DADOS (SUPABASE)
conn = st.connection("supabase", type="sql")

# 3. FUNÇÕES PARA LER DADOS
@st.cache_data(ttl=10)
def carregar_dados_pai():
    # Buscamos tudo ordenado por data para o cálculo do saldo acumulado funcionar
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

# 5. CRIAÇÃO DAS ABAS
tab_pai, tab_inv, tab_cartoes = st.tabs(["🏦 Contas do Pai", "📈 Meus Investimentos", "💳 Cartões"])

# ==========================================
# ABA 1: CONTAS DO PAI (SISTEMA DE SALDO ACUMULADO)
# ==========================================
with tab_pai:
    if not df_pai_geral.empty:
        # --- LÓGICA DE FILTROS ---
        # Lista de meses cronológica para os cálculos
        lista_meses_cron = sorted(df_pai_geral['mes_ano'].unique(), 
                                 key=lambda x: datetime.strptime(x, '%m/%Y'))
        
        # Seletor na barra lateral (mostra o mais recente primeiro)
        mes_selecionado = st.sidebar.selectbox("Selecione o Mês para Análise", lista_meses_cron[::-1])

        # --- CÁLCULO DO SALDO ROLADO (O QUE VEM DO PASSADO) ---
        idx_atual = lista_meses_cron.index(mes_selecionado)
        meses_anteriores = lista_meses_cron[:idx_atual]
        
        df_passado = df_pai_geral[df_pai_geral['mes_ano'].isin(meses_anteriores)]
        saldo_anterior = df_passado[df_passado['tipo_movimento'] == 'Entrada']['custo'].sum() - \
                         df_passado[df_passado['tipo_movimento'] == 'Saída']['custo'].sum()

        # --- CÁLCULOS DO MÊS SELECIONADO ---
        df_mes = df_pai_geral[df_pai_geral['mes_ano'] == mes_selecionado]
        entradas_mes = df_mes[df_mes['tipo_movimento'] == 'Entrada']['custo'].sum()
        saidas_mes = df_mes[df_mes['tipo_movimento'] == 'Saída']['custo'].sum()
        
        # Disponível Final = Saldo que já tinha + Entradas novas - Gastos novos
        disponivel_final = saldo_anterior + entradas_mes - saidas_mes

        # --- DASHBOARD DE MÉTRICAS (4 COLUNAS) ---
        st.subheader(f"Resumo Financeiro - {mes_selecionado}")
        m1, m2, m3, m4 = st.columns(4)
        
        m1.metric("⬅️ Saldo Anterior", f"R$ {saldo_anterior:,.2f}", help="O que sobrou acumulado de todos os meses passados.")
        m2.metric("➕ Entradas do Mês", f"R$ {entradas_mes:,.2f}", help="Soma de todos os ganhos/depósitos deste mês.")
        
        # Cálculo de delta de gastos vs mês anterior
        delta_saidas = 0
        if idx_atual > 0:
            mes_ant_nome = lista_meses_cron[idx_atual - 1]
            saidas_ant = df_pai_geral[(df_pai_geral['mes_ano'] == mes_ant_nome) & (df_pai_geral['tipo_movimento'] == 'Saída')]['custo'].sum()
            delta_saidas = saidas_mes - saidas_ant

        m3.metric("💸 Saídas do Mês", f"R$ {saidas_mes:,.2f}", f"{delta_saidas:,.2f} vs mês ant.", delta_color="inverse")
        m4.metric("💰 Disponível Final", f"R$ {disponivel_final:,.2f}", help="Valor total disponível após todas as entradas e saídas.")

        # --- GRÁFICO E FORMULÁRIO ---
        st.divider()
        c_graf, c_form = st.columns([2, 1])
        
        with c_graf:
            st.write("### Onde o dinheiro foi gasto?")
            gastos_cat = df_mes[df_mes['tipo_movimento'] == 'Saída'].groupby('categoria')['custo'].sum().sort_values()
            if not gastos_cat.empty:
                st.bar_chart(gastos_cat, horizontal=True)
            else:
                st.info("Nenhuma saída registrada neste mês.")

        with c_form:
            st.write("### Adicionar Novo Lançamento")
            with st.form("form_pai_novo", clear_on_submit=True):
                v_data = st.date_input("Data de Vencimento")
                v_det = st.text_input("Detalhe (ex: Aluguel)")
                v_cat = st.selectbox("Categoria", ["Aluguel Granatto", "Du", "PUC", "Nubank", "Gás", "Condomínio", "Limpeza", "Compras", "PIX", "Outros"])
                v_val = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                v_tipo = st.selectbox("Tipo de Movimento", ["Saída", "Entrada"])
                v_pago = st.checkbox("Pago?", value=True)
                
                if st.form_submit_button("💾 Salvar no Banco"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO fluxo_caixa_pai (data_vencimento, detalhes_despesa, categoria, custo, pago, tipo_movimento) VALUES (:d, :det, :c, :v, :p, :t)"),
                                  {"d": v_data, "det": v_det, "c": v_cat, "v": v_val, "p": v_pago, "t": v_tipo})
                        s.commit()
                    st.success("Salvo com sucesso!")
                    st.cache_data.clear()
                    st.rerun()

        # --- EDITOR DE DADOS (PARA MODIFICAR OU APAGAR) ---
        st.divider()
        st.write(f"### 📝 Tabela Detalhada de {mes_selecionado}")
        st.caption("Dica: Para APAGAR, selecione a linha clicando na lateral esquerda dela e aperte 'Delete' no seu teclado. Depois clique em Salvar.")
        
        df_edit = df_mes[['id', 'data_vencimento', 'detalhes_despesa', 'categoria', 'custo', 'tipo_movimento', 'pago']].copy()
        
        edited_df = st.data_editor(
            df_edit,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            disabled=["id"],
            column_config={
                "pago": st.column_config.CheckboxColumn("Pago?"),
                "custo": st.column_config.NumberColumn("Valor (R$)", format="%.2f"),
                "data_vencimento": st.column_config.DateColumn("Vencimento"),
                "tipo_movimento": st.column_config.SelectboxColumn("Tipo", options=["Saída", "Entrada"])
            }
        )

        if st.button("💾 Confirmar Alterações e Exclusões"):
            ids_atuais = set(edited_df['id'].dropna())
            ids_originais = set(df_edit['id'])
            ids_para_deletar = ids_originais - ids_atuais

            with conn.session as s:
                # 1. Remove o que foi deletado na interface
                for id_del in ids_para_deletar:
                    s.execute(text("DELETE FROM fluxo_caixa_pai WHERE id = :i"), {"i": id_del})
                
                # 2. Atualiza o que foi alterado
                for _, row in edited_df.iterrows():
                    if pd.notna(row['id']):
                        s.execute(text("UPDATE fluxo_caixa_pai SET detalhes_despesa=:d, categoria=:c, custo=:v, pago=:p, data_vencimento=:dt, tipo_movimento=:t WHERE id=:i"),
                                  {"d": row['detalhes_despesa'], "c": row['categoria'], "v": row['custo'], "p": row['pago'], "dt": row['data_vencimento'], "t": row['tipo_movimento'], "i": row['id']})
                s.commit()
            st.success("Tudo atualizado na nuvem!")
            st.cache_data.clear()
            st.rerun()

# ==========================================
# ABA 2: INVESTIMENTOS
# ==========================================
with tab_inv:
    st.header("📈 Meu Patrimônio")
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
        resumo.columns = ['Ticker', 'Qtd Atual', 'Investimento Total', 'Preço Médio']
        resumo = resumo[resumo['Qtd Atual'] > 0.000001]
        
        st.subheader("📊 Resumo da Carteira")
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        
        with st.expander("📄 Ver Histórico de Transações"):
            st.dataframe(df_inv, use_container_width=True, hide_index=True)

# ==========================================
# ABA 3: CARTÕES
# ==========================================
with tab_cartoes:
    st.header("💳 Controle de Cartões")
    st.info("Área pronta para receber a lógica de faturas no futuro.")

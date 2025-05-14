import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide") # Moved to the top

# Load data
@st.cache_data
def load_data():
    data = pd.read_csv("csv/jogos_resumo_clean.csv") # Removed parse_dates from here
    
    # Explicitly convert 'data_jogo' to datetime, coercing errors to NaT
    data['data_jogo'] = pd.to_datetime(data['data_jogo'], errors='coerce')

    # Ensure relevant columns are numeric, coercing errors to NaN
    numeric_cols = ['receita_bruta_total', 'publico_total', 'resultado_liquido']
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    # Calculate additional metrics
    data['ticket_medio'] = data['receita_bruta_total'] / data['publico_total']
    data['margem_liquida'] = data['resultado_liquido'] / data['receita_bruta_total']
    
    # Replace inf values with NaN, then fill NaN with 0 (or an appropriate value)
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    data['ticket_medio'].fillna(0, inplace=True)
    data['margem_liquida'].fillna(0, inplace=True)
    
    # Create Portuguese day of the week
    dias_semana_map = {
        'Monday': 'Segunda-feira',
        'Tuesday': 'Terça-feira',
        'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira',
        'Friday': 'Sexta-feira',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    data['dia_semana_en'] = data['data_jogo'].dt.day_name()
    data['dia_semana_pt'] = data['dia_semana_en'].map(dias_semana_map)
    
    # Define categorical order for Portuguese days of the week
    dias_ordenados = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    data['dia_semana_pt'] = pd.Categorical(data['dia_semana_pt'], categories=dias_ordenados, ordered=True)
    
    return data

data = load_data()

st.title("CBF Robot - Análise de Jogos de Futebol")

# --- FILTERS ---
st.sidebar.header("Filtros")
# Filter for year
anos_disponiveis = sorted(data['data_jogo'].dt.year.dropna().unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano", anos_disponiveis, index=0)

# Filter data by selected year first
data_filtrada_ano = data[data['data_jogo'].dt.year == ano_selecionado].copy()


competicao = st.sidebar.multiselect(
    "Competição",
    options=data_filtrada_ano["competicao"].dropna().unique(),
    default=data_filtrada_ano["competicao"].dropna().unique()
)

times_mandantes_options = sorted(data_filtrada_ano["time_mandante"].dropna().unique())
time_mandante_selecionado = st.sidebar.multiselect(
    "Time Mandante",
    options=times_mandantes_options,
    default=times_mandantes_options
)

times_visitantes_options = sorted(data_filtrada_ano["time_visitante"].dropna().unique())
time_visitante_selecionado = st.sidebar.multiselect(
    "Time Visitante",
    options=times_visitantes_options,
    default=times_visitantes_options
)

# Apply filters
data_dashboard = data_filtrada_ano[
    data_filtrada_ano["competicao"].isin(competicao) &
    data_filtrada_ano["time_mandante"].isin(time_mandante_selecionado) &
    data_filtrada_ano["time_visitante"].isin(time_visitante_selecionado)
].copy() # Use .copy() to avoid SettingWithCopyWarning

if data_dashboard.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    # --- GENERAL STATS ---
    st.header("Estatísticas Gerais do Período Filtrado")
    total_jogos = data_dashboard.shape[0]
    total_publico = data_dashboard['publico_total'].sum()
    total_receita = data_dashboard['receita_bruta_total'].sum()
    # Calculate overall ticket_medio and margem_liquida carefully to avoid division by zero
    overall_ticket_medio = total_receita / total_publico if total_publico > 0 else 0
    overall_margem_liquida = data_dashboard['resultado_liquido'].sum() / total_receita if total_receita > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total de Jogos", f"{total_jogos:,}")
    col2.metric("Público Total", f"{total_publico:,.0f}")
    col3.metric("Receita Bruta Total", f"R$ {total_receita:,.2f}")
    col4.metric("Ticket Médio Geral", f"R$ {overall_ticket_medio:,.2f}")
    col5.metric("Margem Líquida Média", f"{overall_margem_liquida:.2%}")

    st.markdown("---")

    # --- ATTENDANCE ANALYSIS ---
    st.header("Análise de Público")
    col1_publico, col2_publico = st.columns(2)

    with col1_publico:
        st.subheader("Público Médio por Dia da Semana")
        # Group by Portuguese day name, calculate mean, then sort by the categorical order (day of week)
        # or by value. Let's sort by value (mean attendance) for now.
        dia_semana_publico = data_dashboard.groupby('dia_semana_pt', observed=False)['publico_total'].mean().sort_values(ascending=False)
        st.bar_chart(dia_semana_publico)
        st.caption("Mostra o público médio para cada dia da semana em que ocorreram jogos.")

    with col2_publico:
        st.subheader("Distribuição do Público Total")
        # Drop NaN values before creating histogram to avoid errors
        publico_total_valid = data_dashboard['publico_total'].dropna()
        if not publico_total_valid.empty:
            st.bar_chart(np.histogram(publico_total_valid, bins=20)[0])
            st.caption("Histograma mostrando a frequência de diferentes faixas de público total.")
        else:
            st.info("Não há dados de público suficientes para gerar o histograma.")


    col3_publico, col4_publico = st.columns(2)
    with col3_publico:
        st.subheader("Público Médio por Time Mandante")
        publico_medio_mandante = data_dashboard.groupby('time_mandante')['publico_total'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(publico_medio_mandante)
        st.caption("Top 20 times com maior público médio quando mandantes.")

    with col4_publico:
        st.subheader("Público Médio por Time Visitante")
        publico_medio_visitante = data_dashboard.groupby('time_visitante')['publico_total'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(publico_medio_visitante)
        st.caption("Top 20 times com maior público médio quando visitantes.")
    
    st.markdown("---")

    # --- FINANCIAL ANALYSIS ---
    st.header("Análise Financeira")
    col1_fin, col2_fin = st.columns(2)

    with col1_fin:
        st.subheader("Ticket Médio por Clube (Mandante)")
        ticket_medio_clube = data_dashboard.groupby('time_mandante')['ticket_medio'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(ticket_medio_clube)
        st.caption("Top 20 times com maior ticket médio quando mandantes.")

    with col2_fin:
        st.subheader("Margem Líquida Média por Clube (Mandante)")
        margem_liquida_clube = data_dashboard.groupby('time_mandante')['margem_liquida'].mean().sort_values(ascending=False).head(20) # Top 20
        st.bar_chart(margem_liquida_clube)
        st.caption("Top 20 times com maior margem líquida média quando mandantes. Valores podem ser negativos.")

    st.subheader("Relação Público Total vs. Ticket Médio")
    # Ensure no NaN values in columns for scatter plot
    scatter_data = data_dashboard[['publico_total', 'ticket_medio']].dropna()
    if not scatter_data.empty:
        st.scatter_chart(scatter_data, x='publico_total', y='ticket_medio', size='publico_total')
        st.caption("Cada ponto representa um jogo. O tamanho do ponto pode indicar o público (opcional).")
    else:
        st.info("Não há dados suficientes para o gráfico de dispersão.")

    st.markdown("---")
    
    # --- TOP 5 GAMES ---
    st.header("Top 5 Jogos")
    col1_top, col2_top = st.columns(2)
    col3_top, col4_top = st.columns(2)

    with col1_top:
        st.subheader("Por Maior Público Total")
        top_publico = data_dashboard.nlargest(5, 'publico_total')[['data_jogo', 'time_mandante', 'time_visitante', 'publico_total', 'competicao']]
        st.dataframe(top_publico.style.format({"publico_total": "{:,.0f}"}))
    
    with col2_top:
        st.subheader("Por Maior Receita Bruta")
        top_receita = data_dashboard.nlargest(5, 'receita_bruta_total')[['data_jogo', 'time_mandante', 'time_visitante', 'receita_bruta_total', 'competicao']]
        st.dataframe(top_receita.style.format({"receita_bruta_total": "R$ {:,.2f}"}))

    with col3_top:
        st.subheader("Por Maior Ticket Médio")
        # Filter out games with zero public to avoid misleading high ticket_medio from zero division
        top_ticket = data_dashboard[data_dashboard['publico_total'] > 0].nlargest(5, 'ticket_medio')[['data_jogo', 'time_mandante', 'time_visitante', 'ticket_medio', 'publico_total', 'competicao']]
        st.dataframe(top_ticket.style.format({"ticket_medio": "R$ {:,.2f}", "publico_total": "{:,.0f}"}))

    with col4_top:
        st.subheader("Por Maior Margem Líquida")
        # Filter out games with zero revenue to avoid misleading high margem_liquida from zero division
        top_margem = data_dashboard[data_dashboard['receita_bruta_total'] != 0].nlargest(5, 'margem_liquida')[['data_jogo', 'time_mandante', 'time_visitante', 'margem_liquida', 'receita_bruta_total', 'competicao']]
        st.dataframe(top_margem.style.format({"margem_liquida": "{:.2%}", "receita_bruta_total": "R$ {:,.2f}"}))

    st.markdown("---")

    # --- TIME SERIES ANALYSIS ---
    st.header("Análise Temporal")
    st.subheader("Evolução do Público Total ao Longo do Tempo (Soma Mensal)")
    # Resample requires a DatetimeIndex
    # Drop rows where 'data_jogo' is NaT before setting as index
    publico_tempo_data = data_dashboard.dropna(subset=['data_jogo'])
    if not publico_tempo_data.empty:
        publico_tempo = publico_tempo_data.set_index('data_jogo')['publico_total'].resample('M').sum()
        st.line_chart(publico_tempo)
        st.caption("Soma do público total de todos os jogos, agrupado por mês.")
    else:
        st.info("Não há dados de data suficientes para a análise temporal.")


    st.markdown("---")
    # Display raw data
    st.header("Dados Brutos Filtrados")
    st.write(f"Exibindo {data_dashboard.shape[0]} jogos.")
    st.dataframe(data_dashboard.drop(columns=['dia_semana_en']).style.format({ # Hiding the English day name column
        'data_jogo': '{:%d/%m/%Y}',
        'publico_pagante': '{:,.0f}',
        'publico_nao_pagante': '{:,.0f}',
        'publico_total': '{:,.0f}',
        'receita_bruta_total': 'R$ {:,.2f}',
        'despesa_total': 'R$ {:,.2f}',
        'resultado_liquido': 'R$ {:,.2f}',
        'ticket_medio': 'R$ {:,.2f}',
        'margem_liquida': '{:.2%}'
    }))

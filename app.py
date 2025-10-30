import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Vermicompostagem - Ribeirão Preto",
    page_icon="♻️",
    layout="wide"
)

st.title("♻️ Vermicompostagem nas Escolas de Ribeirão Preto")
st.markdown("**Monitoramento do sistema de compostagem com minhocas**")

# URL REAL DO SEU EXCEL NO GITHUB
URL_EXCEL = "https://github.com/loopvinyl/vermicompostagem-ribeirao-preto/raw/main/dados_vermicompostagem.xlsx"

@st.cache_data
def carregar_dados(url):
    """Carrega os dados do Excel do GitHub"""
    try:
        # Ler as abas
        df_escolas = pd.read_excel(url, sheet_name='escolas')
        df_caixas = pd.read_excel(url, sheet_name='caixas')
        
        st.success(f"✅ Dados carregados: {len(df_escolas)} escolas e {len(df_caixas)} caixas")
        
        return df_escolas, df_caixas
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None, None

# Função segura para calcular dias
def calcular_dias_desde_encheu(data_encheu):
    """Calcula dias desde que encheu de forma segura"""
    if pd.isna(data_encheu):
        return None
    try:
        if isinstance(data_encheu, str):
            data_encheu = pd.to_datetime(data_encheu, errors='coerce')
        if pd.isna(data_encheu):
            return None
        hoje = datetime.now().date()
        data_encheu_date = data_encheu.date()
        return (hoje - data_encheu_date).days
    except:
        return None

# Carregar dados
df_escolas, df_caixas = carregar_dados(URL_EXCEL)

if df_escolas is not None and df_caixas is not None:
    
    # ===== MÉTRICAS PRINCIPAIS =====
    st.subheader("📊 Resumo Geral")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_escolas = len(df_escolas)
        st.metric("🏫 Total de Escolas", total_escolas)
    
    with col2:
        total_caixas = len(df_caixas)
        st.metric("📦 Total de Caixas", total_caixas)
    
    with col3:
        if 'status_caixa' in df_caixas.columns:
            caixas_ativas = df_caixas[df_caixas['status_caixa'] == 'Ativa'].shape[0]
            st.metric("✅ Caixas Ativas", caixas_ativas)
        else:
            st.metric("✅ Caixas", "N/A")
    
    with col4:
        if 'status_caixa' in df_caixas.columns:
            caixas_cheias = df_caixas[df_caixas['status_caixa'] == 'Cheia'].shape[0]
            st.metric("🕒 Caixas Cheias", caixas_cheias)
        else:
            st.metric("🕒 Status", "N/A")

    # ===== CALCULAR ALERTAS DE FORMA SEGURA =====
    if 'data_encheu' in df_caixas.columns and 'status_caixa' in df_caixas.columns:
        # Calcular dias para cada caixa cheia
        alertas_urgentes = []
        alertas_proximos = []
        
        for _, caixa in df_caixas.iterrows():
            if caixa['status_caixa'] == 'Cheia' and pd.notna(caixa['data_encheu']):
                dias = calcular_dias_desde_encheu(caixa['data_encheu'])
                if dias is not None:
                    escola_nome = df_escolas[df_escolas['id_escola'] == caixa['id_escola']]['nome_escola'].iloc[0]
                    
                    if dias > 50:
                        alertas_urgentes.append({
                            'escola': escola_nome,
                            'caixa': caixa['numero_caixa'],
                            'dias': dias
                        })
                    elif dias >= 45:
                        alertas_proximos.append({
                            'escola': escola_nome,
                            'caixa': caixa['numero_caixa'],
                            'dias': dias
                        })
        
        # Mostrar alertas
        if alertas_urgentes:
            st.error("🚨 **ALERTAS URGENTES - Caixas com mais de 50 dias cheias:**")
            for alerta in alertas_urgentes:
                st.write(f"- **{alerta['escola']}** - Caixa {alerta['caixa']}: {alerta['dias']} dias cheia")
        
        if alertas_proximos and not alertas_urgentes:
            st.warning("⚠️ **Caixas próximas da colheita (45+ dias):**")
            for alerta in alertas_proximos:
                st.write(f"- **{alerta['escola']}** - Caixa {alerta['caixa']}: {alerta['dias']} dias")

    # ===== FILTROS =====
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por escola
    escolas_options = st.sidebar.multiselect(
        "Escolas:",
        options=df_escolas['nome_escola'].unique(),
        default=df_escolas['nome_escola'].unique()
    )
    
    # Aplicar filtros
    escolas_filtradas = df_escolas[df_escolas['nome_escola'].isin(escolas_options)]
    caixas_filtradas = df_caixas[df_caixas['id_escola'].isin(escolas_filtradas['id_escola'])]

    # ===== VISUALIZAÇÕES =====
    tab1, tab2, tab3 = st.tabs(["📈 Dashboard", "📦 Caixas", "🏫 Escolas"])

    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            if 'status_caixa' in df_caixas.columns:
                status_count = caixas_filtradas['status_caixa'].value_counts()
                fig1 = px.pie(
                    values=status_count.values, 
                    names=status_count.index,
                    title="Status das Caixas"
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Coluna 'status_caixa' não encontrada")
        
        with col2:
            # Gráfico de caixas por escola
            caixas_por_escola = caixas_filtradas.groupby('id_escola').size()
            if not caixas_por_escola.empty:
                # Pegar nomes das escolas
                caixas_por_escola.index = caixas_por_escola.index.map(
                    lambda x: df_escolas[df_escolas['id_escola'] == x]['nome_escola'].iloc[0]
                )
                fig2 = px.bar(
                    x=caixas_por_escola.index,
                    y=caixas_por_escola.values,
                    title="Caixas por Escola",
                    labels={'x': 'Escola', 'y': 'Número de Caixas'}
                )
                st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("📦 Todas as Caixas")
        # Juntar com nomes das escolas para display
        caixas_display = caixas_filtradas.merge(
            df_escolas[['id_escola', 'nome_escola']], 
            on='id_escola'
        )
        st.dataframe(caixas_display, use_container_width=True)

    with tab3:
        st.subheader("🏫 Informações das Escolas")
        st.dataframe(escolas_filtradas, use_container_width=True)

else:
    st.error("""
    ❌ **Não foi possível carregar os dados. Verifique:**
    
    1. ✅ O arquivo Excel existe no GitHub
    2. ✅ As abas se chamam 'escolas' e 'caixas'
    3. ✅ A URL está correta
    4. ✅ O arquivo não está corrompido
    """)

# ===== INFO NO SIDEBAR =====
st.sidebar.markdown("---")
st.sidebar.info("""
**📊 Fonte dos dados:**
[GitHub - Vermicompostagem Ribeirão Preto](https://github.com/loopvinyl/vermicompostagem-ribeirao-preto)

**🔄 Atualização:** Os dados são atualizados automaticamente quando o Excel no GitHub é modificado.
""")

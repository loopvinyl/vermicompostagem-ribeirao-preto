import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Vermicompostagem - Ribeirão Preto",
    page_icon="♻️",
    layout="wide"
)

st.title("♻️ Vermicompostagem nas Escolas de Ribeirão Preto")
st.markdown("**Monitoramento do sistema de compostagem com minhocas**")

# URL DO EXCEL NO GITHUB - ATUALIZE COM SUA URL!
URL_EXCEL = "https://github.com/loopvinyl/vermicompostagem-ribeirao-preto/blob/main/dados_vermicompostagem.xlsx"

@st.cache_data
def carregar_dados(url):
    """Carrega os dados do Excel do GitHub"""
    try:
        # Ler as abas
        df_escolas = pd.read_excel(url, sheet_name='escolas')
        df_caixas = pd.read_excel(url, sheet_name='caixas')
        
        # Tentar ler a aba de visitas (opcional)
        try:
            df_visitas = pd.read_excel(url, sheet_name='visitas')
        except:
            df_visitas = None
            
        # Converter colunas de data
        colunas_data_escolas = ['data_implantacao', 'ultima_visita']
        for col in colunas_data_escolas:
            if col in df_escolas.columns:
                df_escolas[col] = pd.to_datetime(df_escolas[col], errors='coerce')
                
        colunas_data_caixas = ['data_ativacao', 'data_encheu', 'data_prevista_colheita', 'data_colheita_real']
        for col in colunas_data_caixas:
            if col in df_caixas.columns:
                df_caixas[col] = pd.to_datetime(df_caixas[col], errors='coerce')
                
        return df_escolas, df_caixas, df_visitas
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None, None, None

# Carregar dados
df_escolas, df_caixas, df_visitas = carregar_dados(URL_EXCEL)

if df_escolas is not None and df_caixas is not None:
    
    # ===== CALCULAR ALERTAS AUTOMATICAMENTE =====
    hoje = datetime.now().date()
    
    # Caixas que estão cheias mas ainda não foram colhidas
    caixas_cheias_nao_colhidas = df_caixas[
        (df_caixas['status_caixa'] == 'Cheia') & 
        (df_caixas['data_colheita_real'].isna())
    ].copy()
    
    # Calcular dias desde que encheram
    caixas_cheias_nao_colhidas['dias_desde_encheu'] = (
        hoje - caixas_cheias_nao_colhidas['data_encheu'].dt.date
    ).dt.days
    
    # Alertas: caixas que encheram há mais de 45 dias (próximo dos 50)
    alertas_proximos = caixas_cheias_nao_colhidas[
        caixas_cheias_nao_colhidas['dias_desde_encheu'] >= 45
    ]
    
    # Urgentes: caixas que passaram de 50 dias
    alertas_urgentes = caixas_cheias_nao_colhidas[
        caixas_cheias_nao_colhidas['dias_desde_encheu'] > 50
    ]
    
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
        caixas_ativas = df_caixas[df_caixas['status_caixa'] == 'Ativa'].shape[0]
        st.metric("✅ Caixas Ativas", caixas_ativas)
    
    with col4:
        caixas_cheias = df_caixas[df_caixas['status_caixa'] == 'Cheia'].shape[0]
        st.metric("🕒 Caixas Cheias", caixas_cheias)

    # ===== ALERTAS =====
    if not alertas_urgentes.empty:
        st.error("🚨 **ALERTAS URGENTES - Caixas com mais de 50 dias cheias:**")
        for _, caixa in alertas_urgentes.iterrows():
            escola_nome = df_escolas[df_escolas['id_escola'] == caixa['id_escola']]['nome_escola'].iloc[0]
            st.write(f"- **{escola_nome}** - Caixa {caixa['numero_caixa']}: {caixa['dias_desde_encheu']} dias cheia")
    
    if not alertas_proximos.empty and alertas_urgentes.empty:
        st.warning("⚠️ **Caixas próximas da colheita (45+ dias):**")
        for _, caixa in alertas_proximos.iterrows():
            escola_nome = df_escolas[df_escolas['id_escola'] == caixa['id_escola']]['nome_escola'].iloc[0]
            st.write(f"- **{escola_nome}** - Caixa {caixa['numero_caixa']}: {caixa['dias_desde_encheu']} dias")

    # ===== FILTROS =====
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por escola
    escolas_options = st.sidebar.multiselect(
        "Escolas:",
        options=df_escolas['nome_escola'].unique(),
        default=df_escolas['nome_escola'].unique()
    )
    
    # Filtro por status da caixa
    status_caixa_options = st.sidebar.multiselect(
        "Status das Caixas:",
        options=df_caixas['status_caixa'].unique(),
        default=df_caixas['status_caixa'].unique()
    )

    # Aplicar filtros
    escolas_filtradas = df_escolas[df_escolas['nome_escola'].isin(escolas_options)]
    caixas_filtradas = df_caixas[
        (df_caixas['id_escola'].isin(escolas_filtradas['id_escola'])) &
        (df_caixas['status_caixa'].isin(status_caixa_options))
    ]

    # ===== ABAS DE VISUALIZAÇÃO =====
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Dashboard", "📦 Caixas", "🏫 Escolas", "🔔 Alertas"])

    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de status das caixas
            status_count = caixas_filtradas['status_caixa'].value_counts()
            fig1 = px.pie(
                values=status_count.values, 
                names=status_count.index,
                title="Status das Caixas"
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Gráfico de caixas por escola
            caixas_por_escola = caixas_filtradas.groupby('id_escola').size()
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
        st.dataframe(
            caixas_display[[
                'nome_escola', 'numero_caixa', 'status_caixa', 
                'data_ativacao', 'data_encheu', 'data_prevista_colheita'
            ]],
            use_container_width=True
        )

    with tab3:
        st.subheader("🏫 Informações das Escolas")
        st.dataframe(
            escolas_filtradas[[
                'id_escola', 'nome_escola', 'status', 
                'total_caixas', 'ultima_visita'
            ]],
            use_container_width=True
        )

    with tab4:
        st.subheader("🔔 Painel de Alertas")
        
        if not alertas_urgentes.empty:
            st.error("### 🚨 URGENTE - Colher Imediatamente")
            urgentes_display = alertas_urgentes.merge(
                df_escolas[['id_escola', 'nome_escola']], 
                on='id_escola'
            )
            st.dataframe(
                urgentes_display[[
                    'nome_escola', 'numero_caixa', 'data_encheu', 'dias_desde_encheu'
                ]],
                use_container_width=True
            )
        
        if not alertas_proximos.empty:
            st.warning("### ⚠️ Próximos da Colheita")
            proximos_display = alertas_proximos.merge(
                df_escolas[['id_escola', 'nome_escola']], 
                on='id_escola'
            )
            st.dataframe(
                proximos_display[[
                    'nome_escola', 'numero_caixa', 'data_encheu', 'dias_desde_encheu'
                ]],
                use_container_width=True
            )

else:
    # Mensagem de instruções iniciais
    st.info("""
    ## 📋 Para começar a usar:
    
    1. **Crie a planilha** com o nome: `dados_vermicompostagem.xlsx`
    2. **Estruture com as abas**: `escolas`, `caixas` e `visitas` (opcional)
    3. **Salve no GitHub** e cole a URL raw no código
    4. **Preencha com os dados** das escolas e caixas
    
    ### 📝 Estrutura das abas:
    - **Aba 'escolas'**: id_escola, nome_escola, data_implantacao, status, total_caixas
    - **Aba 'caixas'**: id_caixa, id_escola, numero_caixa, data_ativacao, status_caixa, data_encheu, data_prevista_colheita
    - **Aba 'visitas'**: opcional para histórico detalhado
    """)

# ===== DOWNLOAD DO MODELO =====
st.sidebar.markdown("---")
st.sidebar.subheader("📥 Modelo da Planilha")

def criar_modelo():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # ABA escolas
        df_modelo_escolas = pd.DataFrame(columns=[
            'id_escola', 'nome_escola', 'data_implantacao', 'status', 
            'total_caixas', 'ultima_visita', 'observacoes'
        ])
        df_modelo_escolas.to_excel(writer, sheet_name='escolas', index=False)
        
        # ABA caixas
        df_modelo_caixas = pd.DataFrame(columns=[
            'id_caixa', 'id_escola', 'numero_caixa', 'data_ativacao',
            'status_caixa', 'data_encheu', 'data_prevista_colheita',
            'data_colheita_real', 'humus_produzido_kg', 'observacoes_caixa'
        ])
        df_modelo_caixas.to_excel(writer, sheet_name='caixas', index=False)
        
        # ABA visitas
        df_modelo_visitas = pd.DataFrame(columns=[
            'id_visita', 'id_escola', 'data_visita', 'acao_realizada', 'observacoes'
        ])
        df_modelo_visitas.to_excel(writer, sheet_name='visitas', index=False)
    
    return output.getvalue()

modelo_excel = criar_modelo()
st.sidebar.download_button(
    label="⬇️ Baixar Modelo da Planilha",
    data=modelo_excel,
    file_name="modelo_vermicompostagem_ribeirao.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ===== ATUALIZAR URL =====
st.sidebar.markdown("---")
st.sidebar.info("""
**🔧 Configuração:**
Atualize a URL_EXCEL no código com o endereço do seu arquivo no GitHub
""")

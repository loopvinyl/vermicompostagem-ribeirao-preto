import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings("ignore")

# Configuração da página
st.set_page_config(
    page_title="Compostagem Escolar - Ribeirão Preto",
    page_icon="♻️",
    layout="wide"
)

# Título principal
st.title("♻️ Sistema de Compostagem com Minhocas - Escolas")
st.markdown("""
**Simulador de Créditos de Carbono para Gestão de Resíduos Orgânicos Escolares**
*Cálculo baseado no processamento de resíduos de restaurantes escolares: frutas, verduras e borra de café*
""")

# =============================================================================
# FUNÇÃO DE FORMATAÇÃO BRASILEIRA
# =============================================================================

def formatar_brasil(numero, casas_decimais=2, moeda=False, simbolo_moeda=""):
    """Formata números no padrão brasileiro"""
    try:
        if numero is None:
            return "0,00"
        
        numero_arredondado = round(float(numero), casas_decimais)
        formatado = f"{numero_arredondado:,.{casas_decimais}f}"
        
        if casas_decimais > 0:
            formatado = formatado.replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            formatado = formatado.replace(",", ".")
        
        if moeda and simbolo_moeda:
            return f"{simbolo_moeda} {formatado}"
        else:
            return formatado
            
    except (ValueError, TypeError):
        return "0,00"

# =============================================================================
# COTAÇÃO DO CARBONO (SIMPLIFICADA)
# =============================================================================

def obter_cotacao_carbono():
    """Obtém a cotação do carbono - versão simplificada"""
    return 85.50, "€", "Carbon Emissions Future", True, "Referência"

def obter_cotacao_euro_real():
    """Obtém a cotação do Euro - versão simplificada"""
    return 5.50, "R$", True, "Referência"

def calcular_valor_creditos(emissoes_evitadas_tco2eq, preco_carbono_por_tonelada, moeda, taxa_cambio=1):
    """Calcula o valor financeiro das emissões evitadas"""
    return emissoes_evitadas_tco2eq * preco_carbono_por_tonelada * taxa_cambio

# =============================================================================
# CONFIGURAÇÃO DO SISTEMA
# =============================================================================

# Sidebar principal
with st.sidebar:
    st.header("⚙️ Configuração do Sistema")
    
    # Sistema de reatores
    st.subheader("📦 Reatores de Compostagem")
    
    capacidade_reator = st.slider(
        "Capacidade de cada reator (litros)",
        min_value=20,
        max_value=100,
        value=30,
        step=5,
        help="Caixas padrão de 30L para coleta de biofertilizante"
    )
    
    num_reatores = st.slider(
        "Número de reatores no sistema",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="Cada reator processa resíduos por 50 dias"
    )
    
    ciclos_ano = st.slider(
        "Ciclos completos por ano",
        min_value=1,
        max_value=12,
        value=6,
        step=1,
        help="Número de vezes que os reatores são processados por ano"
    )
    
    # Cálculos automáticos
    densidade_residuo = 0.5  # kg/L - fixo para resíduos escolares
    capacidade_ciclo_kg = capacidade_reator * densidade_residuo * num_reatores
    residuo_anual_kg = capacidade_ciclo_kg * ciclos_ano
    residuo_anual_ton = residuo_anual_kg / 1000
    residuos_kg_dia = residuo_anual_kg / 365
    
    st.info(f"""
    **📊 Capacidade do Sistema:**
    - **Por ciclo:** {formatar_brasil(capacidade_ciclo_kg, 1)} kg
    - **Por ano:** {formatar_brasil(residuo_anual_ton, 1)} toneladas
    - **Resíduos/dia:** {formatar_brasil(residuos_kg_dia, 1)} kg
    """)
    
    # Período de simulação
    st.subheader("📅 Período de Projeto")
    anos_simulacao = st.selectbox(
        "Duração do projeto",
        options=[4, 8, 12, 16, 20],
        index=2,  # Padrão 12 anos
        help="Período típico para projetos escolares"
    )
    
    if st.button("🚀 Calcular Créditos de Carbono", type="primary", use_container_width=True):
        st.session_state.run_simulation = True

# =============================================================================
# INFORMAÇÕES DO SISTEMA
# =============================================================================

st.header("🏫 Sistema de Compostagem Escolar")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader(f"📦 Reatores de {capacidade_reator}L")
    st.markdown(f"""
    - **Material:** Plástico resistente
    - **Função:** Processar resíduos + coletar biofertilizante
    - **Capacidade:** {formatar_brasil(capacidade_ciclo_kg/num_reatores, 1)} kg/reator
    - **Componentes:**
      • Minhocas Californianas
      • Substrato inicial  
      • Resíduos orgânicos
      • Serragem
    """)

with col2:
    st.subheader("🔄 Operação")
    st.markdown(f"""
    - **Ciclo:** 50 dias
    - **Processo:** Enche → Composta → Esvazia
    - **Capacidade/ciclo:** {formatar_brasil(capacidade_ciclo_kg, 1)} kg
    - **Ciclos/ano:** {ciclos_ano}
    - **Produtos:**
      • Húmus (fertilizante)
      • Bio-wash (líquido)
    """)

with col3:
    st.subheader("📈 Resíduos Processados")
    st.markdown(f"""
    - **Reatores:** {num_reatores} unidades
    - **Processamento/anual:** {formatar_brasil(residuo_anual_ton, 1)} t
    - **Resíduos/dia:** {formatar_brasil(residuos_kg_dia, 1)} kg
    - **Tipos de resíduos:**
      • Frutas e verduras
      • Borra de café
      • Restos de refeitório
    """)

# =============================================================================
# PARÂMETROS TÉCNICOS FIXOS
# =============================================================================

# Parâmetros para cálculos de emissões (baseados em literatura científica)
T = 25  # Temperatura média
DOC = 0.15  # Carbono orgânico degradável

# Compostagem com minhocas (Yang et al. 2017)
TOC_COMPOSTAGEM_MINHOCAS = 0.436
TN_COMPOSTAGEM_MINHOCAS = 14.2 / 1000
CH4_C_FRAC_COMPOSTAGEM_MINHOCAS = 0.13 / 100
N2O_N_FRAC_COMPOSTAGEM_MINHOCAS = 0.92 / 100

# Perfis temporais de emissões
PERFIL_CH4_COMPOSTAGEM_MINHOCAS = np.array([0.02, 0.02, 0.02, 0.03, 0.03, 0.04, 0.04, 0.05, 0.05, 0.06, 
                            0.07, 0.08, 0.09, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 
                            0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 
                            0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 
                            0.002, 0.002, 0.002, 0.002, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001])
PERFIL_CH4_COMPOSTAGEM_MINHOCAS /= PERFIL_CH4_COMPOSTAGEM_MINHOCAS.sum()

PERFIL_N2O_COMPOSTAGEM_MINHOCAS = np.array([0.15, 0.10, 0.20, 0.05, 0.03, 0.03, 0.03, 0.04, 0.05, 0.06, 
                            0.08, 0.09, 0.10, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 
                            0.01, 0.01, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 
                            0.002, 0.002, 0.002, 0.002, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001, 
                            0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001])
PERFIL_N2O_COMPOSTAGEM_MINHOCAS /= PERFIL_N2O_COMPOSTAGEM_MINHOCAS.sum()

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7
GWP_N2O_20 = 273

# =============================================================================
# CÁLCULOS SIMPLIFICADOS
# =============================================================================

def calcular_emissoes_compostagem_minhocas():
    """Calcula emissões da compostagem com minhocas - versão simplificada"""
    # Parâmetros fixos para resíduos escolares
    umidade = 0.85  # 85% - típico para frutas/verduras
    fracao_ms = 1 - umidade
    
    # Cálculo baseado em Yang et al. (2017)
    ch4_total_por_lote = residuos_kg_dia * (TOC_COMPOSTAGEM_MINHOCAS * CH4_C_FRAC_COMPOSTAGEM_MINHOCAS * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia * (TN_COMPOSTAGEM_MINHOCAS * N2O_N_FRAC_COMPOSTAGEM_MINHOCAS * (44/28) * fracao_ms)
    
    # Emissões anuais (simplificado)
    emissões_CH4_ano = ch4_total_por_lote * 365
    emissões_N2O_ano = n2o_total_por_lote * 365
    
    # Converter para tCO₂eq
    emissões_tco2eq_ano = (emissões_CH4_ano * GWP_CH4_20 + emissões_N2O_ano * GWP_N2O_20) / 1000
    
    return emissões_tco2eq_ano

def calcular_emissoes_aterro():
    """Calcula emissões do aterro - versão simplificada"""
    # Fator de emissão simplificado para aterro (kg CO₂eq/kg resíduo)
    fator_emissao_aterro = 0.8  # Baseado em IPCC e literatura
    
    emissões_tco2eq_ano = (residuo_anual_kg * fator_emissao_aterro) / 1000
    
    return emissões_tco2eq_ano

# =============================================================================
# EXECUÇÃO DA SIMULAÇÃO
# =============================================================================

if st.session_state.get('run_simulation', False):
    st.header("💰 Resultados Financeiros")
    
    # Cálculos
    emissoes_aterro_ano = calcular_emissoes_aterro()
    emissoes_compostagem_ano = calcular_emissoes_compostagem_minhocas()
    emissoes_evitadas_ano = emissoes_aterro_ano - emissoes_compostagem_ano
    total_evitado = emissoes_evitadas_ano * anos_simulacao
    
    # Cotação
    preco_carbono_eur, moeda, _, _, fonte = obter_cotacao_carbono()
    taxa_cambio, _, _, _ = obter_cotacao_euro_real()
    preco_carbono_brl = preco_carbono_eur * taxa_cambio
    
    # Valores financeiros
    valor_eur = calcular_valor_creditos(total_evitado, preco_carbono_eur, "€")
    valor_brl = calcular_valor_creditos(total_evitado, preco_carbono_brl, "R$")
    
    # Métricas principais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Emissões Evitadas",
            f"{formatar_brasil(total_evitado)} tCO₂eq",
            f"{anos_simulacao} anos"
        )
    
    with col2:
        st.metric(
            "Preço do Carbono", 
            f"R$ {formatar_brasil(preco_carbono_brl)}/tCO₂eq",
            f"Fonte: {fonte}"
        )
    
    with col3:
        st.metric(
            "Valor dos Créditos",
            f"R$ {formatar_brasil(valor_brl)}",
            f"{formatar_brasil(total_evitado)} tCO₂eq"
        )
    
    # Detalhamento
    st.subheader("📊 Detalhamento do Projeto")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **🏭 Cenário Atual (Aterro):**
        - Emissões anuais: {formatar_brasil(emissoes_aterro_ano)} tCO₂eq
        - Emissões totais: {formatar_brasil(emissoes_aterro_ano * anos_simulacao)} tCO₂eq
        
        **♻️ Projeto (Compostagem):**
        - Emissões anuais: {formatar_brasil(emissoes_compostagem_ano)} tCO₂eq  
        - Emissões totais: {formatar_brasil(emissoes_compostagem_ano * anos_simulacao)} tCO₂eq
        """)
    
    with col2:
        st.markdown(f"""
        **📈 Redução de Emissões:**
        - Redução anual: {formatar_brasil(emissoes_evitadas_ano)} tCO₂eq
        - Redução total: {formatar_brasil(total_evitado)} tCO₂eq
        
        **💵 Valor Financeiro:**
        - Em Euros: {formatar_brasil(valor_eur, moeda=True, simbolo_moeda="€")}
        - Em Reais: {formatar_brasil(valor_brl, moeda=True, simbolo_moeda="R$")}
        """)
    
    # Projeção anual
    st.subheader("📅 Projeção Anual")
    
    projecao_data = []
    for ano in range(1, anos_simulacao + 1):
        acumulado_emissoes = emissoes_evitadas_ano * ano
        acumulado_valor = calcular_valor_creditos(acumulado_emissoes, preco_carbono_brl, "R$")
        
        projecao_data.append({
            'Ano': ano,
            'Emissões Evitadas (tCO₂eq)': formatar_brasil(acumulado_emissoes, 1),
            'Valor Acumulado (R$)': formatar_brasil(acumulado_valor, moeda=True, simbolo_moeda="R$")
        })
    
    st.dataframe(pd.DataFrame(projecao_data), use_container_width=True)

else:
    # Tela inicial
    st.info("""
    **💡 Como usar este simulador:**
    
    1. **Configure o sistema** na barra lateral:
       - Escolha a capacidade dos reatores (30L padrão)
       - Defina quantos reatores terá o sistema  
       - Ajuste os ciclos por ano (6 é o padrão)
    
    2. **Selecione a duração** do projeto (12 anos é típico para escolas)
    
    3. **Clique em "Calcular Créditos de Carbono"** para ver os resultados
    
    **🌱 Sobre os resíduos processados:**
    - Frutas e verduras de refeitórios escolares
    - Borra de café das cantinas  
    - Restos de preparo de alimentos
    - Material orgânico de hortas escolares
    """)

# =============================================================================
# INFORMAÇÕES ADICIONAIS
# =============================================================================

with st.expander("📚 Sobre a Metodologia"):
    st.markdown("""
    **🔬 Base Científica:**
    
    **Compostagem com Minhocas (Yang et al. 2017):**
    - Metodologia validada para resíduos alimentares
    - Fatores de emissão específicos para minhocas californianas
    - Período de compostagem: 50 dias
    - Eficiência comprovada na redução de emissões
    
    **Cenário de Referência (Aterro):**
    - Baseado em metodologias IPCC
    - Considera emissões de metano e óxido nitroso
    - Inclui emissões do processo de decomposição
    
    **💼 Aplicação Prática:**
    - Projetos escolares de 4-20 anos
    - Sistemas modulares de 1-10 reatores
    - Capacidade de 20-100 litros por reator
    - Processamento contínuo ao longo do ano
    
    **🎯 Benefícios Adicionais:**
    - Produção de fertilizante orgânico
    - Educação ambiental para alunos
    - Redução de custos com gestão de resíduos
    - Certificação de créditos de carbono
    """)

# Rodapé profissional
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <h4>🏫 Sistema de Compostagem com Minhocas - Ribeirão Preto/SP</h4>
    <p><strong>Secretaria Municipal de Educação</strong> • Desenvolvido para projetos de sustentabilidade escolar</p>
    <p><em>Metodologia: Compostagem com minhocas (Yang et al. 2017) • GWP: IPCC AR6</em></p>
</div>
""", unsafe_allow_html=True)

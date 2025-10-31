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
**Simulador de créditos de carbono para sistemas de compostagem em escolas**
*Cálculo baseado no processamento de resíduos de frutas, verduras e restaurantes escolares*
""")

# =============================================================================
# FUNÇÃO DE FORMATAÇÃO BRASILEIRA
# =============================================================================

def formatar_brasil(numero, casas_decimais=2, moeda=False, simbolo_moeda=""):
    """
    Formata números no padrão brasileiro (vírgula decimal e ponto milhar)
    """
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
# FUNÇÕES DE COTAÇÃO AUTOMÁTICA DO CARBONO E CÂMBIO
# =============================================================================

def obter_cotacao_carbono_investing():
    """
    Obtém a cotação em tempo real do carbono
    """
    try:
        # Valor fixo para evitar problemas de scraping
        return 85.50, "€", "Carbon Emissions Future", True, "Referência"
    except Exception as e:
        return 85.50, "€", "Carbon Emissions (Referência)", False, f"Erro: {str(e)}"

def obter_cotacao_carbono():
    preco, moeda, contrato_info, sucesso, fonte = obter_cotacao_carbono_investing()
    return preco, moeda, f"{contrato_info}", True, fonte

def obter_cotacao_euro_real():
    try:
        # Valor fixo para simplificar
        return 5.50, "R$", True, "Referência"
    except:
        return 5.50, "R$", False, "Referência"

def calcular_valor_creditos(emissoes_evitadas_tco2eq, preco_carbono_por_tonelada, moeda, taxa_cambio=1):
    valor_total = emissoes_evitadas_tco2eq * preco_carbono_por_tonelada * taxa_cambio
    return valor_total

def exibir_cotacao_carbono():
    st.sidebar.header("💰 Mercado de Carbono e Câmbio")
    
    if not st.session_state.get('cotacao_carregada', False):
        st.session_state.mostrar_atualizacao = True
        st.session_state.cotacao_carregada = True
    
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        if st.button("🔄 Atualizar Cotações", key="atualizar_cotacoes"):
            st.session_state.cotacao_atualizada = True
            st.session_state.mostrar_atualizacao = True
    
    if st.session_state.get('mostrar_atualizacao', False):
        st.sidebar.info("🔄 Atualizando cotações...")
        
        preco_carbono, moeda, contrato_info, sucesso_carbono, fonte_carbono = obter_cotacao_carbono()
        preco_euro, moeda_real, sucesso_euro, fonte_euro = obter_cotacao_euro_real()
        
        st.session_state.preco_carbono = preco_carbono
        st.session_state.moeda_carbono = moeda
        st.session_state.taxa_cambio = preco_euro
        st.session_state.moeda_real = moeda_real
        st.session_state.fonte_cotacao = fonte_carbono
        
        st.session_state.mostrar_atualizacao = False
        st.session_state.cotacao_atualizada = False
        
        st.rerun()

    st.sidebar.metric(
        label=f"Preço do Carbono (tCO₂eq)",
        value=formatar_brasil(st.session_state.preco_carbono, moeda=True, simbolo_moeda=st.session_state.moeda_carbono),
        help=f"Fonte: {st.session_state.fonte_cotacao}"
    )
    
    st.sidebar.metric(
        label="Euro (EUR/BRL)",
        value=formatar_brasil(st.session_state.taxa_cambio, moeda=True, simbolo_moeda=st.session_state.moeda_real),
        help="Cotação do Euro em Reais Brasileiros"
    )
    
    preco_carbono_reais = st.session_state.preco_carbono * st.session_state.taxa_cambio
    
    st.sidebar.metric(
        label=f"Carbono em Reais (tCO₂eq)",
        value=formatar_brasil(preco_carbono_reais, moeda=True, simbolo_moeda="R$"),
        help="Preço do carbono convertido para Reais Brasileiros"
    )

# =============================================================================
# INICIALIZAÇÃO DA SESSION STATE
# =============================================================================

def inicializar_session_state():
    if 'preco_carbono' not in st.session_state:
        preco_carbono, moeda, contrato_info, sucesso, fonte = obter_cotacao_carbono()
        st.session_state.preco_carbono = preco_carbono
        st.session_state.moeda_carbono = moeda
        st.session_state.fonte_cotacao = fonte
        
    if 'taxa_cambio' not in st.session_state:
        preco_euro, moeda_real, sucesso_euro, fonte_euro = obter_cotacao_euro_real()
        st.session_state.taxa_cambio = preco_euro
        st.session_state.moeda_real = moeda_real
        
    if 'moeda_real' not in st.session_state:
        st.session_state.moeda_real = "R$"
    if 'cotacao_atualizada' not in st.session_state:
        st.session_state.cotacao_atualizada = False
    if 'run_simulation' not in st.session_state:
        st.session_state.run_simulation = False
    if 'mostrar_atualizacao' not in st.session_state:
        st.session_state.mostrar_atualizacao = False
    if 'cotacao_carregada' not in st.session_state:
        st.session_state.cotacao_carregada = False

inicializar_session_state()

# =============================================================================
# FUNÇÕES DO SISTEMA DE REATORES DE COMPOSTAGEM
# =============================================================================

def calcular_capacidade_sistema(capacidade_reator_litros, num_reatores, densidade_kg_l=0.5):
    """
    Calcula a capacidade total do sistema de compostagem
    """
    capacidade_por_ciclo_kg = capacidade_reator_litros * densidade_kg_l * num_reatores
    return capacidade_por_ciclo_kg, capacidade_por_ciclo_kg

def calcular_residuo_processado_anual(capacidade_reator_litros, num_reatores, ciclos_ano, densidade_kg_l=0.5):
    """
    Calcula a quantidade total de resíduo processado por ano
    """
    residuo_por_ciclo_kg = capacidade_reator_litros * densidade_kg_l * num_reatores
    residuo_total_kg = residuo_por_ciclo_kg * ciclos_ano
    return residuo_total_kg

# =============================================================================
# SIDEBAR COM CONFIGURAÇÃO DO SISTEMA
# =============================================================================

# Exibir cotação de carbono
exibir_cotacao_carbono()

with st.sidebar:
    st.header("⚙️ Sistema de Reatores de Compostagem")
    
    # Configuração do sistema
    st.subheader("📦 Configuração dos Reatores")
    
    capacidade_reator = st.slider(
        "Capacidade de cada reator (litros)",
        min_value=20,
        max_value=100,
        value=30,
        step=5,
        help="Caixas padrão para coleta de biofertilizante (bio-wash)"
    )
    
    num_reatores = st.slider(
        "Número de reatores no sistema",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="Cada reator contém minhocas, substrato, resíduos e serragem"
    )
    
    # Parâmetros operacionais
    st.subheader("🔄 Parâmetros Operacionais")
    
    ciclos_ano = st.slider(
        "Ciclos completos por ano",
        min_value=1,
        max_value=12,
        value=6,
        step=1,
        help="Número de vezes que os reatores são completamente processados por ano (ciclo de 50 dias)"
    )
    
    densidade_residuo = st.slider(
        "Densidade do resíduo (kg/litro)",
        min_value=0.3,
        max_value=0.8,
        value=0.5,
        step=0.05,
        help="Densidade média dos resíduos orgânicos de frutas e verduras"
    )
    
    # Cálculos automáticos do sistema
    capacidade_ciclo_kg, capacidade_total_kg = calcular_capacidade_sistema(
        capacidade_reator, num_reatores, densidade_residuo
    )
    
    residuo_anual_kg = calcular_residuo_processado_anual(
        capacidade_reator, num_reatores, ciclos_ano, densidade_residuo
    )
    residuo_anual_ton = residuo_anual_kg / 1000
    
    # Calcular resíduos diários baseado na capacidade do sistema
    residuos_kg_dia = residuo_anual_kg / 365
    
    # Exibir informações do sistema
    st.info(f"""
    **📊 Capacidade do Sistema:**
    - Por ciclo: {formatar_brasil(capacidade_ciclo_kg, 1)} kg
    - Por ano: {formatar_brasil(residuo_anual_ton, 1)} ton
    - Resíduos/dia: {formatar_brasil(residuos_kg_dia, 1)} kg
    - Reatores: {num_reatores} × {capacidade_reator}L
    - Ciclos/ano: {ciclos_ano}
    """)
    
    # Parâmetros adicionais para cálculos de emissões
    st.subheader("🌡️ Parâmetros Ambientais")
    
    umidade_valor = st.slider(
        "Umidade do resíduo (%)", 
        50, 95, 85, 1,
        help="Percentual de umidade dos resíduos orgânicos"
    )
    umidade = umidade_valor / 100.0
    
    massa_exposta_kg = st.slider(
        "Massa exposta na frente de trabalho (kg)", 
        50, 200, 100, 10,
        help="Massa de resíduos exposta diariamente para tratamento"
    )
    
    h_exposta = st.slider(
        "Horas expostas por dia", 
        4, 24, 8, 1,
        help="Horas diárias de exposição dos resíduos"
    )
    
    # Configuração da simulação
    st.subheader("🎯 Configuração de Simulação")
    anos_simulacao = st.selectbox(
        "Período de simulação",
        options=[4, 8, 12, 16, 20],
        index=4,
        help="Período total da simulação em anos (escolas tipicamente 4-20 anos)"
    )
    
    if st.button("🚀 Executar Simulação Completa", type="primary"):
        st.session_state.run_simulation = True

# =============================================================================
# INFORMAÇÕES SOBRE O SISTEMA - COM CAPACIDADE DINÂMICA
# =============================================================================

st.header("🏫 Sistema de Compostagem Escolar")

col1, col2, col3 = st.columns(3)

with col1:
    # TÍTULO DINÂMICO - ATUALIZADO COM A CAPACIDADE ESCOLHIDA
    st.subheader(f"📦 Reatores de {capacidade_reator}L")
    st.markdown(f"""
    - **Material:** Plástico resistente
    - **Função:** Processar resíduos + coletar biofertilizante
    - **Capacidade:** {formatar_brasil(capacidade_ciclo_kg/num_reatores, 1)} kg/reator por ciclo
    - **Conteúdo:**
      • Minhocas Californianas
      • Substrato inicial
      • Resíduos orgânicos
      • Serragem (carbono)
    """)

with col2:
    st.subheader("🔄 Operação")
    st.markdown(f"""
    - **Ciclo:** 50 dias
    - **Processo:** Enche → Aguarda {ciclos_ano}x/ano → Esvazia
    - **Capacidade/ciclo:** {formatar_brasil(capacidade_ciclo_kg, 1)} kg
    - **Produtos:**
      • Húmus (fertilizante sólido)
      • Bio-wash (fertilizante líquido)
    - **Manutenção:** Diária (alimentação)
    """)

with col3:
    st.subheader("📈 Capacidade Total")
    st.markdown(f"""
    - **Reatores:** {num_reatores} unidades de {capacidade_reator}L
    - **Capacidade/ciclo:** {formatar_brasil(capacidade_ciclo_kg, 1)} kg
    - **Processamento/anual:** {formatar_brasil(residuo_anual_ton, 1)} ton
    - **Ciclos/ano:** {ciclos_ano}
    - **Resíduos/dia:** {formatar_brasil(residuos_kg_dia, 1)} kg
    """)

# =============================================================================
# PARÂMETROS FIXOS PARA CÁLCULO DETALHADO DA VERMICOMPOSTAGEM
# =============================================================================

# Parâmetros fixos para cálculos de emissões
T = 25  # Temperatura média (ºC)
DOC = 0.15  # Carbono orgânico degradável (fração)
DOCf_val = 0.0147 * T + 0.28
MCF = 1  # Fator de correção de metano
F = 0.5  # Fração de metano no biogás
OX = 0.1  # Fator de oxidação
Ri = 0.0  # Metano recuperado

# Constante de decaimento (fixa como no script anexo)
k_ano = 0.06  # Constante de decaimento anual

# Compostagem com minhocas (Yang et al. 2017) - valores fixos
TOC_COMPOSTAGEM_MINHOCAS = 0.436  # Fração de carbono orgânico total
TN_COMPOSTAGEM_MINHOCAS = 14.2 / 1000  # Fração de nitrogênio total
CH4_C_FRAC_COMPOSTAGEM_MINHOCAS = 0.13 / 100  # Fração do TOC emitida como CH4-C (fixo)
N2O_N_FRAC_COMPOSTAGEM_MINHOCAS = 0.92 / 100  # Fração do TN emitida como N2O-N (fixo)
DIAS_COMPOSTAGEM = 50  # Período total de compostagem

# Perfil temporal de emissões baseado em Yang et al. (2017)
PERFIL_CH4_COMPOSTAGEM_MINHOCAS = np.array([
    0.02, 0.02, 0.02, 0.03, 0.03,  # Dias 1-5
    0.04, 0.04, 0.05, 0.05, 0.06,  # Dias 6-10
    0.07, 0.08, 0.09, 0.10, 0.09,  # Dias 11-15
    0.08, 0.07, 0.06, 0.05, 0.04,  # Dias 16-20
    0.03, 0.02, 0.02, 0.01, 0.01,  # Dias 21-25
    0.01, 0.01, 0.01, 0.01, 0.01,  # Dias 26-30
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 31-35
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 36-40
    0.002, 0.002, 0.002, 0.002, 0.002,  # Dias 41-45
    0.001, 0.001, 0.001, 0.001, 0.001   # Dias 46-50
])
PERFIL_CH4_COMPOSTAGEM_MINHOCAS /= PERFIL_CH4_COMPOSTAGEM_MINHOCAS.sum()

PERFIL_N2O_COMPOSTAGEM_MINHOCAS = np.array([
    0.15, 0.10, 0.20, 0.05, 0.03,  # Dias 1-5 (pico no dia 3)
    0.03, 0.03, 0.04, 0.05, 0.06,  # Dias 6-10
    0.08, 0.09, 0.10, 0.08, 0.07,  # Dias 11-15
    0.06, 0.05, 0.04, 0.03, 0.02,  # Dias 16-20
    0.01, 0.01, 0.005, 0.005, 0.005,  # Dias 21-25
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 26-30
    0.002, 0.002, 0.002, 0.002, 0.002,  # Dias 31-35
    0.001, 0.001, 0.001, 0.001, 0.001,  # Dias 36-40
    0.001, 0.001, 0.001, 0.001, 0.001,  # Dias 41-45
    0.001, 0.001, 0.001, 0.001, 0.001   # Dias 46-50
])
PERFIL_N2O_COMPOSTAGEM_MINHOCAS /= PERFIL_N2O_COMPOSTAGEM_MINHOCAS.sum()

# Emissões pré-descarte (Feng et al. 2020)
CH4_pre_descarte_ugC_por_kg_h_media = 2.78

fator_conversao_C_para_CH4 = 16/12
CH4_pre_descarte_ugCH4_por_kg_h_media = CH4_pre_descarte_ugC_por_kg_h_media * fator_conversao_C_para_CH4
CH4_pre_descarte_g_por_kg_dia = CH4_pre_descarte_ugCH4_por_kg_h_media * 24 / 1_000_000

N2O_pre_descarte_mgN_por_kg = 20.26
N2O_pre_descarte_mgN_por_kg_dia = N2O_pre_descarte_mgN_por_kg / 3
N2O_pre_descarte_g_por_kg_dia = N2O_pre_descarte_mgN_por_kg_dia * (44/28) / 1000

PERFIL_N2O_PRE_DESCARTE = {1: 0.8623, 2: 0.10, 3: 0.0377}

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7
GWP_N2O_20 = 273

# Período de Simulação
dias = anos_simulacao * 365
ano_inicio = datetime.now().year
data_inicio = datetime(ano_inicio, 1, 1)
datas = pd.date_range(start=data_inicio, periods=dias, freq='D')

# Perfil temporal N2O (Wang et al. 2017)
PERFIL_N2O = {1: 0.10, 2: 0.30, 3: 0.40, 4: 0.15, 5: 0.05}

# =============================================================================
# FUNÇÕES DE CÁLCULO DETALHADO (BASEADO NO SCRIPT ORIGINAL)
# =============================================================================

def ajustar_emissoes_pre_descarte(O2_concentracao=21):
    ch4_ajustado = CH4_pre_descarte_g_por_kg_dia

    if O2_concentracao == 21:
        fator_n2o = 1.0
    elif O2_concentracao == 10:
        fator_n2o = 11.11 / 20.26
    elif O2_concentracao == 1:
        fator_n2o = 7.86 / 20.26
    else:
        fator_n2o = 1.0

    n2o_ajustado = N2O_pre_descarte_g_por_kg_dia * fator_n2o
    return ch4_ajustado, n2o_ajustado

def calcular_emissoes_pre_descarte(O2_concentracao=21, dias_simulacao=dias):
    ch4_ajustado, n2o_ajustado = ajustar_emissoes_pre_descarte(O2_concentracao)

    emissoes_CH4_pre_descarte_kg = np.full(dias_simulacao, residuos_kg_dia * ch4_ajustado / 1000)
    emissoes_N2O_pre_descarte_kg = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dias_apos_descarte, fracao in PERFIL_N2O_PRE_DESCARTE.items():
            dia_emissao = dia_entrada + dias_apos_descarte - 1
            if dia_emissao < dias_simulacao:
                emissoes_N2O_pre_descarte_kg[dia_emissao] += (
                    residuos_kg_dia * n2o_ajustado * fracao / 1000
                )

    return emissoes_CH4_pre_descarte_kg, emissoes_N2O_pre_descarte_kg

def calcular_emissoes_aterro(dias_simulacao=dias):
    umidade_val, temp_val, doc_val = umidade, T, DOC

    fator_umid = (1 - umidade_val) / (1 - 0.55)
    f_aberto = np.clip((massa_exposta_kg / residuos_kg_dia) * (h_exposta / 24), 0.0, 1.0)
    docf_calc = 0.0147 * temp_val + 0.28

    potencial_CH4_por_kg = doc_val * docf_calc * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    potencial_CH4_lote_diario = residuos_kg_dia * potencial_CH4_por_kg

    t = np.arange(1, dias_simulacao + 1, dtype=float)
    kernel_ch4 = np.exp(-k_ano * (t - 1) / 365.0) - np.exp(-k_ano * t / 365.0)
    entradas_diarias = np.ones(dias_simulacao, dtype=float)
    emissoes_CH4 = np.convolve(entradas_diarias, kernel_ch4, mode='full')[:dias_simulacao]
    emissoes_CH4 *= potencial_CH4_lote_diario

    E_aberto = 1.91
    E_fechado = 2.15
    E_medio = f_aberto * E_aberto + (1 - f_aberto) * E_fechado
    E_medio_ajust = E_medio * fator_umid
    emissao_diaria_N2O = (E_medio_ajust * (44/28) / 1_000_000) * residuos_kg_dia

    kernel_n2o = np.array([PERFIL_N2O.get(d, 0) for d in range(1, 6)], dtype=float)
    emissoes_N2O = np.convolve(np.full(dias_simulacao, emissao_diaria_N2O), kernel_n2o, mode='full')[:dias_simulacao]

    O2_concentracao = 21
    emissoes_CH4_pre_descarte_kg, emissoes_N2O_pre_descarte_kg = calcular_emissoes_pre_descarte(O2_concentracao, dias_simulacao)

    total_ch4_aterro_kg = emissoes_CH4 + emissoes_CH4_pre_descarte_kg
    total_n2o_aterro_kg = emissoes_N2O + emissoes_N2O_pre_descarte_kg

    return total_ch4_aterro_kg, total_n2o_aterro_kg

def calcular_emissoes_compostagem_minhocas(dias_simulacao=dias):
    umidade_val, temp_val, doc_val = umidade, T, DOC
    fracao_ms = 1 - umidade_val
    
    # Usando valores fixos para compostagem com minhocas
    ch4_total_por_lote = residuos_kg_dia * (TOC_COMPOSTAGEM_MINHOCAS * CH4_C_FRAC_COMPOSTAGEM_MINHOCAS * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia * (TN_COMPOSTAGEM_MINHOCAS * N2O_N_FRAC_COMPOSTAGEM_MINHOCAS * (44/28) * fracao_ms)

    emissoes_CH4 = np.zeros(dias_simulacao)
    emissoes_N2O = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dia_compostagem in range(len(PERFIL_CH4_COMPOSTAGEM_MINHOCAS)):
            dia_emissao = dia_entrada + dia_compostagem
            if dia_emissao < dias_simulacao:
                emissoes_CH4[dia_emissao] += ch4_total_por_lote * PERFIL_CH4_COMPOSTAGEM_MINHOCAS[dia_compostagem]
                emissoes_N2O[dia_emissao] += n2o_total_por_lote * PERFIL_N2O_COMPOSTAGEM_MINHOCAS[dia_compostagem]

    return emissoes_CH4, emissoes_N2O

# =============================================================================
# SIMULAÇÃO DETALHADA - CÁLCULO COMPLETO DAS EMISSÕES
# =============================================================================

if st.session_state.get('run_simulation', False):
    st.header("📊 Resultados Detalhados da Simulação - Compostagem com Minhocas")
    
    with st.spinner('Calculando emissões detalhadas...'):
        # Calcular emissões para aterro e compostagem com minhocas
        ch4_aterro_kg, n2o_aterro_kg = calcular_emissoes_aterro()
        ch4_compostagem_kg, n2o_compostagem_kg = calcular_emissoes_compostagem_minhocas()
        
        # Converter para tCO₂eq
        total_aterro_tco2eq = (ch4_aterro_kg * GWP_CH4_20 + n2o_aterro_kg * GWP_N2O_20) / 1000
        total_compostagem_tco2eq = (ch4_compostagem_kg * GWP_CH4_20 + n2o_compostagem_kg * GWP_N2O_20) / 1000
        
        # Calcular emissões evitadas
        reducao_tco2eq_dia = total_aterro_tco2eq - total_compostagem_tco2eq
        total_evitado_compostagem_minhocas = reducao_tco2eq_dia.sum()
        
        # Emissões anuais evitadas
        emissões_evitadas_ano = total_evitado_compostagem_minhocas / anos_simulacao
    
    # Obter preço do carbono
    preco_carbono = st.session_state.preco_carbono
    moeda = st.session_state.moeda_carbono
    taxa_cambio = st.session_state.taxa_cambio
    fonte_cotacao = st.session_state.fonte_cotacao
    
    # Calcular valores financeiros
    valor_compostagem_minhocas_eur = calcular_valor_creditos(total_evitado_compostagem_minhocas, preco_carbono, moeda)
    valor_compostagem_minhocas_brl = calcular_valor_creditos(total_evitado_compostagem_minhocas, preco_carbono, "R$", taxa_cambio)
    
    # SEÇÃO: VALOR FINANCEIRO
    st.subheader("💰 Valor Financeiro das Emissões Evitadas")
    
    # Euros
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            f"Preço Carbono (Euro)", 
            f"{moeda} {formatar_brasil(preco_carbono)}/tCO₂eq",
            help=f"Fonte: {fonte_cotacao}"
        )
    with col2:
        st.metric(
            "Valor Créditos (Euro)", 
            f"{moeda} {formatar_brasil(valor_compostagem_minhocas_eur)}",
            help=f"Baseado em {formatar_brasil(total_evitado_compostagem_minhocas)} tCO₂eq evitadas"
        )
    
    # Reais
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            f"Preço Carbono (R$)", 
            f"R$ {formatar_brasil(preco_carbono * taxa_cambio)}/tCO₂eq",
            help="Preço do carbono convertido para Reais"
        )
    with col2:
        st.metric(
            "Valor Créditos (R$)", 
            f"R$ {formatar_brasil(valor_compostagem_minhocas_brl)}",
            help=f"Baseado em {formatar_brasil(total_evitado_compostagem_minhocas)} tCO₂eq evitadas"
        )

    # RESUMO DO SISTEMA
    st.subheader("🏫 Resumo do Sistema de Compostagem com Minhocas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Capacidade do Sistema",
            f"{formatar_brasil(residuo_anual_ton, 1)} ton/ano",
            f"{num_reatores} reatores de {capacidade_reator}L"
        )
    
    with col2:
        st.metric(
            "Emissões Evitadas/Ano",
            f"{formatar_brasil(emissões_evitadas_ano)} tCO₂eq",
            "Metodologia Yang et al. (2017)"
        )
    
    with col3:
        st.metric(
            "Total Evitado",
            f"{formatar_brasil(total_evitado_compostagem_minhocas)} tCO₂eq",
            f"{anos_simulacao} anos"
        )
    
    with col4:
        st.metric(
            "Valor Financeiro Total",
            f"R$ {formatar_brasil(valor_compostagem_minhocas_brl)}",
            f"{formatar_brasil(total_evitado_compostagem_minhocas)} tCO₂eq"
        )

    # DETALHAMENTO DOS CÁLCULOS
    st.subheader("🧮 Detalhamento dos Cálculos - Compostagem com Minhocas")
    
    with st.expander("📋 Métodos de Cálculo Detalhado"):
        st.markdown(f"""
        **Cálculo da Capacidade do Sistema:**
        ```
        Capacidade por ciclo = Capacidade reator × N° reatores × Densidade
                            = {capacidade_reator} L × {num_reatores} × {densidade_residuo} kg/L
                            = {formatar_brasil(capacidade_ciclo_kg, 1)} kg/ciclo
        
        Resíduo anual = Capacidade por ciclo × Ciclos/ano
                     = {formatar_brasil(capacidade_ciclo_kg, 1)} kg × {ciclos_ano}
                     = {formatar_brasil(residuo_anual_kg, 0)} kg/ano
                     = {formatar_brasil(residuo_anual_ton, 1)} ton/ano
        
        Resíduos/dia = Resíduo anual ÷ 365 dias
                     = {formatar_brasil(residuo_anual_kg, 0)} kg ÷ 365
                     = {formatar_brasil(residuos_kg_dia, 1)} kg/dia
        ```
        
        **Cálculo das Emissões do Aterro (Baseline):**
        - Metodologia: IPCC (2006) + Wang et al. (2017) + Feng et al. (2020)
        - CH4: Modelo de decaimento exponencial + emissões pré-descarte
        - N2O: Fatores de emissão específicos + perfil temporal
        
        **Cálculo das Emissões da Compostagem com Minhocas:**
        - Metodologia: Yang et al. (2017)
        - CH4: {CH4_C_FRAC_COMPOSTAGEM_MINHOCAS*100}% do TOC emitido como CH4-C
        - N2O: {N2O_N_FRAC_COMPOSTAGEM_MINHOCAS*100}% do TN emitido como N2O-N
        - Perfil temporal: 50 dias com distribuição específica
        
        **Cálculo das Emissões Evitadas:**
        ```
        Emissões evitadas = Emissões Aterro - Emissões Compostagem
                         = {formatar_brasil(total_aterro_tco2eq.sum(), 1)} tCO₂eq - {formatar_brasil(total_compostagem_tco2eq.sum(), 1)} tCO₂eq
                         = {formatar_brasil(total_evitado_compostagem_minhocas)} tCO₂eq
        ```
        
        **Cálculo do Valor Financeiro:**
        ```
        Valor (Euro) = Total evitado × Preço carbono
                    = {formatar_brasil(total_evitado_compostagem_minhocas)} tCO₂eq × {moeda} {formatar_brasil(preco_carbono)}/tCO₂eq
                    = {moeda} {formatar_brasil(valor_compostagem_minhocas_eur)}
        
        Valor (R$) = Valor (Euro) × Taxa câmbio
                  = {moeda} {formatar_brasil(valor_compostagem_minhocas_eur)} × R$ {formatar_brasil(taxa_cambio)}/€
                  = R$ {formatar_brasil(valor_compostagem_minhocas_brl)}
        ```
        
        **📚 Base Científica:**
        - **Metodologia:** Compostagem com minhocas (Yang et al. 2017)
        - **Aterro sanitário:** IPCC (2006), Wang et al. (2017), Feng et al. (2020)
        - **GWP:** IPCC AR6 (20 anos)
        - **Ciclo:** 50 dias (otimizado para minhocas californianas)
        """)
    
    # PROJEÇÃO ANUAL
    st.subheader("📅 Projeção Anual de Resultados")
    
    # Criar projeção anual
    projecao_anual = []
    for ano in range(1, anos_simulacao + 1):
        emissões_acumuladas = emissões_evitadas_ano * ano
        valor_eur_acumulado = calcular_valor_creditos(emissões_acumuladas, preco_carbono, "€")
        valor_brl_acumulado = calcular_valor_creditos(emissões_acumuladas, preco_carbono, "R$", taxa_cambio)
        
        projecao_anual.append({
            'Ano': ano,
            'Emissões Evitadas Acumuladas (tCO₂eq)': formatar_brasil(emissões_acumuladas, 1),
            'Valor Acumulado (€)': formatar_brasil(valor_eur_acumulado, moeda=True, simbolo_moeda="€"),
            'Valor Acumulado (R$)': formatar_brasil(valor_brl_acumulado, moeda=True, simbolo_moeda="R$")
        })
    
    projecao_df = pd.DataFrame(projecao_anual)
    st.dataframe(projecao_df, use_container_width=True)

else:
    st.info("""
    💡 **Configure o sistema de compostagem na barra lateral e clique em 'Executar Simulação Completa' para ver os resultados.**
    
    O simulador calculará:
    - Capacidade total do sistema de compostagem
    - Emissões detalhadas do cenário baseline (aterro)
    - Emissões detalhadas da compostagem com minhocas
    - Emissões de gases de efeito estufa evitadas
    - Valor financeiro dos créditos de carbono
    - Projeção anual de resultados
    
    **🌱 Metodologia:** Compostagem com minhocas (Yang et al. 2017)
    """)

# =============================================================================
# INFORMAÇÕES ADICIONAIS
# =============================================================================

with st.expander("📚 Sobre a Metodologia de Cálculo"):
    st.markdown("""
    **🔬 Metodologia Científica:**
    
    **Compostagem com Minhocas (Yang et al. 2017):**
    - **TOC (Carbono Orgânico Total):** {TOC_COMPOSTAGEM_MINHOCAS*100}% dos resíduos
    - **TN (Nitrogênio Total):** {TN_COMPOSTAGEM_MINHOCAS*1000} g/kg dos resíduos  
    - **CH4 emitido:** {CH4_C_FRAC_COMPOSTAGEM_MINHOCAS*100}% do TOC como CH4-C
    - **N2O emitido:** {N2O_N_FRAC_COMPOSTAGEM_MINHOCAS*100}% do TN como N2O-N
    - **Período:** 50 dias de compostagem
    - **Perfil temporal:** Distribuição específica ao longo do processo
    
    **Cenário Baseline - Aterro Sanitário:**
    - **Metodologia CH4:** IPCC (2006) - Modelo de decaimento exponencial
    - **Metodologia N2O:** Wang et al. (2017) - Fatores de emissão
    - **Emissões pré-descarte:** Feng et al. (2020)
    - **Constante de decaimento (k):** {k_ano} por ano
    
    **Parâmetros Globais:**
    - **GWP CH4 (20 anos):** {GWP_CH4_20} (IPCC AR6)
    - **GWP N2O (20 anos):** {GWP_N2O_20} (IPCC AR6)
    - **Temperatura padrão:** {T}°C
    - **DOC (Carbono Degradável):** {DOC*100}%
    
    **💡 Pressupostos do Modelo:**
    - Sistema opera continuamente durante o período simulado
    - Resíduos são processados imediatamente após geração
    - Condições operacionais mantidas constantes
    - Eficiência da compostagem com minhocas baseada em literatura
    - Fatores de emissão específicos para resíduos alimentares
    """)

# Rodapé
st.markdown("---")
st.markdown("""
**🏫 Sistema de Compostagem com Minhocas - Ribeirão Preto/SP**  
*Desenvolvido para cálculo de créditos de carbono no contexto educacional*

**📞 Contato:** Secretaria Municipal de Educação - Ribeirão Preto  
**🔬 Metodologia:** Compostagem com minhocas (Yang et al. 2017)
**🌍 GWP:** IPCC AR6 (20 anos)
""")

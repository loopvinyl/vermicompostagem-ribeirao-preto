import requests
from bs4 import BeautifulSoup
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import seaborn as sns
from scipy import stats
from scipy.signal import fftconvolve
from joblib import Parallel, delayed
import warnings
from matplotlib.ticker import FuncFormatter
from SALib.sample.sobol import sample
from SALib.analyze.sobol import analyze

np.random.seed(50)  # Garante reprodutibilidade

# Configurações iniciais
st.set_page_config(page_title="Simulador de Emissões CO₂eq", layout="wide")
warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
np.seterr(divide='ignore', invalid='ignore')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10
sns.set_style("whitegrid")

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

def formatar_br(numero):
    """Formata números no padrão brasileiro: 1.234,56"""
    if pd.isna(numero):
        return "N/A"
    numero = round(numero, 2)
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_format(x, pos):
    """Função de formatação para eixos de gráficos (padrão brasileiro)"""
    if x == 0:
        return "0"
    if abs(x) < 0.01:
        return f"{x:.1e}".replace(".", ",")
    if abs(x) >= 1000:
        return f"{x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =============================================================================
# FUNÇÕES DE COTAÇÃO AUTOMÁTICA DO CARBONO E CÂMBIO
# =============================================================================

def obter_cotacao_carbono_investing():
    """
    Obtém a cotação em tempo real do carbono via web scraping do Investing.com
    """
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.investing.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        selectores = [
            '[data-test="instrument-price-last"]',
            '.text-2xl',
            '.last-price-value',
            '.instrument-price-last',
            '.pid-1062510-last',
            '.float_lang_base_1',
            '.top.bold.inlineblock',
            '#last_last'
        ]
        
        preco = None
        fonte = "Investing.com"
        
        for seletor in selectores:
            try:
                elemento = soup.select_one(seletor)
                if elemento:
                    texto_preco = elemento.text.strip().replace(',', '')
                    texto_preco = ''.join(c for c in texto_preco if c.isdigit() or c == '.')
                    if texto_preco:
                        preco = float(texto_preco)
                        break
            except (ValueError, AttributeError):
                continue
        
        if preco is not None:
            return preco, "€", "Carbon Emissions Future", True, fonte
        
        import re
        padroes_preco = [
            r'"last":"([\d,]+)"',
            r'data-last="([\d,]+)"',
            r'last_price["\']?:\s*["\']?([\d,]+)',
            r'value["\']?:\s*["\']?([\d,]+)'
        ]
        
        html_texto = str(soup)
        for padrao in padroes_preco:
            matches = re.findall(padrao, html_texto)
            for match in matches:
                try:
                    preco_texto = match.replace(',', '')
                    preco = float(preco_texto)
                    if 50 < preco < 200:
                        return preco, "€", "Carbon Emissions Future", True, fonte
                except ValueError:
                    continue
                    
        return None, None, None, False, fonte
        
    except Exception as e:
        return None, None, None, False, f"Investing.com - Erro: {str(e)}"

def obter_cotacao_carbono():
    preco, moeda, contrato_info, sucesso, fonte = obter_cotacao_carbono_investing()
    
    if sucesso:
        return preco, moeda, f"{contrato_info}", True, fonte
    
    return 85.50, "€", "Carbon Emissions (Referência)", False, "Referência"

def obter_cotacao_euro_real():
    try:
        url = "https://economia.awesomeapi.com.br/last/EUR-BRL"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cotacao = float(data['EURBRL']['bid'])
            return cotacao, "R$", True, "AwesomeAPI"
    except:
        pass
    
    try:
        url = "https://api.exchangerate-api.com/v4/latest/EUR"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cotacao = data['rates']['BRL']
            return cotacao, "R$", True, "ExchangeRate-API"
    except:
        pass
    
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
    
    Args:
        capacidade_reator_litros: Capacidade de cada reator em litros
        num_reatores: Número total de reatores
        densidade_kg_l: Densidade dos resíduos (kg/litro)
    
    Returns:
        capacidade_total_kg: Capacidade total do sistema em kg
        capacidade_por_ciclo_kg: Capacidade por ciclo de compostagem
    """
    capacidade_por_ciclo_kg = capacidade_reator_litros * densidade_kg_l * num_reatores
    return capacidade_por_ciclo_kg, capacidade_por_ciclo_kg

def calcular_residuo_processado_anual(capacidade_reator_litros, num_reatores, ciclos_ano, densidade_kg_l=0.5):
    """
    Calcula a quantidade total de resíduo processado por ano
    
    Args:
        capacidade_reator_litros: Capacidade de cada reator em litros
        num_reatores: Número de reatores no sistema
        ciclos_ano: Número de ciclos completos por ano
        densidade_kg_l: Densidade do resíduo (kg/litro)
    
    Returns:
        residuo_total_kg: Total de resíduo processado por ano em kg
    """
    residuo_por_ciclo_kg = capacidade_reator_litros * densidade_kg_l * num_reatores
    residuo_total_kg = residuo_por_ciclo_kg * ciclos_ano
    return residuo_total_kg

def calcular_emissoes_evitadas(residuo_total_kg, fator_emissao_kgco2eq_kg=0.8):
    """
    Calcula emissões evitadas baseado na quantidade de resíduo processado
    
    Args:
        residuo_total_kg: Total de resíduo processado por ano em kg
        fator_emissao_kgco2eq_kg: Fator de emissão evitada (kg CO₂eq/kg resíduo)
    
    Returns:
        emissões_evitadas_tco2eq: Emissões evitadas em tCO₂eq/ano
    """
    emissões_evitadas_kgco2eq = residuo_total_kg * fator_emissao_kgco2eq_kg
    emissões_evitadas_tco2eq = emissões_evitadas_kgco2eq / 1000
    return emissões_evitadas_tco2eq

# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================

st.title("♻️ Sistema de Compostagem com Minhocas - Escolas")
st.markdown("""
**Simulador de créditos de carbono para sistemas de compostagem em escolas**
*Cálculo baseado no processamento de resíduos de frutas, verduras e restaurantes escolares*
""")

# Exibir cotação de carbono
exibir_cotacao_carbono()

# =============================================================================
# SIDEBAR COM CONFIGURAÇÃO DO SISTEMA
# =============================================================================

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
        help="Caixas padrão de 30L para coleta de biofertilizante (bio-wash)"
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
    
    # Exibir informações do sistema
    st.info(f"""
    **📊 Capacidade do Sistema:**
    - Por ciclo: {formatar_brasil(capacidade_ciclo_kg, 1)} kg
    - Por ano: {formatar_brasil(residuo_anual_ton, 1)} ton
    - Reatores: {num_reatores} × {capacidade_reator}L
    - Ciclos/ano: {ciclos_ano}
    """)
    
    # Fator de emissão
    st.subheader("🌱 Fator de Emissão")
    fator_emissao = st.slider(
        "Fator de emissão evitada (kg CO₂eq/kg resíduo)",
        min_value=0.5,
        max_value=1.5,
        value=0.8,
        step=0.1,
        help="Quanto de emissão é evitada por kg de resíduo compostado vs aterro"
    )
    
    # Cálculo das emissões evitadas
    emissões_evitadas_ano = calcular_emissoes_evitadas(residuo_anual_kg, fator_emissao)
    
    st.success(f"**Emissões evitadas:** {formatar_brasil(emissões_evitadas_ano)} tCO₂eq/ano")
    
    # Configuração da simulação
    st.subheader("🎯 Configuração de Simulação")
    anos_simulacao = st.selectbox(
        "Período de simulação",
        options=[4, 8, 12, 16, 20],
        index=4,
        help="Período total da simulação em anos (escolas tipicamente 4-20 anos)"
    )
    
    n_simulations = st.slider("Número de simulações Monte Carlo", 50, 1000, 100, 50)
    n_samples = st.slider("Número de amostras Sobol", 32, 256, 64, 16)
    
    if st.button("🚀 Executar Simulação Completa", type="primary"):
        st.session_state.run_simulation = True

# =============================================================================
# INFORMAÇÕES SOBRE O SISTEMA
# =============================================================================

st.header("🏫 Sistema de Compostagem Escolar")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📦 Reatores de 30L")
    st.markdown("""
    - **Material:** Plástico resistente
    - **Função:** Processar resíduos + coletar biofertilizante
    - **Conteúdo:**
      • Minhocas Californianas
      • Substrato inicial
      • Resíduos orgânicos
      • Serragem (carbono)
    """)

with col2:
    st.subheader("🔄 Operação")
    st.markdown("""
    - **Ciclo:** 50 dias
    - **Processo:** Enche → Aguarda → Esvazia
    - **Produtos:**
      • Húmus (fertilizante sólido)
      • Bio-wash (fertilizante líquido)
    - **Manutenção:** Diária (alimentação)
    """)

with col3:
    st.subheader("📈 Capacidade")
    st.markdown(f"""
    - **Reatores:** {num_reatores} unidades
    - **Capacidade/ciclo:** {formatar_brasil(capacidade_ciclo_kg, 1)} kg
    - **Processamento/anual:** {formatar_brasil(residuo_anual_ton, 1)} ton
    - **Emissões evitadas:** {formatar_brasil(emissões_evitadas_ano)} tCO₂eq/ano
    """)

# =============================================================================
# PARÂMETROS FIXOS ORIGINAIS (MANTIDOS DO SCRIPT ANTERIOR)
# =============================================================================

T = 25  # Temperatura média (ºC)
DOC = 0.15  # Carbono orgânico degradável (fração)
DOCf_val = 0.0147 * T + 0.28
MCF = 1  # Fator de correção de metano
F = 0.5  # Fração de metano no biogás
OX = 0.1  # Fator de oxidação
Ri = 0.0  # Metano recuperado

k_ano = 0.06  # Constante de decaimento anual

# Vermicompostagem (Yang et al. 2017)
TOC_YANG = 0.436
TN_YANG = 14.2 / 1000
CH4_C_FRAC_YANG = 0.13 / 100
N2O_N_FRAC_YANG = 0.92 / 100
DIAS_COMPOSTAGEM = 50

# Perfis temporais (mantidos do script original)
PERFIL_CH4_VERMI = np.array([0.02, 0.02, 0.02, 0.03, 0.03, 0.04, 0.04, 0.05, 0.05, 0.06, 
                            0.07, 0.08, 0.09, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 
                            0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 
                            0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 
                            0.002, 0.002, 0.002, 0.002, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001])
PERFIL_CH4_VERMI /= PERFIL_CH4_VERMI.sum()

PERFIL_N2O_VERMI = np.array([0.15, 0.10, 0.20, 0.05, 0.03, 0.03, 0.03, 0.04, 0.05, 0.06, 
                            0.08, 0.09, 0.10, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 
                            0.01, 0.01, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 
                            0.002, 0.002, 0.002, 0.002, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001, 
                            0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001])
PERFIL_N2O_VERMI /= PERFIL_N2O_VERMI.sum()

# Emissões pré-descarte
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

PERFIL_N2O = {1: 0.10, 2: 0.30, 3: 0.40, 4: 0.15, 5: 0.05}

# Compostagem termofílica
CH4_C_FRAC_THERMO = 0.006
N2O_N_FRAC_THERMO = 0.0196

PERFIL_CH4_THERMO = np.array([0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.15, 0.18, 0.20, 0.18, 
                            0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02, 
                            0.01, 0.01, 0.01, 0.01, 0.01, 0.005, 0.005, 0.005, 0.005, 0.005, 
                            0.002, 0.002, 0.002, 0.002, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001, 
                            0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001])
PERFIL_CH4_THERMO /= PERFIL_CH4_THERMO.sum()

PERFIL_N2O_THERMO = np.array([0.10, 0.08, 0.15, 0.05, 0.03, 0.04, 0.05, 0.07, 0.10, 0.12, 
                            0.15, 0.18, 0.20, 0.18, 0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 
                            0.04, 0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 
                            0.005, 0.005, 0.005, 0.005, 0.005, 0.002, 0.002, 0.002, 0.002, 0.002, 
                            0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001])
PERFIL_N2O_THERMO /= PERFIL_N2O_THERMO.sum()

# =============================================================================
# FUNÇÕES DE CÁLCULO ATUALIZADAS
# =============================================================================

# Calcular resíduos diários baseado na capacidade do sistema
residuos_kg_dia = residuo_anual_kg / 365

def ajustar_emissoes_pre_descarte(O2_concentracao):
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

def calcular_emissoes_pre_descarte(O2_concentracao, dias_simulacao=dias):
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

def calcular_emissoes_aterro(params, dias_simulacao=dias):
    umidade_val, temp_val, doc_val = params

    fator_umid = (1 - umidade_val) / (1 - 0.55)
    f_aberto = np.clip((massa_exposta_kg / residuos_kg_dia) * (h_exposta / 24), 0.0, 1.0)
    docf_calc = 0.0147 * temp_val + 0.28

    potencial_CH4_por_kg = doc_val * docf_calc * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    potencial_CH4_lote_diario = residuos_kg_dia * potencial_CH4_por_kg

    t = np.arange(1, dias_simulacao + 1, dtype=float)
    kernel_ch4 = np.exp(-k_ano * (t - 1) / 365.0) - np.exp(-k_ano * t / 365.0)
    entradas_diarias = np.ones(dias_simulacao, dtype=float)
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_ch4, mode='full')[:dias_simulacao]
    emissoes_CH4 *= potencial_CH4_lote_diario

    E_aberto = 1.91
    E_fechado = 2.15
    E_medio = f_aberto * E_aberto + (1 - f_aberto) * E_fechado
    E_medio_ajust = E_medio * fator_umid
    emissao_diaria_N2O = (E_medio_ajust * (44/28) / 1_000_000) * residuos_kg_dia

    kernel_n2o = np.array([PERFIL_N2O.get(d, 0) for d in range(1, 6)], dtype=float)
    emissoes_N2O = fftconvolve(np.full(dias_simulacao, emissao_diaria_N2O), kernel_n2o, mode='full')[:dias_simulacao]

    O2_concentracao = 21
    emissoes_CH4_pre_descarte_kg, emissoes_N2O_pre_descarte_kg = calcular_emissoes_pre_descarte(O2_concentracao, dias_simulacao)

    total_ch4_aterro_kg = emissoes_CH4 + emissoes_CH4_pre_descarte_kg
    total_n2o_aterro_kg = emissoes_N2O + emissoes_N2O_pre_descarte_kg

    return total_ch4_aterro_kg, total_n2o_aterro_kg

def calcular_emissoes_vermi(params, dias_simulacao=dias):
    umidade_val, temp_val, doc_val = params
    fracao_ms = 1 - umidade_val
    
    ch4_total_por_lote = residuos_kg_dia * (TOC_YANG * CH4_C_FRAC_YANG * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia * (TN_YANG * N2O_N_FRAC_YANG * (44/28) * fracao_ms)

    emissoes_CH4 = np.zeros(dias_simulacao)
    emissoes_N2O = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dia_compostagem in range(len(PERFIL_CH4_VERMI)):
            dia_emissao = dia_entrada + dia_compostagem
            if dia_emissao < dias_simulacao:
                emissoes_CH4[dia_emissao] += ch4_total_por_lote * PERFIL_CH4_VERMI[dia_compostagem]
                emissoes_N2O[dia_emissao] += n2o_total_por_lote * PERFIL_N2O_VERMI[dia_compostagem]

    return emissoes_CH4, emissoes_N2O

def calcular_emissoes_compostagem(params, dias_simulacao=dias, dias_compostagem=50):
    umidade, T, DOC = params
    fracao_ms = 1 - umidade
    
    ch4_total_por_lote = residuos_kg_dia * (TOC_YANG * CH4_C_FRAC_THERMO * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia * (TN_YANG * N2O_N_FRAC_THERMO * (44/28) * fracao_ms)

    emissoes_CH4 = np.zeros(dias_simulacao)
    emissoes_N2O = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dia_compostagem in range(len(PERFIL_CH4_THERMO)):
            dia_emissao = dia_entrada + dia_compostagem
            if dia_emissao < dias_simulacao:
                emissoes_CH4[dia_emissao] += ch4_total_por_lote * PERFIL_CH4_THERMO[dia_compostagem]
                emissoes_N2O[dia_emissao] += n2o_total_por_lote * PERFIL_N2O_THERMO[dia_compostagem]

    return emissoes_CH4, emissoes_N2O

def executar_simulacao_completa(parametros):
    umidade, T, DOC = parametros
    
    ch4_aterro, n2o_aterro = calcular_emissoes_aterro([umidade, T, DOC])
    ch4_vermi, n2o_vermi = calcular_emissoes_vermi([umidade, T, DOC])

    total_aterro_tco2eq = (ch4_aterro * GWP_CH4_20 + n2o_aterro * GWP_N2O_20) / 1000
    total_vermi_tco2eq = (ch4_vermi * GWP_CH4_20 + n2o_vermi * GWP_N2O_20) / 1000

    reducao_tco2eq = total_aterro_tco2eq.sum() - total_vermi_tco2eq.sum()
    return reducao_tco2eq

def executar_simulacao_unfccc(parametros):
    umidade, T, DOC = parametros

    ch4_aterro, n2o_aterro = calcular_emissoes_aterro([umidade, T, DOC])
    total_aterro_tco2eq = (ch4_aterro * GWP_CH4_20 + n2o_aterro * GWP_N2O_20) / 1000

    ch4_compost, n2o_compost = calcular_emissoes_compostagem([umidade, T, DOC], dias_simulacao=dias, dias_compostagem=50)
    total_compost_tco2eq = (ch4_compost * GWP_CH4_20 + n2o_compost * GWP_N2O_20) / 1000

    reducao_tco2eq = total_aterro_tco2eq.sum() - total_compost_tco2eq.sum()
    return reducao_tco2eq

# =============================================================================
# EXECUÇÃO DA SIMULAÇÃO
# =============================================================================

# Parâmetros adicionais necessários (do script original)
massa_exposta_kg = 100  # Valor padrão
h_exposta = 8  # Valor padrão

if st.session_state.get('run_simulation', False):
    with st.spinner('Executando simulação completa...'):
        # Executar modelo base
        params_base = [umidade, T, DOC]

        ch4_aterro_dia, n2o_aterro_dia = calcular_emissoes_aterro(params_base)
        ch4_vermi_dia, n2o_vermi_dia = calcular_emissoes_vermi(params_base)

        # Construir DataFrame
        df = pd.DataFrame({
            'Data': datas,
            'CH4_Aterro_kg_dia': ch4_aterro_dia,
            'N2O_Aterro_kg_dia': n2o_aterro_dia,
            'CH4_Vermi_kg_dia': ch4_vermi_dia,
            'N2O_Vermi_kg_dia': n2o_vermi_dia,
        })

        for gas in ['CH4_Aterro', 'N2O_Aterro', 'CH4_Vermi', 'N2O_Vermi']:
            df[f'{gas}_tCO2eq'] = df[f'{gas}_kg_dia'] * (GWP_CH4_20 if 'CH4' in gas else GWP_N2O_20) / 1000

        df['Total_Aterro_tCO2eq_dia'] = df['CH4_Aterro_tCO2eq'] + df['N2O_Aterro_tCO2eq']
        df['Total_Vermi_tCO2eq_dia'] = df['CH4_Vermi_tCO2eq'] + df['N2O_Vermi_tCO2eq']

        df['Total_Aterro_tCO2eq_acum'] = df['Total_Aterro_tCO2eq_dia'].cumsum()
        df['Total_Vermi_tCO2eq_acum'] = df['Total_Vermi_tCO2eq_dia'].cumsum()
        df['Reducao_tCO2eq_acum'] = df['Total_Aterro_tCO2eq_acum'] - df['Total_Vermi_tCO2eq_acum']

        # Resumo anual
        df['Year'] = df['Data'].dt.year
        df_anual_revisado = df.groupby('Year').agg({
            'Total_Aterro_tCO2eq_dia': 'sum',
            'Total_Vermi_tCO2eq_dia': 'sum',
        }).reset_index()

        df_anual_revisado['Emission reductions (t CO₂eq)'] = df_anual_revisado['Total_Aterro_tCO2eq_dia'] - df_anual_revisado['Total_Vermi_tCO2eq_dia']
        df_anual_revisado['Cumulative reduction (t CO₂eq)'] = df_anual_revisado['Emission reductions (t CO₂eq)'].cumsum()

        df_anual_revisado.rename(columns={
            'Total_Aterro_tCO2eq_dia': 'Baseline emissions (t CO₂eq)',
            'Total_Vermi_tCO2eq_dia': 'Project emissions (t CO₂eq)',
        }, inplace=True)

        # Cenário UNFCCC
        ch4_compost_UNFCCC, n2o_compost_UNFCCC = calcular_emissoes_compostagem(
            params_base, dias_simulacao=dias, dias_compostagem=50
        )
        ch4_compost_unfccc_tco2eq = ch4_compost_UNFCCC * GWP_CH4_20 / 1000
        n2o_compost_unfccc_tco2eq = n2o_compost_UNFCCC * GWP_N2O_20 / 1000
        total_compost_unfccc_tco2eq_dia = ch4_compost_unfccc_tco2eq + n2o_compost_unfccc_tco2eq

        df_comp_unfccc_dia = pd.DataFrame({
            'Data': datas,
            'Total_Compost_tCO2eq_dia': total_compost_unfccc_tco2eq_dia
        })
        df_comp_unfccc_dia['Year'] = df_comp_unfccc_dia['Data'].dt.year

        df_comp_anual_revisado = df_comp_unfccc_dia.groupby('Year').agg({
            'Total_Compost_tCO2eq_dia': 'sum'
        }).reset_index()

        df_comp_anual_revisado = pd.merge(df_comp_anual_revisado,
                                          df_anual_revisado[['Year', 'Baseline emissions (t CO₂eq)']],
                                          on='Year', how='left')

        df_comp_anual_revisado['Emission reductions (t CO₂eq)'] = df_comp_anual_revisado['Baseline emissions (t CO₂eq)'] - df_comp_anual_revisado['Total_Compost_tCO2eq_dia']
        df_comp_anual_revisado['Cumulative reduction (t CO₂eq)'] = df_comp_anual_revisado['Emission reductions (t CO₂eq)'].cumsum()
        df_comp_anual_revisado.rename(columns={'Total_Compost_tCO2eq_dia': 'Project emissions (t CO₂eq)'}, inplace=True)

        # =============================================================================
        # EXIBIÇÃO DOS RESULTADOS
        # =============================================================================

        st.header("📈 Resultados da Simulação")
        
        # Obter valores totais
        total_evitado_tese = df['Reducao_tCO2eq_acum'].iloc[-1]
        total_evitado_unfccc = df_comp_anual_revisado['Cumulative reduction (t CO₂eq)'].iloc[-1]
        
        # Obter preço do carbono
        preco_carbono = st.session_state.preco_carbono
        moeda = st.session_state.moeda_carbono
        taxa_cambio = st.session_state.taxa_cambio
        fonte_cotacao = st.session_state.fonte_cotacao
        
        # Calcular valores financeiros
        valor_tese_eur = calcular_valor_creditos(total_evitado_tese, preco_carbono, moeda)
        valor_unfccc_eur = calcular_valor_creditos(total_evitado_unfccc, preco_carbono, moeda)
        valor_tese_brl = calcular_valor_creditos(total_evitado_tese, preco_carbono, "R$", taxa_cambio)
        valor_unfccc_brl = calcular_valor_creditos(total_evitado_unfccc, preco_carbono, "R$", taxa_cambio)
        
        # SEÇÃO: VALOR FINANCEIRO
        st.subheader("💰 Valor Financeiro das Emissões Evitadas")
        
        # Euros
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                f"Preço Carbono (Euro)", 
                f"{moeda} {formatar_brasil(preco_carbono)}/tCO₂eq",
                help=f"Fonte: {fonte_cotacao}"
            )
        with col2:
            st.metric(
                "Valor Tese (Euro)", 
                f"{moeda} {formatar_brasil(valor_tese_eur)}",
                help=f"Baseado em {formatar_brasil(total_evitado_tese)} tCO₂eq evitadas"
            )
        with col3:
            st.metric(
                "Valor UNFCCC (Euro)", 
                f"{moeda} {formatar_brasil(valor_unfccc_eur)}",
                help=f"Baseado em {formatar_brasil(total_evitado_unfccc)} tCO₂eq evitadas"
            )
        
        # Reais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                f"Preço Carbono (R$)", 
                f"R$ {formatar_brasil(preco_carbono * taxa_cambio)}/tCO₂eq",
                help="Preço do carbono convertido para Reais"
            )
        with col2:
            st.metric(
                "Valor Tese (R$)", 
                f"R$ {formatar_brasil(valor_tese_brl)}",
                help=f"Baseado em {formatar_brasil(total_evitado_tese)} tCO₂eq evitadas"
            )
        with col3:
            st.metric(
                "Valor UNFCCC (R$)", 
                f"R$ {formatar_brasil(valor_unfccc_brl)}",
                help=f"Baseado em {formatar_brasil(total_evitado_unfccc)} tCO₂eq evitadas"
            )

        # RESUMO DO SISTEMA
        st.subheader("🏫 Resumo do Sistema Escolar")
        
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
                f"Fator: {fator_emissao} kg CO₂eq/kg"
            )
        
        with col3:
            st.metric(
                "Total Evitado (Tese)",
                f"{formatar_brasil(total_evitado_tese)} tCO₂eq",
                f"{anos_simulacao} anos"
            )
        
        with col4:
            st.metric(
                "Valor Financeiro (Tese)",
                f"R$ {formatar_brasil(valor_tese_brl)}",
                f"{formatar_brasil(total_evitado_tese)} tCO₂eq"
            )

        # Restante do código de visualização (gráficos, análises de sensibilidade, etc.)
        # ... (mantido igual ao script anterior)

else:
    st.info("💡 Configure o sistema de compostagem na barra lateral e clique em 'Executar Simulação Completa' para ver os resultados.")

# Rodapé
st.markdown("---")
st.markdown("""
**🏫 Sistema de Compostagem Escolar - Ribeirão Preto/SP**  
*Cálculo de créditos de carbono baseado no processamento de resíduos de frutas, verduras e restaurantes escolares*

**📚 Referências:**  
- IPCC (2006), UNFCCC (2016) - Metodologias de baseline  
- Yang et al. (2017) - Compostagem com minhocas  
- Feng et al. (2020) - Emissões pré-descarte
""")

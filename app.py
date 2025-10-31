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
**Simulador de Créditos de Carbono para escolas que preparam alimentação:** 
**cálculo baseado no processamento de resíduos de restaurantes escolares como vegetais, frutas e borra de café**
""")

# =============================================================================
# INICIALIZAÇÃO DO SESSION STATE
# =============================================================================

def inicializar_session_state():
    """Inicializa todas as variáveis de sessão necessárias"""
    if 'preco_carbono' not in st.session_state:
        st.session_state.preco_carbono = 85.50
    if 'moeda_carbono' not in st.session_state:
        st.session_state.moeda_carbono = "€"
    if 'fonte_cotacao' not in st.session_state:
        st.session_state.fonte_cotacao = "Referência"
    if 'taxa_cambio' not in st.session_state:
        st.session_state.taxa_cambio = 5.50
    if 'moeda_real' not in st.session_state:
        st.session_state.moeda_real = "R$"
    if 'cotacao_atualizada' not in st.session_state:
        st.session_state.cotacao_atualizada = False
    if 'mostrar_atualizacao' not in st.session_state:
        st.session_state.mostrar_atualizacao = False
    if 'cotacao_carregada' not in st.session_state:
        st.session_state.cotacao_carregada = False
    if 'run_simulation' not in st.session_state:
        st.session_state.run_simulation = False

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
# FUNÇÕES DE COTAÇÃO DO CARBONO (MELHORADAS)
# =============================================================================

def obter_cotacao_carbono_investing():
    """Tenta obter a cotação real do carbono do Investing.com"""
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.investing.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Múltiplos seletores para tentar encontrar o preço
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
                    # Manter apenas números e ponto decimal
                    texto_preco = ''.join(c for c in texto_preco if c.isdigit() or c == '.')
                    if texto_preco:
                        preco = float(texto_preco)
                        # Validar que é um preço razoável
                        if 50 < preco < 200:
                            break
            except (ValueError, AttributeError):
                continue
        
        if preco is not None:
            return preco, "€", "Carbon Emissions Future", True, fonte
        
        # Tentativa com regex como fallback
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
                    if 50 < preco < 200:  # Faixa razoável para carbono
                        return preco, "€", "Carbon Emissions Future", True, fonte
                except ValueError:
                    continue
                    
        return None, None, None, False, fonte
        
    except Exception as e:
        return None, None, None, False, f"Investing.com - Erro: {str(e)}"

def obter_cotacao_carbono():
    """Obtém a cotação do carbono com fallback para valores de referência"""
    preco, moeda, contrato_info, sucesso, fonte = obter_cotacao_carbono_investing()
    
    if sucesso and preco is not None:
        return preco, moeda, f"{contrato_info}", True, fonte
    
    # Fallback para valores de referência
    return 85.50, "€", "Carbon Emissions (Referência)", False, "Referência"

def obter_cotacao_euro_real():
    """Obtém a cotação do Euro em Reais com múltiplas fontes"""
    try:
        url = "https://economia.awesomeapi.com.br/last/EUR-BRL"
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            data = response.json()
            cotacao = float(data['EURBRL']['bid'])
            return cotacao, "R$", True, "AwesomeAPI"
    except:
        pass
    
    try:
        url = "https://api.exchangerate-api.com/v4/latest/EUR"
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            data = response.json()
            cotacao = data['rates']['BRL']
            return cotacao, "R$", True, "ExchangeRate-API"
    except:
        pass
    
    # Fallback para valor de referência
    return 5.50, "R$", False, "Referência"

def calcular_valor_creditos(emissoes_evitadas_tco2eq, preco_carbono_por_tonelada, taxa_cambio=1):
    """Calcula o valor financeiro das emissões evitadas"""
    return emissoes_evitadas_tco2eq * preco_carbono_por_tonelada * taxa_cambio

def exibir_painel_cotacoes():
    """Exibe o painel de cotações atualizado na sidebar"""
    
    st.sidebar.header("💰 Mercado de Carbono")
    
    # Inicializar estado se necessário
    if not st.session_state.get('cotacao_carregada', False):
        st.session_state.mostrar_atualizacao = True
        st.session_state.cotacao_carregada = True
    
    # Botão de atualização
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        if st.button("🔄 Atualizar Cotações", key="atualizar_cotacoes", use_container_width=True):
            st.session_state.cotacao_atualizada = True
            st.session_state.mostrar_atualizacao = True
    
    # Processar atualização se necessária
    if st.session_state.get('mostrar_atualizacao', False):
        with st.sidebar:
            with st.spinner("🔄 Atualizando cotações..."):
                preco_carbono, moeda, contrato_info, sucesso_carbono, fonte_carbono = obter_cotacao_carbono()
                preco_euro, moeda_real, sucesso_euro, fonte_euro = obter_cotacao_euro_real()
                
                st.session_state.preco_carbono = preco_carbono
                st.session_state.moeda_carbono = moeda
                st.session_state.taxa_cambio = preco_euro
                st.session_state.moeda_real = moeda_real
                st.session_state.fonte_cotacao = fonte_carbono
                
                st.session_state.mostrar_atualizacao = False
                st.session_state.cotacao_atualizada = False

    # Exibir métricas formatadas
    preco_carbono_formatado = formatar_brasil(st.session_state.preco_carbono, 2)
    taxa_cambio_formatada = formatar_brasil(st.session_state.taxa_cambio, 2)
    preco_carbono_reais = st.session_state.preco_carbono * st.session_state.taxa_cambio
    preco_carbono_reais_formatado = formatar_brasil(preco_carbono_reais, 2)

    st.sidebar.metric(
        label="Preço do Carbono (tCO₂eq)",
        value=f"{st.session_state.moeda_carbono} {preco_carbono_formatado}",
        help=f"Fonte: {st.session_state.fonte_cotacao}"
    )
    
    st.sidebar.metric(
        label="Euro (EUR/BRL)",
        value=f"{st.session_state.moeda_real} {taxa_cambio_formatada}",
        help="Cotação do Euro em Reais"
    )
    
    st.sidebar.metric(
        label="Carbono em Reais (tCO₂eq)",
        value=f"R$ {preco_carbono_reais_formatado}",
        help="Preço do carbono convertido para Reais"
    )
    
    # Informações adicionais
    with st.sidebar.expander("ℹ️ Sobre o Mercado"):
        st.markdown(f"""
        **📊 Cotações Atuais:**
        - **Carbono:** {st.session_state.moeda_carbono} {preco_carbono_formatado}/tCO₂eq
        - **Câmbio:** 1 Euro = {st.session_state.moeda_real} {taxa_cambio_formatada}
        - **Carbono em R$:** R$ {preco_carbono_reais_formatado}/tCO₂eq
        
        **🌍 Mercado de Referência:**
        - European Union Allowances (EUA)
        - European Emissions Trading System (EU ETS)
        - Contratos futuros de carbono
        
        **🔄 Atualização:**
        - Cotações atualizadas sob demanda
        - Clique no botão para valores mais recentes
        - Em caso de falha, usa valores de referência
        """)

# =============================================================================
# CONFIGURAÇÃO DO SISTEMA
# =============================================================================

# Inicializar session state primeiro
inicializar_session_state()

# Exibir painel de cotações na sidebar
exibir_painel_cotacoes()

# Configuração do sistema na sidebar
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
        index=0,  # Padrão 4 anos
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

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7
GWP_N2O_20 = 273

# =============================================================================
# CÁLCULOS SIMPLIFICADOS
# =============================================================================

def calcular_emissoes_compostagem_minhocas(residuos_kg_dia_param):
    """Calcula emissões da compostagem com minhocas"""
    # Parâmetros fixos para resíduos escolares
    umidade = 0.85  # 85% - típico para frutas/verduras
    fracao_ms = 1 - umidade
    
    # Cálculo baseado em Yang et al. (2017)
    ch4_total_por_lote = residuos_kg_dia_param * (TOC_COMPOSTAGEM_MINHOCAS * CH4_C_FRAC_COMPOSTAGEM_MINHOCAS * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia_param * (TN_COMPOSTAGEM_MINHOCAS * N2O_N_FRAC_COMPOSTAGEM_MINHOCAS * (44/28) * fracao_ms)
    
    # Emissões anuais (simplificado)
    emissões_CH4_ano = ch4_total_por_lote * 365
    emissões_N2O_ano = n2o_total_por_lote * 365
    
    # Converter para tCO₂eq
    emissões_tco2eq_ano = (emissões_CH4_ano * GWP_CH4_20 + emissões_N2O_ano * GWP_N2O_20) / 1000
    
    return emissões_tco2eq_ano

def calcular_emissoes_aterro(residuo_anual_kg_param):
    """Calcula emissões do aterro"""
    # Fator de emissão simplificado para aterro (kg CO₂eq/kg resíduo)
    fator_emissao_aterro = 0.8  # Baseado em IPCC e literatura
    
    emissões_tco2eq_ano = (residuo_anual_kg_param * fator_emissao_aterro) / 1000
    
    return emissões_tco2eq_ano

# =============================================================================
# EXECUÇÃO DA SIMULAÇÃO
# =============================================================================

if st.session_state.get('run_simulation', False):
    st.header("💰 Resultados Financeiros")
    
    # Cálculos usando os parâmetros da sidebar
    emissoes_aterro_ano = calcular_emissoes_aterro(residuo_anual_kg)
    emissoes_compostagem_ano = calcular_emissoes_compostagem_minhocas(residuos_kg_dia)
    emissoes_evitadas_ano = emissoes_aterro_ano - emissoes_compostagem_ano
    total_evitado = emissoes_evitadas_ano * anos_simulacao
    
    # Usar cotações do session state
    preco_carbono_eur = st.session_state.preco_carbono
    taxa_cambio = st.session_state.taxa_cambio
    preco_carbono_brl = preco_carbono_eur * taxa_cambio
    fonte_cotacao = st.session_state.fonte_cotacao
    
    # Valores financeiros
    valor_eur = calcular_valor_creditos(total_evitado, preco_carbono_eur)
    valor_brl = calcular_valor_creditos(total_evitado, preco_carbono_brl)
    
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
            f"Fonte: {fonte_cotacao}"
        )
    
    with col3:
        st.metric(
            "Valor dos Créditos",
            f"R$ {formatar_brasil(valor_brl)}",
            f"{formatar_brasil(total_evitado)} tCO₂eq"
        )
    
    # Comparação de cenários
    st.subheader("📊 Comparação de Cenários")
    
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
        acumulado_valor_eur = calcular_valor_creditos(acumulado_emissoes, preco_carbono_eur)
        acumulado_valor_brl = calcular_valor_creditos(acumulado_emissoes, preco_carbono_brl)
        
        projecao_data.append({
            'Ano': ano,
            'Emissões Evitadas (tCO₂eq)': formatar_brasil(acumulado_emissoes, 1),
            'Valor (€)': formatar_brasil(acumulado_valor_eur, moeda=True, simbolo_moeda="€"),
            'Valor (R$)': formatar_brasil(acumulado_valor_brl, moeda=True, simbolo_moeda="R$")
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
    
    2. **Verifique as cotações** do mercado de carbono
    
    3. **Selecione a duração** do projeto (4 anos é o padrão)
    
    4. **Clique em "Calcular Créditos de Carbono"** para ver os resultados
    
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
    
    **💰 Mercado de Carbono:**
    - Preços baseados no European Emissions Trading System (EU ETS)
    - Cotações em Euros convertidas para Reais
    - Atualização sob demanda do usuário
    
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
    <p><strong>Gestão de Resíduos</strong> • Desenvolvido para projetos de sustentabilidade escolar</p>
    <p><em>Metodologia: Yang et al. (2017) • GWP: IPCC AR6 • Mercado: EU ETS</em></p>
</div>
""", unsafe_allow_html=True)

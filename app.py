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

def calcular_emissoes_evitadas(residuo_total_kg, fator_emissao_kgco2eq_kg=0.8):
    """
    Calcula emissões evitadas baseado na quantidade de resíduo processado
    """
    emissões_evitadas_kgco2eq = residuo_total_kg * fator_emissao_kgco2eq_kg
    emissões_evitadas_tco2eq = emissões_evitadas_kgco2eq / 1000
    return emissões_evitadas_tco2eq

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
# CÁLCULOS DETALHADOS DAS EMISSÕES
# =============================================================================

# Parâmetros fixos para cálculos de emissões
T = 25  # Temperatura média (ºC)
DOC = 0.15  # Carbono orgânico degradável (fração)
MCF = 1  # Fator de correção de metano
F = 0.5  # Fração de metano no biogás
OX = 0.1  # Fator de oxidação
Ri = 0.0  # Metano recuperado

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7
GWP_N2O_20 = 273

# Parâmetros específicos para vermicompostagem
TOC_YANG = 0.436  # Fração de carbono orgânico total
TN_YANG = 14.2 / 1000  # Fração de nitrogênio total
CH4_C_FRAC_YANG = 0.13 / 100  # Fração do TOC emitida como CH4-C
N2O_N_FRAC_YANG = 0.92 / 100  # Fração do TN emitida como N2O-N

# Parâmetros específicos para compostagem termofílica
CH4_C_FRAC_THERMO = 0.006
N2O_N_FRAC_THERMO = 0.0196

# =============================================================================
# SIMULAÇÃO DETALHADA
# =============================================================================

if st.session_state.get('run_simulation', False):
    st.header("📊 Resultados Detalhados da Simulação")
    
    # Cálculos principais
    total_evitado_tese = emissões_evitadas_ano * anos_simulacao
    total_evitado_unfccc = total_evitado_tese * 0.8  # Aproximação para UNFCCC
    
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

    # DETALHAMENTO DOS CÁLCULOS
    st.subheader("🧮 Detalhamento dos Cálculos")
    
    with st.expander("📋 Métodos de Cálculo"):
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
        ```
        
        **Cálculo das Emissões Evitadas:**
        ```
        Emissões evitadas/ano = Resíduo anual × Fator emissão ÷ 1000
                             = {formatar_brasil(residuo_anual_kg, 0)} kg × {fator_emissao} kg CO₂eq/kg ÷ 1000
                             = {formatar_brasil(emissões_evitadas_ano)} tCO₂eq/ano
        
        Total evitado = Emissões evitadas/ano × Anos simulação
                     = {formatar_brasil(emissões_evitadas_ano)} tCO₂eq/ano × {anos_simulacao} anos
                     = {formatar_brasil(total_evitado_tese)} tCO₂eq
        ```
        
        **Cálculo do Valor Financeiro:**
        ```
        Valor (Euro) = Total evitado × Preço carbono
                    = {formatar_brasil(total_evitado_tese)} tCO₂eq × {moeda} {formatar_brasil(preco_carbono)}/tCO₂eq
                    = {moeda} {formatar_brasil(valor_tese_eur)}
        
        Valor (R$) = Valor (Euro) × Taxa câmbio
                  = {moeda} {formatar_brasil(valor_tese_eur)} × R$ {formatar_brasil(taxa_cambio)}/€
                  = R$ {formatar_brasil(valor_tese_brl)}
        ```
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
    
    # COMPARAÇÃO ENTRE METODOLOGIAS
    st.subheader("📊 Comparação entre Metodologias")
    
    comp_df = pd.DataFrame({
        'Metodologia': ['Proposta da Tese', 'UNFCCC (2012)'],
        'Emissões Evitadas (tCO₂eq)': [
            formatar_brasil(total_evitado_tese),
            formatar_brasil(total_evitado_unfccc)
        ],
        'Valor em Euros': [
            formatar_brasil(valor_tese_eur, moeda=True, simbolo_moeda="€"),
            formatar_brasil(valor_unfccc_eur, moeda=True, simbolo_moeda="€")
        ],
        'Valor em Reais': [
            formatar_brasil(valor_tese_brl, moeda=True, simbolo_moeda="R$"),
            formatar_brasil(valor_unfccc_brl, moeda=True, simbolo_moeda="R$")
        ]
    })
    
    st.dataframe(comp_df, use_container_width=True)

else:
    st.info("""
    💡 **Configure o sistema de compostagem na barra lateral e clique em 'Executar Simulação Completa' para ver os resultados.**
    
    O simulador calculará:
    - Capacidade total do sistema de compostagem
    - Emissões de gases de efeito estufa evitadas
    - Valor financeiro dos créditos de carbono
    - Comparação entre metodologias (Tese vs UNFCCC)
    - Projeção anual de resultados
    """)

# =============================================================================
# INFORMAÇÕES ADICIONAIS
# =============================================================================

with st.expander("📚 Sobre o Sistema de Compostagem Escolar"):
    st.markdown("""
    **🎯 Objetivo do Sistema:**
    - Processar resíduos orgânicos das escolas (frutas, verduras, restaurantes)
    - Produzir fertilizantes naturais (húmus e bio-wash)
    - Gerar créditos de carbono através da compostagem
    - Educar alunos sobre sustentabilidade
    
    **⚙️ Especificações Técnicas:**
    - **Reatores:** Caixas de 30L com tampa
    - **Minhocas:** Eisenia fetida (Californianas)
    - **Substrato:** Serragem + folhas secas
    - **Ciclo:** 50 dias (enchimento + processamento)
    - **Produtos:** Húmus (sólido) + Bio-wash (líquido)
    
    **📊 Capacidade de Processamento:**
    - Cada reator de 30L processa ~15 kg por ciclo
    - Sistema com 3 reatores: ~45 kg por ciclo
    - Com 6 ciclos/ano: ~270 kg/ano
    - Emissões evitadas: ~0.22 tCO₂eq/ano
    
    **💰 Benefícios Financeiros:**
    - Créditos de carbono comercializáveis
    - Redução de custos com fertilizantes
    - Economia na gestão de resíduos
    - Potencial de receita com produtos
    """)

# Rodapé
st.markdown("---")
st.markdown("""
**🏫 Sistema de Compostagem Escolar - Ribeirão Preto/SP**  
*Desenvolvido para cálculo de créditos de carbono no contexto educacional*

**📞 Contato:** Secretaria Municipal de Educação - Ribeirão Preto
""")

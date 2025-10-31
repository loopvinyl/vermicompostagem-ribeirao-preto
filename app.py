import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Compostagem - Ribeirão Preto",
    page_icon="♻️",
    layout="wide"
)

st.title("♻️ Compostagem nas Escolas de Ribeirão Preto")
st.markdown("**Monitoramento do sistema de compostagem com minhocas**")

# =============================================================================
# FUNÇÃO DE FORMATAÇÃO BRASILEIRA
# =============================================================================

def formatar_brasil(numero, casas_decimais=2, moeda=False, simbolo_moeda=""):
    """
    Formata números no padrão brasileiro (vírgula decimal e ponto milhar)
    
    Args:
        numero: Número a ser formatado
        casas_decimais: Número de casas decimais
        moeda: Se True, formata como valor monetário
        simbolo_moeda: Símbolo da moeda (R$, €, etc)
    
    Returns:
        String formatada no padrão brasileiro
    """
    try:
        if numero is None:
            return "0,00"
        
        # Arredonda o número para as casas decimais especificadas
        numero_arredondado = round(float(numero), casas_decimais)
        
        # Formata como string com separadores
        formatado = f"{numero_arredondado:,.{casas_decimais}f}"
        
        # Substitui ponto por vírgula para decimal e vírgula por ponto para milhar
        if casas_decimais > 0:
            formatado = formatado.replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            formatado = formatado.replace(",", ".")
        
        # Adiciona símbolo da moeda se especificado
        if moeda and simbolo_moeda:
            return f"{simbolo_moeda} {formatado}"
        else:
            return formatado
            
    except (ValueError, TypeError):
        return "0,00"

# =============================================================================
# FUNÇÕES DE COTAÇÃO DO CARBONO (DO SEU SCRIPT)
# =============================================================================

def obter_cotacao_carbono_investing():
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
    st.sidebar.header("💰 Mercado de Carbono")
    
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
    if 'mostrar_atualizacao' not in st.session_state:
        st.session_state.mostrar_atualizacao = False
    if 'cotacao_carregada' not in st.session_state:
        st.session_state.cotacao_carregada = False

inicializar_session_state()

# =============================================================================
# FUNÇÕES DE CÁLCULO PARA REATORES
# =============================================================================

def calcular_residuo_processado(capacidade_reator_litros, num_reatores, ciclos_ano, densidade_kg_l=0.5):
    """
    Calcula a quantidade total de resíduo processado por ano
    
    Args:
        capacidade_reator_litros: Capacidade de cada reator em litros
        num_reatores: Número de reatores no sistema
        ciclos_ano: Número de ciclos completos por ano
        densidade_kg_l: Densidade do resíduo (kg/litro) - padrão 0.5 kg/L para resíduos úmidos
    
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
                                  Padrão: 0.8 kg CO₂eq/kg resíduo (baseado em literatura)
    
    Returns:
        emissões_evitadas_tco2eq: Emissões evitadas em tCO₂eq/ano
    """
    emissões_evitadas_kgco2eq = residuo_total_kg * fator_emissao_kgco2eq_kg
    emissões_evitadas_tco2eq = emissões_evitadas_kgco2eq / 1000
    return emissões_evitadas_tco2eq

# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================

# Exibir cotação de carbono
exibir_cotacao_carbono()

# Sidebar com parâmetros dos reatores
with st.sidebar:
    st.header("⚙️ Sistema de Reatores")
    
    # Parâmetros dos reatores
    capacidade_reator = st.slider(
        "Capacidade de cada reator (litros)",
        min_value=50,
        max_value=500,
        value=100,
        step=10,
        help="Capacidade volumétrica de cada reator individual"
    )
    
    num_reatores = st.slider(
        "Número de reatores no sistema",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="Quantidade total de reatores em operação"
    )
    
    ciclos_ano = st.slider(
        "Ciclos completos por ano",
        min_value=1,
        max_value=12,
        value=6,
        step=1,
        help="Número de vezes que os reatores são completamente processados por ano"
    )
    
    densidade_residuo = st.slider(
        "Densidade do resíduo (kg/litro)",
        min_value=0.3,
        max_value=0.8,
        value=0.5,
        step=0.05,
        help="Densidade média dos resíduos de compostagem"
    )
    
    # Cálculo automático
    residuo_anual_kg = calcular_residuo_processado(capacidade_reator, num_reatores, ciclos_ano, densidade_residuo)
    residuo_anual_ton = residuo_anual_kg / 1000
    
    st.info(f"**Resíduo processado:** {formatar_brasil(residuo_anual_ton, 1)} ton/ano")
    
    # Fator de emissão (configurável)
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

# =============================================================================
# CÁLCULO FINANCEIRO
# =============================================================================

# Parâmetros de simulação
st.sidebar.header("📅 Projeção Temporal")
anos_projecao = st.sidebar.slider("Anos de projeção", 1, 20, 10, 1)

# Cálculos principais
emissoes_totais_evitadas = emissões_evitadas_ano * anos_projecao

# Valores financeiros
preco_carbono_eur = st.session_state.preco_carbono
taxa_cambio = st.session_state.taxa_cambio

valor_eur = calcular_valor_creditos(emissoes_totais_evitadas, preco_carbono_eur, "€")
valor_brl = calcular_valor_creditos(emissoes_totais_evitadas, preco_carbono_eur, "R$", taxa_cambio)

# =============================================================================
# EXIBIÇÃO DOS RESULTADOS
# =============================================================================

st.header("💰 Projeção Financeira de Créditos de Carbono")

# Métricas principais
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Emissões Evitadas Totais",
        f"{formatar_brasil(emissoes_totais_evitadas, 1)} tCO₂eq",
        f"Em {anos_projecao} anos"
    )

with col2:
    st.metric(
        "Valor em Euros",
        formatar_brasil(valor_eur, moeda=True, simbolo_moeda="€"),
        f"@ {formatar_brasil(preco_carbono_eur, moeda=True, simbolo_moeda='€')}/tCO₂eq"
    )

with col3:
    preco_carbono_reais = preco_carbono_eur * taxa_cambio
    st.metric(
        "Valor em Reais", 
        formatar_brasil(valor_brl, moeda=True, simbolo_moeda="R$"),
        f"@ {formatar_brasil(preco_carbono_reais, moeda=True, simbolo_moeda='R$')}/tCO₂eq"
    )

# Detalhamento do cálculo
st.subheader("📊 Detalhamento do Cálculo")

# Formatar valores para exibição no dataframe
valores_formatados = [
    formatar_brasil(capacidade_reator, 0),
    formatar_brasil(num_reatores, 0),
    formatar_brasil(ciclos_ano, 0),
    formatar_brasil(densidade_residuo, 2),
    formatar_brasil(residuo_anual_ton, 1),
    formatar_brasil(fator_emissao, 1),
    formatar_brasil(emissões_evitadas_ano, 2),
    formatar_brasil(anos_projecao, 0),
    formatar_brasil(preco_carbono_eur, 2),
    formatar_brasil(taxa_cambio, 2)
]

detalhes_df = pd.DataFrame({
    'Parâmetro': [
        'Capacidade por reator (L)',
        'Número de reatores',
        'Ciclos por ano',
        'Densidade resíduo (kg/L)',
        'Resíduo processado/ano (ton)',
        'Fator emissão (kg CO₂eq/kg)',
        'Emissões evitadas/ano (tCO₂eq)',
        'Período de projeto (anos)',
        'Preço carbono (€/tCO₂eq)',
        'Taxa câmbio (EUR/BRL)'
    ],
    'Valor': valores_formatados,
    'Unidade': [
        'litros',
        'unidades',
        'ciclos/ano',
        'kg/L',
        'ton/ano',
        'kg CO₂eq/kg',
        'tCO₂eq/ano',
        'anos',
        '€/tCO₂eq',
        'R$/€'
    ]
})

st.dataframe(detalhes_df, use_container_width=True)

# Projeção anual
st.subheader("📈 Projeção Anual de Receita")

projecao_anual = []
for ano in range(1, anos_projecao + 1):
    emissoes_acumuladas = emissões_evitadas_ano * ano
    valor_eur_acumulado = calcular_valor_creditos(emissoes_acumuladas, preco_carbono_eur, "€")
    valor_brl_acumulado = calcular_valor_creditos(emissoes_acumuladas, preco_carbono_eur, "R$", taxa_cambio)
    
    projecao_anual.append({
        'Ano': ano,
        'Emissões Evitadas Acumuladas (tCO₂eq)': formatar_brasil(emissoes_acumuladas, 1),
        'Valor Acumulado (€)': formatar_brasil(valor_eur_acumulado, moeda=True, simbolo_moeda="€"),
        'Valor Acumulado (R$)': formatar_brasil(valor_brl_acumulado, moeda=True, simbolo_moeda="R$")
    })

projecao_df = pd.DataFrame(projecao_anual)
st.dataframe(projecao_df, use_container_width=True)

# Gráfico de projeção - precisa dos valores numéricos para o gráfico
projecao_numerica = []
for ano in range(1, anos_projecao + 1):
    emissoes_acumuladas = emissões_evitadas_ano * ano
    valor_brl_acumulado = calcular_valor_creditos(emissoes_acumuladas, preco_carbono_eur, "R$", taxa_cambio)
    projecao_numerica.append({
        'Ano': ano,
        'Valor Acumulado (R$)': valor_brl_acumulado
    })

projecao_grafico_df = pd.DataFrame(projecao_numerica)

fig = px.line(
    projecao_grafico_df, 
    x='Ano', 
    y='Valor Acumulado (R$)',
    title='Projeção de Receita com Créditos de Carbono',
    markers=True
)

# Formatar o eixo Y no padrão brasileiro
fig.update_layout(
    yaxis_title='Valor Acumulado (R$)',
    xaxis_title='Ano',
    yaxis=dict(
        tickformat=',.2f',
        tickmode='linear'
    )
)

# Aplicar formatação brasileira nos ticks do eixo Y
fig.update_yaxes(
    tickformat=",.2f",
    ticklabelmode="period"
)

st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# INFORMAÇÕES ADICIONAIS
# =============================================================================

with st.expander("ℹ️ Sobre os Cálculos"):
    st.markdown(f"""
    **🧮 Metodologia de Cálculo:**
    
    **1. Resíduo Processado:**
    ```
    Resíduo Anual (kg) = Capacidade Reator (L) × N° Reatores × Densidade (kg/L) × Ciclos/Ano
                       = {capacidade_reator} L × {num_reatores} × {densidade_residuo} kg/L × {ciclos_ano}
                       = {formatar_brasil(residuo_anual_kg, 0)} kg/ano = {formatar_brasil(residuo_anual_ton, 1)} ton/ano
    ```
    
    **2. Emissões Evitadas:**
    ```
    Emissões Evitadas (tCO₂eq/ano) = Resíduo Anual (kg) × Fator Emissão (kg CO₂eq/kg) ÷ 1000
                                   = {formatar_brasil(residuo_anual_kg, 0)} kg × {fator_emissao} kg CO₂eq/kg ÷ 1000
                                   = {formatar_brasil(emissões_evitadas_ano)} tCO₂eq/ano
    ```
    
    **3. Valor dos Créditos:**
    ```
    Valor (€) = Emissões Totais Evitadas (tCO₂eq) × Preço Carbono (€/tCO₂eq)
              = {formatar_brasil(emissoes_totais_evitadas, 1)} tCO₂eq × {formatar_brasil(preco_carbono_eur, moeda=True, simbolo_moeda='€')}/tCO₂eq
              = {formatar_brasil(valor_eur, moeda=True, simbolo_moeda='€')}
              
    Valor (R$) = Valor (€) × Taxa Câmbio (R$/€)
               = {formatar_brasil(valor_eur, moeda=True, simbolo_moeda='€')} × {formatar_brasil(taxa_cambio, moeda=True, simbolo_moeda='R$')}/€
               = {formatar_brasil(valor_brl, moeda=True, simbolo_moeda='R$')}
    ```
    
    **📚 Referências:**
    - Fator de emissão baseado em IPCC e metodologias de MDL
    - Preço do carbono baseado em EU ETS (mercado europeu)
    - Densidade típica de resíduos orgânicos: 0,4-0,6 kg/L
    """)

# =============================================================================
# DOWNLOAD DOS RESULTADOS
# =============================================================================

# Criar DataFrame para download (mantém valores numéricos originais)
download_df = pd.DataFrame({
    'Ano': list(range(1, anos_projecao + 1)),
    'Emissões_Evitadas_tCO2eq': [emissões_evitadas_ano * ano for ano in range(1, anos_projecao + 1)],
    'Valor_EUR': [calcular_valor_creditos(emissões_evitadas_ano * ano, preco_carbono_eur, "€") for ano in range(1, anos_projecao + 1)],
    'Valor_BRL': [calcular_valor_creditos(emissões_evitadas_ano * ano, preco_carbono_eur, "R$", taxa_cambio) for ano in range(1, anos_projecao + 1)]
})

# Botão de download
csv = download_df.to_csv(index=False, decimal=',', sep=';')
st.download_button(
    label="📥 Download da Projeção (CSV)",
    data=csv,
    file_name=f"projecao_creditos_carbono_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

st.markdown("---")
st.markdown("""
**♻️ Sistema de Compostagem - Ribeirão Preto/SP**  
*Cálculo de créditos de carbono baseado na capacidade dos reatores e processamento de resíduos*
""")

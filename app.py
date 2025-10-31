def calcular_emissoes_aterro(residuo_anual_kg_param):
    """Calcula emissões do aterro baseado em metodologia IPCC"""
    # Parâmetros baseados em IPCC 2006 Waste Model e literatura científica
    DOC = 0.15  # Carbono orgânico degradável (IPCC padrão para resíduos alimentares)
    DOC_f = 0.5  # Fração de DOC que realmente se decompõe
    F = 0.5      # Fração de CH4 no biogás
    MCF = 1.0    # Fator de correção de metano para aterros managed (IPCC)
    OX = 0.1     # Fator de oxidação
    
    # Cálculo do potencial de geração de CH4 (IPCC)
    potencial_CH4_kg = (residuo_anual_kg_param * DOC * DOC_f * F * 
                       (16/12) * MCF * (1 - OX))
    
    # Conversão para CO₂eq usando GWP AR6
    emissao_CH4_tco2eq = (potencial_CH4_kg * GWP_CH4_20) / 1000
    
    # Adicionar emissões de N2O do aterro (estimativa conservadora baseada em IPCC)
    fator_N2O_aterro = 0.005  # kg N2O/kg resíduo (IPCC para resíduos municipais)
    emissao_N2O_kg = residuo_anual_kg_param * fator_N2O_aterro
    emissao_N2O_tco2eq = (emissao_N2O_kg * GWP_N2O_20) / 1000
    
    # Total de emissões do aterro
    emissões_tco2eq_ano = emissao_CH4_tco2eq + emissao_N2O_tco2eq
    
    return emissões_tco2eq_ano

def calcular_detalhes_emissoes(residuo_anual_kg_param, residuos_kg_dia_param):
    """Calcula detalhes completos das emissões para exibição"""
    # Parâmetros fixos
    umidade = 0.85
    fracao_ms = 1 - umidade
    
    # CÁLCULO DETALHADO DO ATERRO (IPCC)
    DOC = 0.15
    DOC_f = 0.5
    F = 0.5
    MCF = 1.0
    OX = 0.1
    
    potencial_CH4_kg = (residuo_anual_kg_param * DOC * DOC_f * F * 
                       (16/12) * MCF * (1 - OX))
    emissao_CH4_tco2eq = (potencial_CH4_kg * GWP_CH4_20) / 1000
    
    fator_N2O_aterro = 0.005
    emissao_N2O_kg = residuo_anual_kg_param * fator_N2O_aterro
    emissao_N2O_tco2eq = (emissao_N2O_kg * GWP_N2O_20) / 1000
    
    aterro_total = emissao_CH4_tco2eq + emissao_N2O_tco2eq
    
    # Cálculo detalhado da compostagem (Yang et al. 2017)
    ch4_kg_dia = residuos_kg_dia_param * (TOC_COMPOSTAGEM_MINHOCAS * CH4_C_FRAC_COMPOSTAGEM_MINHOCAS * (16/12) * fracao_ms)
    n2o_kg_dia = residuos_kg_dia_param * (TN_COMPOSTAGEM_MINHOCAS * N2O_N_FRAC_COMPOSTAGEM_MINHOCAS * (44/28) * fracao_ms)
    
    ch4_kg_ano = ch4_kg_dia * 365
    n2o_kg_ano = n2o_kg_dia * 365
    
    ch4_tco2eq = (ch4_kg_ano * GWP_CH4_20) / 1000
    n2o_tco2eq = (n2o_kg_ano * GWP_N2O_20) / 1000
    compostagem_total = ch4_tco2eq + n2o_tco2eq
    
    # Emissões evitadas
    evitadas_total = aterro_total - compostagem_total
    
    return {
        'compostagem': {
            'ch4_kg_dia': ch4_kg_dia,
            'n2o_kg_dia': n2o_kg_dia,
            'ch4_kg_ano': ch4_kg_ano,
            'n2o_kg_ano': n2o_kg_ano,
            'ch4_tco2eq': ch4_tco2eq,
            'n2o_tco2eq': n2o_tco2eq,
            'total': compostagem_total
        },
        'aterro': {
            'potencial_CH4_kg': potencial_CH4_kg,
            'emissao_N2O_kg': emissao_N2O_kg,
            'ch4_tco2eq': emissao_CH4_tco2eq,
            'n2o_tco2eq': emissao_N2O_tco2eq,
            'total': aterro_total
        },
        'evitadas': evitadas_total,
        'parametros': {
            'umidade': umidade,
            'fracao_ms': fracao_ms,
            'TOC': TOC_COMPOSTAGEM_MINHOCAS,
            'TN': TN_COMPOSTAGEM_MINHOCAS,
            'CH4_frac': CH4_C_FRAC_COMPOSTAGEM_MINHOCAS,
            'N2O_frac': N2O_N_FRAC_COMPOSTAGEM_MINHOCAS,
            'GWP_CH4': GWP_CH4_20,
            'GWP_N2O': GWP_N2O_20,
            'DOC': DOC,
            'DOC_f': DOC_f,
            'F': F,
            'MCF': MCF,
            'OX': OX,
            'fator_N2O_aterro': fator_N2O_aterro
        }
    }

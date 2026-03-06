# COBERTURA - Analise de Cobertura de Dados
> Gerado automaticamente em 2026-03-06 | SMO Intelligence

---

## 1. Cobertura por Grupo / Trimestre

Releases disponiveis e extraidos com sucesso (24 de 24):

| Grupo               | 1T24 | 2T24 | 3T24 | 4T24 | 1T25 | 2T25 | Total |
|----------------------|------|------|------|------|------|------|-------|
| Multiplan (MULT3)    | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] | 6/6   |
| Iguatemi (IGTI11)    | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] | 6/6   |
| Allos (ALOS3)        | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] | 6/6   |
| General Shopping     | [OK] | [OK] | [OK] | [OK] | [OK] | [OK] | 6/6   |

**Legenda:** [OK] = Release extraido com sucesso

---

## 2. Cobertura de Metricas por Grupo

Numero de metricas capturadas (de 12 possiveis) por trimestre:

| Grupo               | 1T24 | 2T24 | 3T24 | 4T24 | 1T25 | 2T25 | Media |
|----------------------|------|------|------|------|------|------|-------|
| Multiplan            | 11   | 11   | 11   | 11   | 11   | 11   | 11.0  |
| Iguatemi             |  9   |  8   |  8   |  8   |  9   |  8   |  8.3  |
| Allos                |  8   |  6   |  7   |  8   |  8   |  7   |  7.3  |
| General Shopping     |  5   |  5   |  5   |  5   |  5   |  5   |  5.0  |

---

## 3. Cobertura por Metrica (todas as 24 observacoes)

| Metrica                 | Disponiveis | Cobertura | Grupos que publicam                    |
|-------------------------|-------------|-----------|----------------------------------------|
| ebitda_ajustado         | 24/24       | 100%      | Todos                                  |
| taxa_ocupacao           | 24/24       | 100%      | Todos                                  |
| noi_margem              | 21/24       |  88%      | Multiplan, Iguatemi, Allos (parcial), GSB |
| ffo                     | 21/24       |  88%      | Multiplan, Allos, GSB, Iguatemi (parcial) |
| receita_bruta           | 18/24       |  75%      | Multiplan, Iguatemi, GSB               |
| inadimplencia_liquida   | 18/24       |  75%      | Multiplan, Iguatemi, Allos             |
| sss                     | 18/24       |  75%      | Multiplan, Iguatemi, Allos             |
| ssr                     | 18/24       |  75%      | Multiplan, Iguatemi, Allos             |
| noi                     | 16/24       |  67%      | Multiplan, Allos (parcial), Iguatemi (parcial) |
| receita_locacao         |  6/24       |  25%      | Multiplan apenas                       |
| abl_propria_m2          |  6/24       |  25%      | Multiplan apenas (valores questionaveis)|
| vendas_totais           |  0/24       |   0%      | Nenhum (nao publicam nos releases)     |

---

## 4. Analise por Nivel de Dado

### 4.1 Nivel disponivel

| Grupo               | Nivel no Release            | Dados Individuais por Shopping |
|----------------------|-----------------------------|-------------------------------|
| Multiplan            | Consolidado do grupo        | Sim (Suplemento Operacional)  |
| Iguatemi             | Consolidado do grupo        | Nao                           |
| Allos                | Consolidado do portfolio    | Nao                           |
| General Shopping     | Consolidado do grupo        | Nao                           |

### 4.2 Observacoes sobre nivel de dados

- **Multiplan**: Publica dados consolidados no Release de Resultados. Dados individuais por shopping (incluindo Ribeirao Shopping e Shopping Santa Ursula) estao disponiveis no **Suplemento Operacional** (planilha Excel), que nao foi incluido nesta extracao.
- **Iguatemi**: Publica apenas dados consolidados. Nao ha breakdown por empreendimento nos releases.
- **Allos**: Publica dados consolidados do portfolio. Nao disponibiliza dados individuais nos releases trimestrais.
- **General Shopping**: Publica dados consolidados. Release mais enxuto, com menos metricas operacionais detalhadas.

---

## 5. Gap Analysis

### 5.1 Trimestres faltantes para serie historica completa (8 trimestres)

A serie atual cobre **1T2024 a 2T2025** (6 trimestres). Para completar 8 trimestres:

| Grupo               | Trimestres extraidos | Faltam para 8 tri | Trimestres necessarios |
|----------------------|----------------------|--------------------|------------------------|
| Multiplan            | 6 (1T24-2T25)        | 2                  | 3T23, 4T23             |
| Iguatemi             | 6 (1T24-2T25)        | 2                  | 3T23, 4T23             |
| Allos                | 6 (1T24-2T25)        | 2                  | 3T23, 4T23             |
| General Shopping     | 6 (1T24-2T25)        | 2                  | 3T23, 4T23             |

> **Nota**: Os releases de 3T23 e 4T23 precisam ser baixados do RI de cada empresa para completar a serie.

### 5.2 Metricas ausentes por grupo

**Multiplan** - Metricas faltantes:
- `vendas_totais`: Nao publicada no release consolidado (disponivel no Suplemento Operacional)

**Iguatemi** - Metricas faltantes:
- `ffo`: Ausente em 2T24, 3T24, 4T24
- `noi`: Valor absoluto ausente em 2T25 (apenas margem disponivel)
- `vendas_totais`, `abl_propria_m2`, `receita_locacao`: Nao publicados nos releases

**Allos** - Metricas faltantes:
- `receita_bruta`: Nao publicada (Allos reporta NOI/EBITDA diretamente)
- `noi` / `noi_margem`: Ausente parcialmente (2T24, 2T25 sem margem; 2T24 sem NOI absoluto)
- `vendas_totais`, `abl_propria_m2`, `receita_locacao`: Nao publicados nos releases

**General Shopping** - Metricas faltantes:
- `noi`: Nao publicado separadamente (apenas NOI Margem)
- `inadimplencia_liquida`: Nao publicada nos releases
- `sss`, `ssr`: Nao publicados nos releases
- `vendas_totais`, `abl_propria_m2`, `receita_locacao`: Nao publicados nos releases

---

## 6. Qualidade dos Dados Extraidos

### 6.1 Alertas de qualidade

Os dados foram extraidos automaticamente via regex de PDFs. Alguns valores requerem **revisao manual**:

| Grupo     | Trimestre | Metrica           | Valor Extraido | Alerta                                        |
|-----------|-----------|-------------------|----------------|-----------------------------------------------|
| Multiplan | 4T24      | receita_bruta     | 2.023,0        | Possivel captura do ano "2023" em vez de receita |
| Multiplan | 4T24      | abl_propria_m2    | 100,0          | Possivel captura de "base 100%" em vez de ABL |
| Multiplan | 1T25      | abl_propria_m2    | 100,0          | Idem                                          |
| Multiplan | 2T25      | abl_propria_m2    | 100,0          | Idem                                          |
| Multiplan | 4T24      | inadimplencia     | 12,4           | Valor atipicamente alto, verificar            |
| Iguatemi  | 3T24      | ebitda_ajustado   | 2.024,0        | Possivel captura do ano "2024" em vez de EBITDA |
| Iguatemi  | 1T24-4T24 | noi               | ~90-95         | Valores parecem ser NOI Margem (%), nao valor absoluto |

> **Flag `revisado=False`**: Todos os 24 registros foram marcados com `revisado=False` no seed, indicando necessidade de validacao manual antes de uso em analises.

### 6.2 Confiabilidade por grupo

| Grupo               | Confiabilidade | Observacao                                    |
|----------------------|----------------|-----------------------------------------------|
| Multiplan            | Alta           | Release bem estruturado, maioria das metricas capturadas corretamente. ABL e receita 4T24 requerem revisao. |
| Iguatemi             | Media          | NOI pode estar confundido com NOI Margem. FFO ausente em 3 trimestres. EBITDA 3T24 incorreto. |
| Allos                | Media          | Receita bruta nao publicada. NOI parcialmente disponivel. Demais metricas ok. |
| General Shopping     | Media-Baixa    | Release enxuto. Poucas metricas disponíveis. Valores absolutos menores (empresa menor). |

---

## 7. Resumo Estatistico

| Indicador                          | Valor     |
|------------------------------------|-----------|
| Total de releases processados      | 24        |
| Grupos cobertos                    | 4         |
| Trimestres por grupo               | 6 (1T24-2T25) |
| Total de metricas possiveis        | 288 (24 x 12) |
| Metricas extraidas (nao-nulas)     | 190       |
| Cobertura geral                    | 66,0%     |
| Melhor cobertura (grupo)           | Multiplan (91,7%) |
| Pior cobertura (grupo)             | General Shopping (41,7%) |
| Metrica mais disponivel            | ebitda_ajustado, taxa_ocupacao (100%) |
| Metrica menos disponivel           | vendas_totais (0%) |

---

## 8. Recomendacoes

1. **Revisar manualmente** os 7 alertas de qualidade listados na secao 6.1
2. **Baixar releases 3T23 e 4T23** dos 4 grupos para completar serie de 8 trimestres
3. **Obter Suplemento Operacional da Multiplan** para extrair dados individuais de Ribeirao Shopping e Shopping Santa Ursula
4. **Considerar ITRs/DFPs** como fonte complementar para metricas faltantes (vendas_totais, NOI absoluto da Iguatemi)
5. **Automatizar validacao** com ranges esperados por metrica/grupo para futuras extracoes

---

*Gerado por `scripts/extract_releases.py` + analise automatica | SMO Intelligence v0.1*

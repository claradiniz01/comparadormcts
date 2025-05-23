import re
from collections import defaultdict

# Função para extrair tipo de movimentação (Refinada v2)
def extract_movement_type(text_block):
    """Tenta extrair o tipo de movimentação/intimação do bloco de texto, priorizando marcadores como 'Conteudo:'"""
    text_lower = text_block.lower()
    
    # Padrões refinados, priorizando os que começam com 'Conteudo:' ou são mais específicos
    # Ordem é importante: mais específicos primeiro
    patterns = {
        # Padrões com 'Conteudo:'
        'INTIMACAO DE ACORDAO': r'conteudo:\s*intimacao de acordao',
        'DESPACHO': r'conteudo:\s*despacho',
        'DECISAO': r'conteudo:\s*decisao',
        'SENTENCA': r'conteudo:\s*sentenca',
        'INTIMACAO': r'conteudo:\s*intimacao',
        # Outros padrões específicos
        'ATO ORDINATORIO': r'ato ordinatorio',
        'INCLUSAO EM PAUTA': r'inclusao em pauta|pauta de julgamento',
        'EDITAL DE INTIMACAO': r'edital de intimacao',
        'CUMPRIMENTO DE SENTENCA': r'cumprimento de sentenca',
        # Padrões gerais (palavras-chave isoladas)
        'INTIMACAO DE ACORDAO': r'intimacao de acordao', # Repete para capturar sem 'Conteudo:'
        'DESPACHO': r'\bdespacho\b',
        'DECISAO': r'\bdecisao\b',
        'SENTENCA': r'\bsentenca\b',
        # Padrão genérico de Intimação (menos prioritário)
        'INTIMACAO': r'\bintimacao\b|tipo de comunicacao:\s*intimacao'
    }
    
    # Analisa uma porção inicial do texto para eficiência
    search_area = text_block[:600].lower() # Aumentei um pouco a área de busca

    # Itera sobre os padrões na ordem definida
    # Usamos um dicionário ordenado implicitamente (Python 3.7+) ou podemos usar OrderedDict
    # A ordem atual no dicionário literal funciona em Python 3.7+
    for type_name, pattern in patterns.items():
        match = re.search(pattern, search_area, re.IGNORECASE)
        if match:
            # Verifica se o match não é algo indesejado como 'advogado'
            # Uma heurística simples: se o match for muito curto e genérico, pode ser um falso positivo?
            # Por ora, confiamos na especificidade e ordem dos padrões.
            # O padrão 'Conteudo: ADV:' não está nos patterns, então não será capturado como tipo.
            return type_name
            
    # Tenta extrair do campo Título (padrão DJ Goias)
    title_match = re.search(r'Título:\s*(.+)', text_block, re.IGNORECASE)
    if title_match:
        title_content = title_match.group(1).strip().lower()
        # Verifica se o título corresponde a um tipo conhecido (usando os padrões gerais)
        general_patterns = {
            'DESPACHO': r'\bdespacho\b',
            'DECISAO': r'\bdecisao\b',
            'SENTENCA': r'\bsentenca\b',
            'INTIMACAO': r'\bintimacao\b'
            # Adicionar outros tipos gerais se necessário
        }
        for type_name, pattern in general_patterns.items():
             if re.search(pattern, title_content, re.IGNORECASE):
                 return type_name
        # Se não for um tipo conhecido, pode retornar uma categoria genérica ou o próprio título?
        # Retornar 'Tipo Não Identificado' é mais seguro para evitar poluir com títulos variados.

    return 'Tipo Não Identificado' # Retorno padrão

def normalize_text(text):
    """Normaliza o texto removendo espaços extras e convertendo para minúsculas."""
    return ' '.join(text.lower().split())

# Função de processamento que adiciona o tipo de movimentação (mantida)
def process_publications(texto, origem):
    texto = texto.replace('\xa0', ' ').replace('\r', '').strip()
    blocos = []

    def add_block(match_proc, bloco_completo, cabecalho_pub, origem_pub, posicao_pub):
        numero_processo = match_proc.group(1)
        tipo_mov = extract_movement_type(bloco_completo)
        blocos.append({
            "numero_processo": numero_processo,
            "texto": bloco_completo,
            "texto_normalizado": normalize_text(bloco_completo),
            "tipo_movimentacao": tipo_mov, # Campo adicionado
            "cabecalho": cabecalho_pub,
            "origem": origem_pub,
            "posicao": posicao_pub
        })

    padrao_al = re.split(r'(Publicação\s+\d+\s+de\s+\d+)', texto)
    if len(padrao_al) > 1:
        for i in range(1, len(padrao_al), 2):
            cabecalho = padrao_al[i].strip()
            corpo = padrao_al[i + 1].strip() if i + 1 < len(padrao_al) else ''
            bloco = f"{cabecalho}\n{corpo}"
            match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
            if match:
                add_block(match, bloco, cabecalho, origem, cabecalho)
    else:
        partes_djen_proc = re.split(r'(Publicacao Processo:\s*\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})', texto, flags=re.IGNORECASE)
        processed_indices = set()
        if len(partes_djen_proc) > 1:
            for i in range(1, len(partes_djen_proc), 2):
                cabecalho_match = re.search(r'Publicacao Processo:\s*(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})', partes_djen_proc[i], flags=re.IGNORECASE)
                if cabecalho_match:
                    numero_processo_cabecalho = cabecalho_match.group(1)
                    cabecalho = f"Publicação {numero_processo_cabecalho}"
                    corpo = partes_djen_proc[i+1].strip() if i + 1 < len(partes_djen_proc) else ''
                    data_disp_match = re.search(r'Data de disponibilizacao:\s*(\d{2}/\d{2}/\d{4})', corpo, flags=re.IGNORECASE)
                    if data_disp_match:
                        cabecalho += f" ({data_disp_match.group(1)})"
                    bloco = f"{partes_djen_proc[i].strip()}\n{corpo}"
                    match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
                    if match:
                        add_block(match, bloco, cabecalho, origem, cabecalho)
                        processed_indices.add(i)
                        processed_indices.add(i+1)

        partes_djen_pub = re.split(r"(PUBLICAÇÃO:\s*\d+\s+de\s+\d+)", texto, flags=re.IGNORECASE)
        if len(partes_djen_pub) > 1:
             for i in range(1, len(partes_djen_pub), 2):
                 if i in processed_indices or i+1 in processed_indices:
                     continue
                 cabecalho = f"{partes_djen_pub[i].strip()}"
                 corpo = partes_djen_pub[i + 1].strip() if i + 1 < len(partes_djen_pub) else ''
                 bloco = f"{cabecalho}\n{corpo}"
                 match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
                 if match:
                     add_block(match, bloco, cabecalho, origem, cabecalho)

    return blocos

# Função de agrupamento: agrupa SOMENTE por número de processo,
# mas EXIBE o tipo de movimentação na lista de duplicatas.
def agrupar_unicos_com_duplicatas(publicacoes):
    mapa_processo = defaultdict(list)
    for pub in publicacoes:
        if 'tipo_movimentacao' not in pub:
             pub['tipo_movimentacao'] = extract_movement_type(pub['texto'])
        mapa_processo[pub["numero_processo"]].append(pub)

    resultado_final = []
    duplicatas_info_geral = []

    for numero_processo, grupo_processo in mapa_processo.items():
        grupo_processo = sorted(grupo_processo, key=lambda x: x["origem"])
        primeiro = grupo_processo[0].copy()
        primeiro["duplicado_de"] = []

        if len(grupo_processo) > 1:
            outros = grupo_processo[1:]
            duplicados_info = [
                f"{g.get('posicao', 'N/A')} ({g.get('origem', 'N/A')}) - Tipo: {g.get('tipo_movimentacao', 'N/A')}"
                for g in outros
            ]
            primeiro["duplicado_de"] = duplicados_info
            duplicatas_info_geral.append(grupo_processo)

        resultado_final.append(primeiro)

    resultado_final = sorted(resultado_final, key=lambda x: (x["numero_processo"], x["origem"]))
    return resultado_final, duplicatas_info_geral


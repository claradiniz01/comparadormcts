import re
from collections import defaultdict

# Função para extrair tipo de movimentação (Refinada v3 - Aplicando Sugestões)
def extract_movement_type(text_block):
    """
    Tenta extrair o tipo de movimentação/intimação do bloco de texto.
    Prioriza tipos mais conclusivos e refina a detecção de intimações genéricas.
    Aumenta a área de busca para maior precisão.
    """
    # Aumenta a área de busca para capturar tipos em textos mais longos
    # Buscar em todo o texto pode impactar performance, começar com um limite maior.
    search_area = text_block[:1500].lower() # Aumentado de 600 para 1500 caracteres

    # Padrões reordenados e refinados
    # Ordem de prioridade: Tipos mais fortes -> Específicos -> Genéricos -> Indicadores
    patterns = {
        # 1. Tipos mais fortes (alta prioridade)
        'SENTENCA': r'\bsentenca\b|conteudo:\s*sentenca',
        'ACORDAO': r'\bacordao\b|conteudo:\s*acordao|intimacao de acordao', # "Intimacao de Acordao" é um tipo específico
        'DECISAO': r'\bdecisao\b|conteudo:\s*decisao',
        'DESPACHO': r'\bdespacho\b|conteudo:\s*despacho',

        # 2. Outros tipos específicos
        'ATO ORDINATORIO': r'ato ordinatorio',
        'EDITAL DE INTIMACAO': r'edital de intimacao', # Classifica o edital em si
        'INCLUSAO EM PAUTA': r'inclusao em pauta|pauta de julgamento',
        'CUMPRIMENTO DE SENTENCA': r'cumprimento de sentenca',
        # Adicionar outros tipos específicos identificados...
        # 'CITACAO': r'\bcitacao\b|conteudo:\s*citacao', # Exemplo
        # 'NOTIFICACAO': r'\bnotificacao\b|conteudo:\s*notificacao', # Exemplo

        # 3. Intimações mais específicas (antes da genérica)
        'INTIMACAO_ESPECIFICA': r'intimacao para\b|intimem-se as partes para|intime-se a parte|conteudo:\s*intimacao', # Prioriza "Conteudo: Intimacao" aqui

        # 4. Indicador DJEN (baixa prioridade, pode ser apenas um cabeçalho)
        'INDICADOR_INTIMACAO_DJEN': r'tipo de comunicacao:\s*intimacao',

        # 5. Intimação Genérica (último recurso, com restrição para evitar "Edital de Intimação")
        # Usando lookbehind negativo para não capturar se precedido por "edital de "
        'INTIMACAO_GENERICA': r'(?<!edital de\s)\bintimacao\b'
    }

    found_types = {} # Armazena tipos encontrados e suas posições

    # Itera sobre os padrões para encontrar todas as ocorrências na área de busca
    for type_name, pattern in patterns.items():
        # Usar finditer para encontrar todas as ocorrências e suas posições
        for match in re.finditer(pattern, search_area, re.IGNORECASE):
            # Armazena o tipo e a posição do início do match
            # Se o mesmo tipo for encontrado múltiplas vezes, guarda a primeira ocorrência
            if type_name not in found_types:
                found_types[type_name] = match.start()

    if not found_types:
        # Tenta extrair do campo Título (padrão DJ Goias) como fallback
        title_match = re.search(r'título:\s*(.+)', text_block.lower(), re.IGNORECASE) # Busca no texto completo aqui
        if title_match:
            title_content = title_match.group(1).strip()
            # Verifica se o título corresponde a um tipo conhecido (usando subconjunto dos padrões)
            general_patterns_title = {
                'DESPACHO': r'\bdespacho\b',
                'DECISAO': r'\bdecisao\b',
                'SENTENCA': r'\bsentenca\b',
                'INTIMACAO': r'\bintimacao\b' # Manter genérico para título
            }
            for type_name, pattern in general_patterns_title.items():
                 if re.search(pattern, title_content, re.IGNORECASE):
                     return type_name # Retorna tipo do título se encontrado

        return 'Tipo Não Identificado' # Retorno padrão se nada for encontrado

    # Lógica de Desambiguação Simples: Prioridade pela ordem definida no dicionário `patterns`
    # Itera na ordem de prioridade definida
    priority_order = [
        'SENTENCA', 'ACORDAO', 'DECISAO', 'DESPACHO', # Fortes
        'ATO ORDINATORIO', 'EDITAL DE INTIMACAO', 'INCLUSAO EM PAUTA', 'CUMPRIMENTO DE SENTENCA', # Específicos
        # 'CITACAO', 'NOTIFICACAO', # Outros específicos (se adicionados)
        'INTIMACAO_ESPECIFICA', # Intimação direcionada
        'INDICADOR_INTIMACAO_DJEN', # Indicador fraco
        'INTIMACAO_GENERICA' # Último recurso
    ]

    for type_name in priority_order:
        if type_name in found_types:
            # Retorna o tipo de maior prioridade encontrado
            # Renomeia os tipos internos para o nome final desejado se necessário
            if type_name == 'INDICADOR_INTIMACAO_DJEN' or type_name == 'INTIMACAO_GENERICA' or type_name == 'INTIMACAO_ESPECIFICA':
                 # Simplificação: retorna 'INTIMACAO' para esses casos.
                 # Uma lógica mais avançada poderia verificar se um tipo mais forte foi encontrado
                 # em uma posição posterior no texto, mas fora da 'search_area' inicial.
                 return 'INTIMACAO'
            else:
                 return type_name

    # Fallback final (não deveria ser alcançado se found_types não estiver vazio)
    return 'Tipo Não Identificado'

def normalize_text(text):
    """Normaliza o texto removendo espaços extras e convertendo para minúsculas."""
    return ' '.join(text.lower().split())

# Função de processamento que adiciona o tipo de movimentação
def process_publications(texto, origem):
    # Limpeza inicial do texto
    texto = texto.replace('\xa0', ' ').replace('\r', '').strip()
    blocos = []

    # Função auxiliar para adicionar bloco processado à lista
    def add_block(match_proc, bloco_completo, cabecalho_pub, origem_pub, posicao_pub):
        numero_processo = match_proc.group(1)
        # Chama a nova função de extração de tipo
        tipo_mov = extract_movement_type(bloco_completo)
        blocos.append({
            "numero_processo": numero_processo,
            "texto": bloco_completo,
            "texto_normalizado": normalize_text(bloco_completo),
            "tipo_movimentacao": tipo_mov, # Campo adicionado com nova lógica
            "cabecalho": cabecalho_pub,
            "origem": origem_pub,
            "posicao": posicao_pub
        })

    # Tenta identificar o padrão de Alagoas (Publicação X de Y)
    padrao_al = re.split(r'(Publicação\s+\d+\s+de\s+\d+)', texto)
    if len(padrao_al) > 1:
        # Processa blocos baseados no padrão de Alagoas
        for i in range(1, len(padrao_al), 2):
            cabecalho = padrao_al[i].strip()
            corpo = padrao_al[i + 1].strip() if i + 1 < len(padrao_al) else ''
            bloco = f"{cabecalho}\n{corpo}"
            # Busca número do processo no bloco
            match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
            if match:
                add_block(match, bloco, cabecalho, origem, cabecalho)
    else:
        # Se não for padrão Alagoas, tenta padrões DJEN
        # Padrão DJEN com número do processo no cabeçalho
        partes_djen_proc = re.split(r'(Publicacao Processo:\s*\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})', texto, flags=re.IGNORECASE)
        processed_indices = set() # Para evitar processamento duplicado
        if len(partes_djen_proc) > 1:
            for i in range(1, len(partes_djen_proc), 2):
                cabecalho_match = re.search(r'Publicacao Processo:\s*(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})', partes_djen_proc[i], flags=re.IGNORECASE)
                if cabecalho_match:
                    numero_processo_cabecalho = cabecalho_match.group(1)
                    cabecalho = f"Publicação {numero_processo_cabecalho}"
                    corpo = partes_djen_proc[i+1].strip() if i + 1 < len(partes_djen_proc) else ''
                    # Tenta adicionar data de disponibilização ao cabeçalho
                    data_disp_match = re.search(r'Data de disponibilizacao:\s*(\d{2}/\d{2}/\d{4})', corpo, flags=re.IGNORECASE)
                    if data_disp_match:
                        cabecalho += f" ({data_disp_match.group(1)})"
                    bloco = f"{partes_djen_proc[i].strip()}\n{corpo}"
                    # Busca número do processo (pode ser diferente do cabeçalho? Melhor garantir)
                    match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
                    if match:
                        add_block(match, bloco, cabecalho, origem, cabecalho)
                        processed_indices.add(i)
                        processed_indices.add(i+1)

        # Padrão DJEN com numeração de publicação (PUBLICAÇÃO X de Y)
        partes_djen_pub = re.split(r"(PUBLICAÇÃO:\s*\d+\s+de\s+\d+)", texto, flags=re.IGNORECASE)
        if len(partes_djen_pub) > 1:
             for i in range(1, len(partes_djen_pub), 2):
                 # Pula se já processado pelo padrão anterior
                 if i in processed_indices or i+1 in processed_indices:
                     continue
                 cabecalho = f"{partes_djen_pub[i].strip()}"
                 corpo = partes_djen_pub[i + 1].strip() if i + 1 < len(partes_djen_pub) else ''
                 bloco = f"{cabecalho}\n{corpo}"
                 match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
                 if match:
                     add_block(match, bloco, cabecalho, origem, cabecalho)

        # Adicionar aqui outros padrões de split se necessário para outros formatos de diário

    # Se nenhum padrão de split funcionou, pode ser um formato não reconhecido
    # ou um único bloco. Tentar extrair tipo mesmo assim?
    # A lógica atual retorna blocos vazios se nenhum split funcionar.
    # Considerar um fallback para tratar o texto inteiro como um bloco se nenhum split ocorrer.

    return blocos

# Função de agrupamento: agrupa por número de processo e lida com duplicatas
def agrupar_unicos_com_duplicatas(publicacoes):
    mapa_processo = defaultdict(list)
    for pub in publicacoes:
        # Garante que tipo_movimentacao existe (embora process_publications já deva adicionar)
        if 'tipo_movimentacao' not in pub:
             pub['tipo_movimentacao'] = extract_movement_type(pub['texto'])
        mapa_processo[pub["numero_processo"]].append(pub)

    resultado_final = []
    duplicatas_info_geral = [] # Lista para armazenar grupos de duplicatas

    for numero_processo, grupo_processo in mapa_processo.items():
        # Ordena as publicações do mesmo processo pela origem (nome do arquivo)
        grupo_processo = sorted(grupo_processo, key=lambda x: x["origem"])
        primeiro = grupo_processo[0].copy() # Pega a primeira ocorrência como a "única"
        primeiro["duplicado_de"] = [] # Inicializa lista de onde foi duplicado

        if len(grupo_processo) > 1:
            # Se houver mais de uma, as outras são duplicatas
            outros = grupo_processo[1:]
            # Cria informações sobre as duplicatas (posição, origem, tipo)
            duplicados_info = [
                f"{g.get('posicao', 'N/A')} ({g.get('origem', 'N/A')}) - Tipo: {g.get('tipo_movimentacao', 'N/A')}"
                for g in outros
            ]
            primeiro["duplicado_de"] = duplicados_info
            # Adiciona o grupo inteiro (incluindo o primeiro) à lista de duplicatas gerais
            # Isso pode ser útil para análise posterior, mas não é usado no DOCX final diretamente
            duplicatas_info_geral.append(grupo_processo)

        resultado_final.append(primeiro)

    # Ordena o resultado final por número de processo e origem
    resultado_final = sorted(resultado_final, key=lambda x: (x["numero_processo"], x["origem"]))
    return resultado_final, duplicatas_info_geral


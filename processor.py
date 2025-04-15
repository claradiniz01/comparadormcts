
import re
from collections import defaultdict

def process_publications(texto, origem):
    texto = texto.replace('\xa0', ' ').replace('\r', '').strip()

    blocos = []
    padrao_al = re.split(r'(Publicação\s+\d+\s+de\s+\d+)', texto)
    if len(padrao_al) > 1:
        for i in range(1, len(padrao_al), 2):
            cabecalho = padrao_al[i].strip()
            corpo = padrao_al[i + 1].strip() if i + 1 < len(padrao_al) else ''
            bloco = f"{cabecalho}\n{corpo}"
            match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
            if match:
                blocos.append({
                    "numero_processo": match.group(1),
                    "texto": bloco,
                    "cabecalho": cabecalho,
                    "origem": origem,
                    "posicao": cabecalho
                })
    else:
        # padrão DJEN tipo "PUBLICAÇÃO: X de Y"
        partes = re.split(r"PUBLICAÇÃO:\s*(\d+\s+de\s+\d+)", texto, flags=re.IGNORECASE)
        for i in range(1, len(partes), 2):
            cabecalho = f"Publicação {partes[i].strip()}"
            corpo = partes[i + 1].strip() if i + 1 < len(partes) else ''
            bloco = f"{cabecalho}\n{corpo}"
            match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})", bloco)
            if match:
                blocos.append({
                    "numero_processo": match.group(1),
                    "texto": bloco,
                    "cabecalho": cabecalho,
                    "origem": origem,
                    "posicao": cabecalho
                })

    return blocos

def agrupar_unicos_com_duplicatas(publicacoes):
    mapa = defaultdict(list)
    for pub in publicacoes:
        mapa[pub["numero_processo"]].append(pub)

    resultado = []
    duplicados = []

    for grupo in mapa.values():
        grupo = sorted(grupo, key=lambda x: x["origem"])  # ordem determinística
        primeiro = grupo[0].copy()
        if len(grupo) > 1:
            outros = grupo[1:]
            duplicados_info = [f"{g['posicao']} ({g['origem']})" for g in outros]
            primeiro["duplicado_de"] = duplicados_info
            duplicados.append(grupo)
        resultado.append(primeiro)

    return resultado, duplicados

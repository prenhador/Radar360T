import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

ufs = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
raw_data = []

def get_text(elem, tag):
    child = elem.find(tag)
    return child.text if child is not None else ''

def categorizar(l):
    l = l.upper()
    if 'BR-' in l or 'BR ' in l: return 'Federal (BR)'
    if re.search(r'\b[A-Z]{2}[-\s]\d', l): return 'Rodovias'
    return 'Urbano/Outros'

def get_regiao_classe(uf):
    regioes = {
        'Norte': {'ufs': ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'], 'classe': 'norte'},
        'Nordeste': {'ufs': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'], 'classe': 'nordeste'},
        'Centro-Oeste': {'ufs': ['DF', 'GO', 'MT', 'MS'], 'classe': 'centro'},
        'Sudeste': {'ufs': ['ES', 'MG', 'RJ', 'SP'], 'classe': 'sudeste'},
        'Sul': {'ufs': ['PR', 'RS', 'SC'], 'classe': 'sul'}
    }
    for r in regioes.values():
        if uf in r['ufs']: return r['classe']
    return ''

for uf in ufs:
    url = f"https://servicos.rbmlq.gov.br/dados-abertos/{uf}/medidores.xml"
    try:
        print(f"Baixando dados de {uf}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=20)
        root = ET.fromstring(response.read())
        
        for medidor in root.findall('DadosAbertosMedidoresVelocidade'):
            local = get_text(medidor, 'LocalVerificacao')
            data = get_text(medidor, 'DataValidade')
            vel = '?'
            faixas = medidor.find('Faixas')
            if faixas is not None and faixas.find('Faixa') is not None:
                vel = get_text(faixas.find('Faixa'), 'VelocidadeNominal') or '?'

            # Conversão de data segura
            is_vencido = False
            if data and data != '-':
                try:
                    is_vencido = datetime.strptime(data, '%d/%m/%Y') < datetime.now()
                except:
                    pass

            raw_data.append({
                'uf': uf,
                'mun': get_text(medidor, 'Municipio'),
                'local': local,
                'data': data or '-',
                'cat': categorizar(local),
                'regiao': get_regiao_classe(uf),
                'vencido': is_vencido,
                'vel': vel,
                'ficha': {
                    'responsavel': get_text(medidor.find('Proprietario') if medidor.find('Proprietario') is not None else medidor, 'Nome') or 'Não informado',
                    'dataVerif': get_text(medidor, 'DataUltimaVerificacao') or '-',
                    'resultado': get_text(medidor, 'UltimoResultado') or '-',
                    'marcaModelo': get_text(medidor, 'TipoMedidor'),
                    'faixas': [], 'historico': []
                }
            })
    except Exception as e:
        print(f"Aviso: Erro ao baixar {uf} - {e}")

try:
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    data_json = json.dumps(raw_data, ensure_ascii=False)
    html = re.sub(r'let rawData = \[.*?\];', f'let rawData = {data_json};', html, flags=re.DOTALL)
    html = re.sub(r'let filteredData = \[.*?\];', f'let filteredData = [];', html, flags=re.DOTALL)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
        
    print(f"Sucesso! {len(raw_data)} radares processados no Brasil.")
except Exception as e:
    print(f"Erro ao salvar index.html: {e}")

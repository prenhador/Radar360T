import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
import time

# Apenas Paraná por agora
ufs = ['PR']
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
    url_oficial = f"https://servicos.rbmlq.gov.br/dados-abertos/{uf}/medidores.xml"
    urls_para_tentar = [
        f"https://api.allorigins.win/raw?url={urllib.parse.quote(url_oficial)}",
        f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(url_oficial)}",
        url_oficial
    ]
    
    sucesso = False
    for i, tentativa_url in enumerate(urls_para_tentar):
        if sucesso: break
        try:
            print(f"Baixando {uf} (Tentativa {i+1}/3)...")
            req = urllib.request.Request(tentativa_url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=40)
            root = ET.fromstring(response.read())
            
            for medidor in root.findall('DadosAbertosMedidoresVelocidade'):
                local = get_text(medidor, 'LocalVerificacao')
                data = get_text(medidor, 'DataValidade')
                vel = '?'
                faixas = medidor.find('Faixas')
                if faixas is not None and faixas.find('Faixa') is not None:
                    vel = get_text(faixas.find('Faixa'), 'VelocidadeNominal') or '?'

                is_vencido = False
                if data and data != '-':
                    try:
                        is_vencido = datetime.strptime(data, '%d/%m/%Y') < datetime.now()
                    except: pass

                raw_data.append({
                    'uf': uf, 'mun': get_text(medidor, 'Municipio'), 'local': local,
                    'data': data or '-', 'cat': categorizar(local), 'regiao': get_regiao_classe(uf),
                    'vencido': is_vencido, 'vel': vel,
                    'ficha': {
                        'responsavel': get_text(medidor.find('Proprietario') if medidor.find('Proprietario') is not None else medidor, 'Nome') or 'Não informado',
                        'dataVerif': get_text(medidor, 'DataUltimaVerificacao') or '-', 'resultado': get_text(medidor, 'UltimoResultado') or '-',
                        'marcaModelo': get_text(medidor, 'TipoMedidor'), 'faixas': [], 'historico': []
                    }
                })
            sucesso = True
            print(f"-> Sucesso em {uf}!")
        except Exception as e:
            # AGORA ELE VAI GRITAR O ERRO EXATO!
            print(f"-> Falha na tentativa {i+1}: {e}")
            time.sleep(2)

# ==============================================================
# O MÉTODO BLINDADO DE GRAVAÇÃO
# ==============================================================
try:
    if len(raw_data) > 0:
        with open('index.html', 'r', encoding='utf-8') as f:
            html = f.read()

        data_json = json.dumps(raw_data, ensure_ascii=False)
        novo_html = re.sub(r'let\s+rawData\s*=\s*\[.*?\]\s*;', lambda m: f'let rawData = {data_json};', html, flags=re.DOTALL)

        if novo_html == html:
            print("\n❌ ERRO FATAL: O Python não encontrou a linha 'let rawData' no HTML!")
        else:
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(novo_html)
            print(f"\n🎉 GRAVADO COM SUCESSO! {len(raw_data)} radares injetados.")
    else:
        print("\n❌ ERRO: O Robô não baixou nenhum radar. O site do INMETRO deve estar offline.")
except Exception as e:
    print(f"Erro Crítico ao tentar gravar o arquivo: {e}")

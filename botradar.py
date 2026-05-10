import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
import time

# LISTA REDUZIDA: Apenas Paraná para teste rápido
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
    
    # PLANO A, B e C para escapar aos bloqueios
    urls_para_tentar = [
        f"https://api.allorigins.win/raw?url={urllib.parse.quote(url_oficial)}", # Plano A
        f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(url_oficial)}", # Plano B
        url_oficial # Plano C (Ligação direta)
    ]
    
    sucesso = False
    
    for tentativa_url in urls_para_tentar:
        if sucesso: 
            break
            
        try:
            print(f"A tentar baixar dados de {uf}...")
            req = urllib.request.Request(tentativa_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response = urllib.request.urlopen(req, timeout=40)
            xml_content = response.read()
            root = ET.fromstring(xml_content)
            
            radares_estado = 0
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
                radares_estado += 1
                
            print(f"-> ✅ {radares_estado} radares encontrados em {uf}!")
            sucesso = True
            
        except Exception as e:
            time.sleep(2)
            
    if not sucesso:
        print(f"❌ Aviso crítico: Falha absoluta em {uf}. Servidor do Governo indisponível para este estado hoje.")

# Gravar os dados no HTML
try:
    if len(raw_data) > 0:
        with open('index.html', 'r', encoding='utf-8') as f:
            html = f.read()

        data_json = json.dumps(raw_data, ensure_ascii=False)
        html = re.sub(r'let rawData = \[.*?\];', lambda m: f'let rawData = {data_json};', html, flags=re.DOTALL)
        html = re.sub(r'let filteredData = \[.*?\];', lambda m: f'let filteredData = [];', html, flags=re.DOTALL)

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f"\n🎉 SUCESSO! {len(raw_data)} radares injetados no Dashboard.")
    else:
        print("\n❌ ERRO CRÍTICO: Nenhum dado foi baixado.")
except Exception as e:
    print(f"Erro ao salvar index.html: {e}")

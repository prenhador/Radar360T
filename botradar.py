import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

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
    if uf == 'PR': return 'sul'
    return ''

try:
    print("A ler o ficheiro local PR.xml...")
    # Lê o ficheiro diretamente da pasta do GitHub
    with open('PR.xml', 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    root = ET.fromstring(xml_content)
    
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
            'uf': 'PR', 'mun': get_text(medidor, 'Municipio'), 'local': local,
            'data': data or '-', 'cat': categorizar(local), 'regiao': get_regiao_classe('PR'),
            'vencido': is_vencido, 'vel': vel,
            'ficha': {
                'responsavel': get_text(medidor.find('Proprietario') if medidor.find('Proprietario') is not None else medidor, 'Nome') or 'Não informado',
                'dataVerif': get_text(medidor, 'DataUltimaVerificacao') or '-', 'resultado': get_text(medidor, 'UltimoResultado') or '-',
                'marcaModelo': get_text(medidor, 'TipoMedidor'), 'faixas': [], 'historico': []
            }
        })
    print(f"-> Sucesso! {len(raw_data)} radares lidos do PR.xml local.")
except Exception as e:
    print(f"-> Falha ao ler o ficheiro local: {e}")

# ==============================================================
# GRAVAÇÃO (O Método Blindado que já validámos que funciona!)
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
        print("\n❌ ERRO: Nenhum radar encontrado no ficheiro PR.xml.")
except Exception as e:
    print(f"Erro Crítico: {e}")

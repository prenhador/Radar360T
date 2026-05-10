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
    print("A ler o arquivo local PR.xml...")
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
    print(f"-> Sucesso! {len(raw_data)} radares processados.")
except Exception as e:
    print(f"-> Falha ao processar os dados: {e}")

# ==============================================================
# NOVA ARQUITETURA: GRAVAR OS DADOS NUM ARQUIVO SEPARADO
# ==============================================================
try:
    if len(raw_data) > 0:
        data_json = json.dumps(raw_data, ensure_ascii=False)
        # O Robô agora escreve o JS puro. O HTML vai carregar isto como um script.
        js_content = f"window.DADOS_DO_ROBO = {data_json};"
        
        with open('dados.js', 'w', encoding='utf-8') as f:
            f.write(js_content)
            
        print(f"\n🎉 ARQUITETURA NOVA! dados.js criado/atualizado com sucesso com {len(raw_data)} radares.")
    else:
        print("\n❌ ERRO: Nenhum dado processado.")
except Exception as e:
    print(f"Erro Crítico: {e}")

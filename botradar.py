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
    if uf == 'PR': return 'uf-sul'
    return ''

try:
    print("A ler o arquivo local PR.xml...")
    with open('PR.xml', 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    root = ET.fromstring(xml_content)
    
    for medidor in root.findall('DadosAbertosMedidoresVelocidade'):
        local = get_text(medidor, 'LocalVerificacao')
        data = get_text(medidor, 'DataValidade')
        resultado = get_text(medidor, 'UltimoResultado')
        
        # Extração básica para o Dashboard
        vel = '?'
        faixas_el = medidor.getElementsByTagName('Faixa') if hasattr(medidor, 'getElementsByTagName') else medidor.findall('.//Faixa')
        if faixas_el:
            vel = faixas_el[0].find('VelocidadeNominal').text if faixas_el[0].find('VelocidadeNominal') is not None else '?'

        # Lógica de Ficha Técnica completa (Historico e Faixas)
        def extrair_ficha_completa(m):
            faixas = []
            for fx in m.findall('.//Faixa'):
                faixas.append({
                    'num': get_text(fx, 'NumeroFaixa'),
                    'desc': get_text(fx, 'Descricao'),
                    'inmetro': get_text(fx, 'NumeroInmetro'),
                    'serie': get_text(fx, 'NumeroSerie'),
                    'sentido': get_text(fx, 'Sentido'),
                    'vel': get_text(fx, 'VelocidadeNominal')
                })
            hist = []
            for cert in m.findall('.//Certificado'):
                hist.append({
                    'cert': get_text(cert, 'NumeroCertificado'),
                    'ensaio': get_text(cert, 'NumeroEnsaio'),
                    'ano': get_text(cert, 'Ano'),
                    'laudo': get_text(cert, 'DataLaudo'),
                    'validade': get_text(cert, 'DataValidade'),
                    'tipo': get_text(cert, 'TipoServico'),
                    'resultado': get_text(cert, 'Resultado')
                })
            return {
                'responsavel': get_text(m, 'Nome') or 'Não informado',
                'dataVerif': get_text(m, 'DataUltimaVerificacao') or '-',
                'resultado': resultado or '-',
                'marcaModelo': get_text(m, 'TipoMedidor') or '-',
                'portaria': get_text(m, 'PortariaAprovacao') or '-',
                'faixas': faixas,
                'historico': hist
            }

        is_vencido = False
        if data and data != '-':
            try:
                is_vencido = datetime.strptime(data, '%d/%m/%Y') < datetime.now()
            except: pass

        raw_data.append({
            'uf': 'PR', 'mun': get_text(medidor, 'Municipio'), 'local': local,
            'data': data or '-', 'cat': categorizar(local), 'regiao': get_regiao_classe('PR'),
            'vencido': is_vencido, 'vel': vel, 'ficha': extrair_ficha_completa(medidor)
        })
    print(f"-> Sucesso! {len(raw_data)} radares processados.")
except Exception as e:
    print(f"-> Falha ao processar dados: {e}")

# SALVAR NOVO ARQUIVO DE DADOS
try:
    if len(raw_data) > 0:
        data_json = json.dumps(raw_data, ensure_ascii=False)
        with open('dados.js', 'w', encoding='utf-8') as f:
            f.write(f"window.DADOS_DO_ROBO = {data_json};")
        print("🎉 Ficheiro dados.js criado com sucesso!")
except Exception as e:
    print(f"Erro ao salvar: {e}")

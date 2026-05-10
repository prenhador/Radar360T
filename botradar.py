import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
import requests
import zipfile
import io
import glob
import os

raw_data = []
# Todos os 27 estados para mandar no POST
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

def get_text(elem, tag):
    child = elem.find(tag)
    return child.text if child is not None else ''

def categorizar(l):
    l = l.upper()
    if 'BR-' in l or 'BR ' in l: return 'Federal (BR)'
    if re.search(r'\b[A-Z]{2}[-\s]\d', l): return 'Rodovias'
    return 'Urbano/Outros'

def get_regiao_classe(uf):
    if uf in ['PR', 'SC', 'RS']: return 'uf-sul'
    if uf in ['SP', 'RJ', 'MG', 'ES']: return 'uf-sudeste'
    if uf in ['GO', 'MT', 'MS', 'DF']: return 'uf-centro'
    if uf in ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO', 'AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE']: return 'uf-norte'
    return ''

# ==============================================================
# 1. BAIXAR E EXTRAIR O ZIP AO VIVO (A SUA DESCOBERTA!)
# ==============================================================
try:
    url = "https://servicos.rbmlq.gov.br/Instrumento/Download"
    data = [("SelectedTipoClassificacaoInstrumento", "322")] # 322 = Medidor de Velocidade
    data += [("SelectedEstados", uf) for uf in UFS]
    data.append(("extensao", "xml"))

    print("🚀 A solicitar ZIP com os radares de todo o Brasil ao vivo...")
    resp = requests.post(url, data=data, timeout=120)
    resp.raise_for_status()
    
    # Extrai tudo para uma pasta temporária invisível no servidor
    os.makedirs("xml_temp", exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall("xml_temp")
    print("📦 Arquivos ZIP baixados e extraídos com sucesso!")
    
except Exception as e:
    print(f"❌ Falha no download ou extração: {e}")
    exit(1)

# ==============================================================
# 2. LER E PROCESSAR OS XMLs
# ==============================================================
arquivos_xml = glob.glob('xml_temp/*.xml')

for arquivo in arquivos_xml:
    try:
        print(f"A ler o {arquivo}...")
        with open(arquivo, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # O DF costuma vir vazio, previne que o Python dê erro a tentar ler nada
        if not xml_content.strip():
            print(f"  -> Ignorado: O arquivo {arquivo} está vazio.")
            continue

        root = ET.fromstring(xml_content)
        
        for medidor in root.findall('DadosAbertosMedidoresVelocidade'):
            uf = get_text(medidor, 'SiglaUf')
            if not uf: continue # Ignora se não tiver estado
            
            local = get_text(medidor, 'LocalVerificacao')
            data = get_text(medidor, 'DataValidade')
            resultado = get_text(medidor, 'UltimoResultado')
            
            vel = '?'
            faixas_el = medidor.getElementsByTagName('Faixa') if hasattr(medidor, 'getElementsByTagName') else medidor.findall('.//Faixa')
            if faixas_el:
                vel = faixas_el[0].find('VelocidadeNominal').text if faixas_el[0].find('VelocidadeNominal') is not None else '?'

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
                'uf': uf, 'mun': get_text(medidor, 'Municipio'), 'local': local,
                'data': data or '-', 'cat': categorizar(local), 'regiao': get_regiao_classe(uf),
                'vencido': is_vencido, 'vel': vel, 'ficha': extrair_ficha_completa(medidor)
            })
    except Exception as e:
        print(f"-> Erro ao processar o arquivo {arquivo}: {e}")

# ==============================================================
# 3. SALVAR O MEGA ARQUIVO DADOS.JS PARA O DASHBOARD
# ==============================================================
try:
    if len(raw_data) > 0:
        data_json = json.dumps(raw_data, ensure_ascii=False)
        with open('dados.js', 'w', encoding='utf-8') as f:
            f.write(f"window.DADOS_DO_ROBO = {data_json};")
        print(f"\n🎉 SUCESSO ABSOLUTO! dados.js criado com {len(raw_data)} radares reais do Brasil inteiro.")
    else:
        print("\n❌ ERRO: Nenhum dado processado.")
except Exception as e:
    print(f"Erro ao salvar: {e}")

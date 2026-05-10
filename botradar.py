import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
import glob

raw_data = []

def get_text(elem, tag):
    child = elem.find(tag)
    return child.text if child is not None else ''

def categorizar(l):
    l = l.upper()
    if 'BR-' in l or 'BR ' in l: return 'Federal (BR)'
    if re.search(r'\b[A-Z]{2}[-\s]\d', l): return 'Rodovias'
    return 'Urbano/Outros'

# Mapa completo de cores/regiões para todos os estados do Brasil
def get_regiao_classe(uf):
    if uf in ['PR', 'SC', 'RS']: return 'uf-sul'
    if uf in ['SP', 'RJ', 'MG', 'ES']: return 'uf-sudeste'
    if uf in ['GO', 'MT', 'MS', 'DF']: return 'uf-centro'
    if uf in ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO', 'AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE']: return 'uf-norte'
    return ''

# Procura TODOS os arquivos .xml na pasta do GitHub
arquivos_xml = glob.glob('*.xml')

if not arquivos_xml:
    print("❌ Nenhum ficheiro XML encontrado na pasta.")
else:
    for arquivo in arquivos_xml:
        try:
            print(f"A processar {arquivo}...")
            with open(arquivo, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            root = ET.fromstring(xml_content)
            
            for medidor in root.findall('DadosAbertosMedidoresVelocidade'):
                # Descobre o Estado (UF) diretamente de dentro do XML
                uf = get_text(medidor, 'SiglaUf')
                if not uf:
                    continue # Ignora se houver algum radar sem UF
                
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
            print(f"-> Concluído: {arquivo} lido com sucesso!")
        except Exception as e:
            print(f"-> Falha ao processar {arquivo}: {e}")

# ==============================================================
# SALVAR O MEGA ARQUIVO DE DADOS (dados.js)
# ==============================================================
try:
    if len(raw_data) > 0:
        data_json = json.dumps(raw_data, ensure_ascii=False)
        with open('dados.js', 'w', encoding='utf-8') as f:
            f.write(f"window.DADOS_DO_ROBO = {data_json};")
        print(f"\n🎉 SUCESSO ABSOLUTO! dados.js criado com {len(raw_data)} radares de todo o Brasil.")
    else:
        print("\n❌ ERRO: Nenhum dado processado.")
except Exception as e:
    print(f"Erro ao salvar: {e}")

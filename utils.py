from operator import contains
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import matplotlib.dates as mdates
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import datetime
import pycep_correios
import os
import glob
import warnings
import numpy as np
warnings.simplefilter(action='ignore', category=FutureWarning)
import config
from io import BytesIO
from PIL import Image

mapa_estado_rj = gpd.read_file('./dados_geo/RJ_UF_2021.shp', encoding='utf-8').to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')

def converte_gms_gd(latlong):
    if latlong[2] == '.':
        coordenada_convertida = float(latlong) * -1
    else:
        info = str(latlong)
        direcao = -1 # multiplicará o valor da coordenada, adequando ao sistema
        conversao = info.replace('-',' ') # substitui os hífens entre os valores de grau, minuto, segundo para serem manipulados e organizados
        conversao = conversao.split() # segmenta a string anterior pelos espaços
        # conversao_direcao = conversao.pop() # remove o último segmento da coordenada, que trata da posição/direção no globo N-S-L-O
        grau = int(conversao[0])
        minuto = int(conversao[1])
        segundo = int(conversao[2])
        coordenada_convertida_gd = grau + minuto /60.0+ segundo/3600.0
        coordenada_convertida = coordenada_convertida_gd * direcao
    return round(coordenada_convertida, 4)

def valida_coordenadas(coordenadas):
    coordenadas_dividida = coordenadas.split(',')
    latitude = converte_gms_gd(coordenadas_dividida[0].strip())
    longitude = converte_gms_gd(coordenadas_dividida[1].strip())
    coordenadas_gd = {'latitude': [latitude], 'longitude': [longitude]}
    coordenadas_gd = pd.DataFrame(data = coordenadas_gd)
    coordenadas_gd = gpd.GeoDataFrame(data = coordenadas_gd, geometry = gpd.points_from_xy(coordenadas_gd.longitude, coordenadas_gd.latitude), crs = crs)
    coordenadas_gd = coordenadas_gd.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')
    if mapa_estado_rj.contains(coordenadas_gd)[0]:
        return True
    else:
        return False

crs = {'proj': 'latlong', 'ellps': 'WGS84', 'datum': 'WGS84', 'no_defs': True}
'''
Definindo pontos das estações automáticas abordadas.
'''
estacoes = gpd.read_file('./dados_geo/estacoes_rj_geoloc.shp')
estacoes = estacoes.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')

'''
Definindo mapa base para o Rio de Janeiro que será usado em todos os plots do projeto.
'''
mapa_rj = gpd.read_file('./dados_geo/RJ_Municipios_2021.shp', encoding='utf-8')
mapa_rj = mapa_rj.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')


def obter_endereco(cep):
    '''
    Recebe um CEP e retorna endereço formatado.
    '''
    endereco = pycep_correios.get_address_from_cep(cep, webservice=pycep_correios.WebService.CORREIOS)
    return endereco['logradouro'] + ", " + endereco['bairro'] + ", " + endereco['cidade'] + " - " + endereco['uf']

def geolocaliza_endereco(cep_referencia):
    '''
    Recebe um CEP de referência e retorna objeto geodataframe contendo endereço e coordenadas para o ponto.
    Será preciso aplicar CRS compatível para plotar o ponto do CEP sobre mapa.
    '''
    cep_geolocalizado = pd.DataFrame({'CEP': [str(cep_referencia)]})
    geolocator = Nominatim(user_agent = config.user_agent) # user_agent definido no arquivo config.py
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    cep_geolocalizado['endereco'] = cep_geolocalizado['CEP'].apply(obter_endereco).apply(geocode)
    cep_geolocalizado['latitude'] = cep_geolocalizado['endereco'].apply(lambda loc: loc.latitude if loc else None)
    cep_geolocalizado['longitude'] = cep_geolocalizado['endereco'].apply(lambda loc: loc.longitude if loc else None)
    cep_geolocalizado['geometry'] = [Point(x) for x in zip(cep_geolocalizado.longitude, cep_geolocalizado.latitude)]
    return cep_geolocalizado

def valida_cep(informar_cep):
    # faixa de CEP RJ 20000000 até 28999999, antes do intervalo são CEPs de SP, após são CEPs do ES
    cep_inicio = 20000000
    cep_fim = 28999999
    if cep_inicio <= int(informar_cep.strip().replace('-', '')) <= cep_fim: # valida cep dentro do intervalo permitido para o RJ
        try: # através da api, checa se o mesmo retorna dados geográficos válidos
            cep = pd.DataFrame({'CEP': [informar_cep.strip().replace('-', '')]}) # cria dataframe para conter dados gerados pela API
            geolocator = Nominatim(user_agent = config.user_agent) # user_agent definido no arquivo config.py
            geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
            cep['endereco'] = cep['CEP'].apply(obter_endereco).apply(geocode)
            cep['latitude'] = cep['endereco'].apply(lambda loc: loc.latitude if loc else None)
            cep['longitude'] = cep['endereco'].apply(lambda loc: loc.longitude if loc else None)
            cep['geometry'] = [Point(x) for x in zip(cep.longitude, cep.latitude)]
            return True
        except:
            return False
    else:
        return False

def plotar_mapa_estacao(userid, ema):
    estacoes = gpd.read_file('./dados_geo/estacoes_rj_geoloc.shp')
    estacoes = estacoes.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')
    ponto = estacoes[estacoes['codigo'] == ema]
    demais_estacoes = estacoes[estacoes['codigo'] != ema]
    base = mapa_rj.plot(color='#a9c4aa', edgecolor='#000', figsize=(10,10))
    ponto.plot(ax = base, markersize = 5, marker='x', color = 'red', label = f'Estação de Referência {ema}')
    demais_estacoes.plot(ax = base, markersize=5, marker = '*', color='blue', label = 'Estações Meteorológicas Automáticas do RJ')
    
    base.set_xlabel('Distância (Km)')
    base.set_ylabel('Distância (Km)')
    plt.legend(loc = 'upper left')
    locs,labels = plt.xticks()
    plt.xticks(locs, map(lambda x: "%g" % x, locs - 450))
    locs, labels = plt.yticks()
    plt.yticks(locs, map(lambda y: "%g" % y, locs - 7400))
    bytes_img = BytesIO()
    plt.savefig(bytes_img, format='png', dpi=300, bbox_inches='tight')
    bytes_img.seek(0)
    bytes_img.name = f'{str(userid)}_{ema}_plotado'
    return bytes_img

def plotar_mapa_cep(cep_geolocalizado):
    '''
    Recebe CEP já geolocalizado e plota sobre mapa na forma de ponto, na cor vermelha, sinalizando o ponto de interesse do usuário.
    '''
    ponto_cep = gpd.GeoDataFrame(cep_geolocalizado, crs = crs).to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')
    base = mapa_rj.plot(color='#a9c4aa', edgecolor='#000', figsize=(10,10))
    estacoes.plot(ax = base, markersize=5, marker = '*', color='blue', label = 'Estações Automáticas')
    ponto_cep.plot(ax = base, markersize = 5, marker = 'x', color = 'red', label = 'Local de Referência')
    base.set_title(f'Localização para o CEP {str(cep_geolocalizado)}')
    base.set_xlabel('Distância (Km)')
    base.set_ylabel('Distância (Km)')
    plt.legend(loc = 'upper left')
    plt.savefig(f'imgs_plots/{str(cep_geolocalizado)}_plotado.png', bbox_inches='tight')

def obter_estacao_proxima(ref):
    '''
    Passa o DF com o CEP geolocalizado, para se então obter a estação meteorológica mais próxima.
    '''
    estacoes['distancia_pont_estacao'] = estacoes.geometry.apply(lambda x: ref.distance(x).min())
    estacao_proxima = estacoes['distancia_pont_estacao'].min()
    estacao = estacoes[estacoes.distancia_pont_estacao == estacao_proxima]
    estacao_proxima = str(list(estacao.local)[0], list(estacao.codigo)[0])
    return estacao_proxima

# Gera mapa com a coordenada geográfica GD apontando a posição do ponto e EMA mais próxima
def plota_mapa_coord(userid, latitude, longitude):
    coordenadas_gd = {'latitude': [latitude], 'longitude': [longitude]}
    coordenadas_gd = pd.DataFrame(data = coordenadas_gd)
    coordenadas_gd = gpd.GeoDataFrame(data = coordenadas_gd, geometry = gpd.points_from_xy(coordenadas_gd.longitude, coordenadas_gd.latitude), crs = crs)
    coordenadas_gd = coordenadas_gd.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')

    estacoes = gpd.read_file('./dados_geo/estacoes_rj_geoloc.shp')
    estacoes = estacoes.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')
    estacoes['ema_distancia_min'] = estacoes.geometry.apply(lambda x: coordenadas_gd.distance(x).min())
    estacao_proxima = estacoes['ema_distancia_min'].min()
    estacao = estacoes[estacoes.ema_distancia_min == estacao_proxima]

    mapa_rj = gpd.read_file('./dados_geo/RJ_Municipios_2021.shp', encoding='utf-8')
    mapa_rj = mapa_rj.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')

    # carrega mapa base do RJ com geopandas
    base = mapa_rj.plot(color ='#a9c4aa', edgecolor = '#000', figsize = (10,10))
    # carrega as posições das EMAs sobre o mapa do RJ
    estacoes.plot(ax = base, markersize = 5, marker = '*', color = 'blue', label = 'Estações Meteorológicas Automáticas do RJ')
    # posiciona o ponto de referência de acordo com a coordenada geográfica informada
    coordenadas_gd.plot(ax = base, markersize=5, marker = 'x', color = 'red', label = 'Ponto de Referência')
    # posiciona o ponto no mapa da estação mais próxima do ponto de referência
    estacao.plot(ax = base, markersize=5, marker = 'x', color = 'orange', label = f'Estação mais próxima EMA {list(estacao.codigo)[0]}')

    base.set_xlabel('Distância (Km)')
    base.set_ylabel('Distância (Km)')
    plt.legend(loc = 'upper left')
    locs,labels = plt.xticks()
    plt.xticks(locs, map(lambda x: "%g" % x, locs - 450))
    locs, labels = plt.yticks()
    plt.yticks(locs, map(lambda y: "%g" % y, locs - 7400))
    bytes_img = BytesIO()
    plt.savefig(bytes_img, format='png', dpi=300, bbox_inches='tight')
    bytes_img.seek(0)
    bytes_img.name = f'imgs_plots/{str(userid)}_latlong.png'
    return bytes_img
    # return list(estacao.codigo)[0]

def busca_estacao_usando_coordenadas(latitude, longitude):
    coordenadas_gd = {'latitude': [latitude], 'longitude': [longitude]}
    coordenadas_gd = pd.DataFrame(data = coordenadas_gd)
    coordenadas_gd = gpd.GeoDataFrame(data = coordenadas_gd, geometry = gpd.points_from_xy(coordenadas_gd.longitude, coordenadas_gd.latitude), crs = crs)
    coordenadas_gd = coordenadas_gd.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')
    estacoes = gpd.read_file('./dados_geo/estacoes_rj_geoloc.shp')
    estacoes = estacoes.to_crs('+proj=utm +zone=23 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=km +no_defs')
    estacoes['ema_distancia_min'] = estacoes.geometry.apply(lambda x: coordenadas_gd.distance(x).min())
    estacao_proxima = estacoes['ema_distancia_min'].min()
    estacao = estacoes[estacoes.ema_distancia_min == estacao_proxima]
    return list(estacao.codigo)[0]


estacoes = ['A601', 'A602', 'A603', 'A604', 'A606', 'A607', 'A608', 'A609', 'A610', 'A611', 'A618', 'A619', 'A620', 'A621', 'A624', 'A625', 'A626', 'A627', 'A628', 'A629', 'A630', 'A635', 'A636', 'A652', 'A659', 'A667']

info_estacoes_disponiveis = 'A601, A602, A603, A604, A606, A607, A608, A609, A610, A611, A618, A619, A620, A621, A624, A625, A626, A627, A628, A629, A630, A635, A636, A652, A659, A667'

inicio_operacao = {
    'A601': '2000-05-23',
    'A602': '2002-11-07',
    'A603': '2002-10-20',
    'A604': '2002-11-19',
    'A606': '2006-09-21',
    'A607': '2006-09-24',
    'A608': '2006-09-21',
    'A609': '2006-09-28',
    'A610': '2006-10-21',
    'A611': '2006-09-26',
    'A618': '2006-10-31',
    'A619': '2006-11-18',
    'A620': '2008-06-12',
    'A621': '2007-04-12',
    'A624': '2010-09-17',
    'A625': '2016-06-07',
    'A626': '2016-06-02',
    'A627': '2018-07-12',
    'A628': '2017-08-24',
    'A629': '2018-10-10',
    'A630': '2018-10-15',
    'A635': '2017-08-31',
    'A636': '2017-08-09',
    'A652': '2007-05-17',
    'A659': '2015-07-27',
    'A667': '2015-09-01'}

def ajusta_data_plot(dia_mes_ano):
    tratando_data = dia_mes_ano.replace('-',' ')
    dividindo_data = tratando_data.split()
    dia = dividindo_data[0]
    mes = dividindo_data[1]
    ano = dividindo_data[2]
    ano_mes_dia = f'{ano}-{mes}-{dia}'
    return ano_mes_dia

def trata_data_completa(data_completa):
    tratando_data = data_completa.replace('-',' ')
    dividindo_data = tratando_data.split()
    ano = dividindo_data[0]
    mes = dividindo_data[1]
    dia = dividindo_data[2]
    return f'{dia}-{mes}-{ano}'

# Recebe datas separadas por traço, separa elementos da data e reorganiza na string
def trata_data_mes_ano(data_completa):
    tratando_data = data_completa.strip().replace('-',' ')
    dividindo_data = tratando_data.split()
    ano = dividindo_data[0]
    mes = dividindo_data[1]
    return f'{mes}-{ano}'

def valida_data(data_completa):
    data_certa = None
    try:
        separa_dia_mes_ano = data_completa.replace('-', ' ').split()
        ano = int(separa_dia_mes_ano[2])
        mes = int(separa_dia_mes_ano[1])
        dia = int(separa_dia_mes_ano[0])
        if len(data_completa.replace('-','')) != 8 or not data_completa.replace('-','').replace('/','').isdigit():
            data_certa = False
            return data_certa
        else:
            try:
                nova_data = datetime.datetime(ano, mes, dia)
                data_certa = True
                return data_certa
            except:
                data_certa = False
                return data_certa
    except:
        return False

def valida_inicio_operacao(ema, dia_mes_ano):
    # testes A601 início operacional em 23-05-2000
    formato_data = '%d-%m-%Y'
    data_inicio_operacional = datetime.datetime.strptime(trata_data_completa(inicio_operacao[ema]), formato_data)
    data_inicial_proposta = datetime.datetime.strptime(dia_mes_ano.strip(), formato_data)
    data_inicial_limite = datetime.datetime(2017, 1, 1)
    data_final_limite = datetime.datetime(2022, 8, 31)
    if (data_inicial_limite < data_inicio_operacional < data_final_limite) or (data_inicial_limite < data_inicial_proposta < data_final_limite): # data de início de op da ema e data proposta estão contidas no intervalo init e fim
        if data_inicial_proposta > data_inicio_operacional: # se a data proposta ocorrer após o início de operação da ema, retorna a data proposta
            return dia_mes_ano
        else: # caso contrário, retorna a data de início de operação da ema
            return trata_data_completa(inicio_operacao[ema])
    elif data_inicio_operacional < data_inicial_limite:
        return '01-01-2017'
    elif data_inicial_proposta < data_inicial_limite:
        return '01-01-2017'

def valida_fim_operacao(dia_mes_ano_inicial_adotado, dia_mes_ano_final_proposto): # chegando nessa etapa de validação, a data inicial proposta já foi validada e está contida no intervalo de limites inicial e final
    formato_data = '%d-%m-%Y'
    data_inicial_adotada = datetime.datetime.strptime(dia_mes_ano_inicial_adotado, formato_data)
    data_final_proposta = datetime.datetime.strptime(dia_mes_ano_final_proposto.strip(), formato_data)
    data_inicial_limite = datetime.datetime(2017, 1, 1)
    data_final_limite = datetime.datetime(2022, 8, 31)
    if (data_inicial_limite < data_final_proposta < data_final_limite) and (data_final_proposta > data_inicial_adotada): # caso a data final proposta esteja no intervalo limite e for menor que a data inicial proposta, retorna a data final proposta
        return dia_mes_ano_final_proposto
    elif (data_inicial_limite < data_final_proposta < data_final_limite) and (data_inicial_adotada > data_final_proposta): # caso esteja dentro do intervalo, mas for menor que a data inicial adotada, retorna data final limite
        return '31-08-2022'
    elif (data_final_proposta > data_inicial_adotada) and (data_final_proposta == data_final_limite):
        return '31-08-2022'
    elif data_final_proposta < data_inicial_limite:
        return '31-08-2022'

opcoes_inline_vars_climaticas = {
        'var_temp_min': 'TEMP_MIN',
        'var_temp_med': 'TEMP_MED',
        'var_temp_max': 'TEMP_MAX',
        'var_chuva': 'CHUVA',
        'var_umid_min': 'UMID_MIN',
        'var_umid_med': 'UMID_MED',
        'var_vento_med': 'VEL_VENTO_MED'}

vars_climaticas = {
    'TEMP_MIN': 'Temperatura Mínima',
    'TEMP_MED': 'Temperatura Média',
    'TEMP_MAX': 'Temperatura Máxima',
    'CHUVA': 'Chuva',
    'UMID_MIN': 'Umidade Mínima',
    'UMID_MED': 'Umidade Média',
    'VEL_VENTO_MED': 'Velocidade Média do Vento'}

def plotar_dados_estacao(userid, estacao, variavel, inicio, fim = '31-08-2022'):
    ema = pd.read_csv(f'./dados_estacoes/{estacao}/{estacao}.csv', parse_dates=['DT_MEDICAO'])
    ema.set_index('DT_MEDICAO', inplace = True)
    inicio = ajusta_data_plot(inicio)
    fim = ajusta_data_plot(fim)
    vars_climaticas = {
        'TEMP_MIN': 'Temperatura Mínima',
        'TEMP_MED': 'Temperatura Média',
        'TEMP_MAX': 'Temperatura Máxima',
        'CHUVA': 'Chuva',
        'UMID_MIN': 'Umidade Mínima',
        'UMID_MED': 'Umidade Média',
        'VEL_VENTO_MED': 'Velocidade Média do Vento'}

    rotulo_variavel_climatica = vars_climaticas[variavel]
    fig, ax = plt.subplots(figsize=(10, 10))
    if 'TEMP' in variavel:
        loc = plticker.MultipleLocator(base=1.0)
        ax.yaxis.set_major_locator(loc)
    elif 'CHUVA' in variavel:
        loc = plticker.MultipleLocator(base=10.0)
        ax.yaxis.set_major_locator(loc)
    elif 'UMID' in variavel:
        loc = plticker.MultipleLocator(base=5.0)
        ax.yaxis.set_major_locator(loc)
    elif 'VENTO' in variavel:
        loc = plticker.MultipleLocator(base=1.0)
        ax.yaxis.set_major_locator(loc)    
    
    ax = ema[f'{variavel}'][f'{inicio}':f'{fim}'].plot(figsize=(10,10), label = rotulo_variavel_climatica)
    media_movel = ema[f'{variavel}'][f'{inicio}':f'{fim}'].rolling(7).mean()
    media_movel.plot(label = 'Média Móvel')
    plt.legend(loc = 'upper right')
    ax.set_xlabel('Tempo')
    unidade = {
        'TEMP_MIN': 'Temperatura (°C)',
        'TEMP_MED': 'Temperatura (°C)',
        'TEMP_MAX': 'Temperatura (°C)',
        'CHUVA': 'Precipitação Total (mm)',
        'UMID_MIN': 'Umidade Relativa (%)',
        'UMID_MED': 'Umidade Relativa (%)',
        'VEL_VENTO_MED': 'Velocidade do Vento (m/s)'
    }
    ax.set_ylabel(f'{unidade[variavel]}')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
    for label in ax.get_xticklabels(which='major'):
        label.set(rotation=30, horizontalalignment='right')
    ax.set_xlim(left=inicio, right=fim)    
    # plt.savefig(f'imgs_plots/{nome_arquivo}.png', dpi=300, bbox_inches = "tight")
    bytes_img = BytesIO()
    plt.savefig(bytes_img, format='png', dpi=300, bbox_inches='tight')
    bytes_img.seek(0)
    bytes_img.name = f'{userid}_{estacao}_{variavel}'
    return bytes_img


municipios_rj = ['Angra dos Reis', 'Aperibé', 'Araruama', 'Areal', 'Armação dos Búzios', 'Arraial do Cabo', 'Barra do Piraí', 'Barra Mansa', 'Belford Roxo', 'Bom Jardim', 'Bom Jesus do Itabapoana', 'Cabo Frio', 'Cachoeiras de Macacu', 'Cambuci', 'Campos dos Goytacazes', 'Cantagalo', 'Carapebus', 'Cardoso Moreira', 'Carmo', 'Casimiro de Abreu', 'Comendador Levy Gasparian', 'Conceição de Macabu', 'Cordeiro', 'Duas Barras', 'Duque de Caxias', 'Engenheiro Paulo de Frontin', 'Guapimirim', 'Iguaba Grande', 'Itaboraí', 'Itaguaí', 'Italva', 'Itaocara', 'Itaperuna', 'Itatiaia', 'Japeri', 'Laje do Muriaé', 'Macaé', 'Macuco', 'Magé', 'Mangaratiba', 'Maricá', 'Mendes', 'Mesquita', 'Miguel Pereira', 'Miracema', 'Natividade', 'Nilópolis', 'Niterói', 'Nova Friburgo', 'Nova Iguaçu', 'Paracambi', 'Paraíba do Sul', 'Paraty', 'Paty do Alferes', 'Petrópolis', 'Pinheiral', 'Piraí', 'Porciúncula', 'Porto Real', 'Quatis', 'Queimados', 'Quissamã', 'Resende', 'Rio Bonito', 'Rio Claro', 'Rio das Flores', 'Rio das Ostras', 'Rio de Janeiro', 'Santa Maria Madalena', 'Santo Antônio de Pádua', 'São Fidélis', 'São Francisco de Itabapoana', 'São Gonçalo', 'São João da Barra', 'São João de Meriti', 'São José de Ubá', 'São José do Vale do Rio Preto', 'São Pedro da Aldeia', 'São Sebastião do Alto', 'Sapucaia', 'Saquarema', 'Seropédica', 'Silva Jardim', 'Sumidouro', 'Tanguá', 'Teresópolis', 'Trajano de Moraes', 'Três Rios', 'Valença', 'Varre-Sai', 'Vassouras', 'Volta Redonda']

def coordenada_municipio(municipio, coordenada):
    municipios_georef = pd.read_csv('./dados_geo/municipios_georef.csv')
    return round(list(municipios_georef[municipios_georef.municipio==municipio][coordenada])[0], 4)

def descobrir_ema_com_municipio(nome_municipio):
    latitude_municipio = coordenada_municipio(nome_municipio, 'latitude')
    longitude_municipio = coordenada_municipio(nome_municipio, 'longitude')
    estacao = busca_estacao_usando_coordenadas(latitude_municipio, longitude_municipio)
    return estacao

def limpa_dados_gerados():
    plt.close('all')
    arquivos = glob.glob('imgs_plots/*')
    for arquivo in arquivos:
        os.remove(arquivo)

msg_inicial = "Olá! Eu sou o bot <b>CLIMATER</b> e forneço visualizações de dados climáticos e séries temporais.\n\nSou um projeto de TCC da pós-graduação PAATER da UFF, criado pelo engenheiro agrônomo Daniel Alvares, sob orientação do Dr. Márcio Cataldi.\n\nPara usar nossas funções, é necessário <b>determinar um ponto de referência</b>."
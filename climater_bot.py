from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from aiogram.types import Message
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import aiogram.utils.markdown as md
from telegram import ParseMode
from aiogram.dispatcher.filters import Text
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import config # chaves particulares
import utils  # funções geradas nos notebooks para obtenção e manipulação de dados geoespaciais e climáticos

storage = MemoryStorage()
bot = Bot(token = config.token_bot)
dp = Dispatcher(bot, storage=storage)

class EMA_sessao(StatesGroup):
    ema = State()
    ema_inicio_periodo = State()
    ema_fim_periodo = State()
    ema_var_climatica = State()
    
class COORD_sessao(StatesGroup):
    coordenadas = State()
    coord_ema = State()
    coord_inicio_periodo = State()
    coord_fim_periodo = State()
    coord_var_climatica = State()

class MUNICIPIO_sessao(StatesGroup):
    municipio = State()
    municipio_inicio_periodo = State()
    municipio_fim_periodo = State()
    municipio_var_climatica = State()

class CEP_sessao(StatesGroup):
    cep = State()
    cep_inicio_periodo = State()
    cep_fim_periodo = State()
    cep_var_climatica = State()

botao_ema = InlineKeyboardButton(text='Usar Estação Meteorológica', callback_data='informa_ema') 
botao_latlong = InlineKeyboardButton(text='Usar Coordenadas Latitude Longitude', callback_data='informa_latlong')
botao_cep = InlineKeyboardButton(text='Converter CEP para Coordenadas', callback_data='informa_cep')
botao_municipio = InlineKeyboardButton(text='Usar Município como Ponto de Referência', callback_data='informa_municipio')

# Insere botões definidos no Menu Inicial do bot
menu_inicial = InlineKeyboardMarkup(resize_keyboard=True).row(botao_ema).row(botao_latlong).row(botao_cep).row(botao_municipio)

botao_temp_min = InlineKeyboardButton(text='Temperatura Mínima', callback_data='var_temp_min')
botao_temp_med = InlineKeyboardButton(text='Temperatura Média', callback_data='var_temp_med')
botao_temp_max = InlineKeyboardButton(text='Temperatura Máxima', callback_data='var_temp_max')
botao_chuva = InlineKeyboardButton(text='Chuva Total Diária', callback_data='var_chuva')
botao_umid_min = InlineKeyboardButton(text='Umidade Relativa do Ar - Mínima Diária', callback_data='var_umid_min')
botao_umid_med = InlineKeyboardButton(text='Umidade Relativa do Ar - Média Diária', callback_data='var_umid_med')
botao_vento = InlineKeyboardButton(text='Velocidade do Vento - Média Diária', callback_data='var_vento_med')

menu_vars_climaticas = InlineKeyboardMarkup(resize_keyboard=True).row(botao_temp_max).row(botao_temp_med).row(botao_temp_min).row(botao_chuva).row(botao_umid_med).row(botao_umid_min).row(botao_vento)

@dp.callback_query_handler(lambda c: c.data == 'menu_principal')
@dp.message_handler(state='*', commands=['start', 'iniciar', 'menu', 'menu_principal'])
@dp.message_handler(Text(equals=['start', 'iniciar', 'menu', 'menu_principal'], ignore_case=True), state='*')
async def inicio(msg: Message):
    await bot.send_message(msg.chat.id, utils.msg_inicial, reply_markup=menu_inicial, parse_mode='HTML')
    await bot.send_message(msg.chat.id, 'Escolha uma das opções para definir seu ponto de referência e iniciar o funcionamento do bot.', parse_mode='HTML')
    await bot.send_message(msg.chat.id, 'Para obter <b>informações</b> sobre cada opção do menu e funcionamento geral do bot, use o comando /informacoes.\n\nEm caso de <b>problemas</b> use o comando /cancelar.', parse_mode='HTML')
    
@dp.message_handler(commands=['informacoes'])
async def info_menu(msg: Message):
    await bot.send_message(msg.chat.id, utils.msg_inicial, parse_mode='HTML')
    await bot.send_message(msg.chat.id, '<b>1ª opção Usar Estação Meteorológica</b>:\nSerá necessário informar o <b>código</b> de uma estação meteorológica automática do Rio de Janeiro. Para mais informações e lista completa de estações, use o comando /lista_estacoes.\n\n<b>2ª opção Usar Coordenadas Latitude Longitude</b>:\nSerá necesário informar as <b>coordenadas geográficas</b> do ponto através da <b>latitude</b> e <b>longitude</b>, no formato <b>Grau-Minuto-Segundo</b> ou <b>Grau-Decimal</b>.\n\n<b>Importante</b>:\nCoordenadas que apontem pontos fora do Rio de Janeiro serão consideradas inválidas.', parse_mode='HTML')
    await bot.send_message(msg.chat.id, '<b>3ª opção Converter CEP para Coordenadas</b>:\nSerá necessário informar um <b>CEP</b> e essa informação será convertida numa coordenada geofráfica de referência.\n\n<b>Importante</b>:\nNão funciona para todos os CEPs, devido limitações de sistemas informativos, atendendo apenas a faixa de CEPs do Rio de Janeiro.\n\n<b>4ª opção Usar Município como Ponto de Referência</b>:\n\nSerá necessário informar o nome de um município do Rio de Janeiro. Com isso teremos a sede do município como ponto georreferenciado.', parse_mode='HTML')
    await bot.send_message(msg.chat.id, '<b>Informações adicionais</b>:\n\nApós escolher o método de referência, você precisará definir um período com duas datas, compondo o início e fim para a geração das visualizações climáticas.\n\nOs dados climáticos são provenientes da base de dados do <b>Inmet</b>, contemplando as seguintes variáveis:\n - Temperatura Máxima\n - Temperatura Média\n - Temperatura Mínima\n - Chuva Total no Dia\n - Umidade Relativa do Ar Média Diária\n - Umidade Relativa do Ar Mínima Diária\n - Velocidade do Vento Nédia Diária\n\nOs dados apresentados pelo bot apresentam falhas provinientes da coleta de dados realizada pelo Inmet, resultado de falha e interrupção de funcionamento das estações automáticas.\nNos gráficos climáticos empregamos uma <b>média móvel</b> que considera <b>7 dias anteriores</b>.\n\nPara elaboração desse projeto optamos por ofertar dados do Inmet desde o ano de 2017, sendo apenas limitados pela data inicial de operação de cada uma das estações, configurando séries temporais até <b>31 de agosto de 2022</b>.\n\nEm caso de problemas no funcionamento do bot ou simplesmente desejar cancelar alguma operação, digite /cancelar e você poderá voltar para o menu principal.\n\nVolte para o <b>menu principal</b> agora usando o comando /menu.', parse_mode='HTML')

@dp.message_handler(state='*', commands=['lista_estacoes'])
@dp.message_handler(Text(equals='lista_estacoes', ignore_case=True), state='*')
async def lista_estacoes(msg: Message, state: FSMContext):
    dados_sessao = await state.get_state()
    if dados_sessao is None:
        return await bot.send_message(msg.chat.id, f'<b>Estações Meteorológicas Automáticas</b>:\nSegue a listagem das estações disponíveis no projeto: {utils.info_estacoes_disponiveis}.\n\nVolte para o <b>menu principal</b> agora usando o comando /menu.', parse_mode='HTML')
    await bot.send_message(msg.chat.id, f'<b>Estações Meteorológicas Automáticas</b>:\nSegue a listagem das estações disponíveis no projeto: {utils.info_estacoes_disponiveis}.\n\nVolte para o <b>menu principal</b> agora usando o comando /menu.', parse_mode='HTML')
    await msg.reply('Volte para o <b>menu principal</b> agora usando o comando /menu.', parse_mode='HTML')
    await state.finish()

@dp.message_handler(state='*', commands=['cancelar', 'reiniciar', 'restart', 'voltar'])
@dp.message_handler(Text(equals='cancelar', ignore_case=True), state='*')
async def cancela_operacoes(msg: Message, state: FSMContext):
    # Possibilita cancelar operações e reseta o estado da sessão atual
    dados_sessao = await state.get_state()
    if dados_sessao is None:
        return msg.reply('Nada para ser cancelado.')
    await msg.reply('Cancelando operações!\n\nVolte para o <b>menu principal</b> agora usando o comando /menu.', parse_mode='HTML')
    await state.finish()

####################################################################################
#                          DEFINE ESTAÇÕES METEOROLÓGICAS                          #
####################################################################################

@dp.callback_query_handler(lambda c: c.data == 'informa_ema')
async def escolhe_ema(call: CallbackQuery):
    await EMA_sessao.ema.set()    
    await bot.send_message(call.message.chat.id, 'Digite o código da estação meteorológica.')

@dp.message_handler(state=EMA_sessao.ema)
async def valida_ema(msg: Message, state: FSMContext):
    async with state.proxy() as dados_sessao:
        if msg.text.strip().upper() in utils.estacoes: # valida o código inserido e registra nos dados da sessão ativa, mesmo que se digitado com letras minúsculas
            dados_sessao['ema'] = msg.text.strip().upper()
            await bot.send_message(msg.chat.id, f'A estação <b>{dados_sessao["ema"]}</b> iniciou suas operações em: <b>{utils.trata_data_completa(utils.inicio_operacao[dados_sessao["ema"]])}</b>.\nPossuímos dados registrados pelo Inmet até <b>31 de agosto de 2022</b>.', parse_mode='HTML')           
            await bot.send_photo(msg.chat.id, utils.plotar_mapa_estacao(msg.chat.id, dados_sessao['ema']))
            await bot.send_message(msg.chat.id, 'Agora informe data para definir o início da série temporal, com <b>dia</b>, <b>mês</b> e <b>ano</b> separados por um traço.\n\n<b>Exemplo</b>: 01-11-2019', parse_mode='HTML')
            await EMA_sessao.next()
        else:
            await msg.reply('<b>Código inválido</b>.\nInforme um código válido.\n\nSe não souber os códigos, use outro método ou confira os códigos das estações meteorológicas automáticas através do comando /lista_estacoes.', parse_mode='HTML')

# Valida entrada e formato de data
@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=EMA_sessao.ema_inicio_periodo)
async def valida_ema_inicio_periodo(msg: Message):
    return await msg.reply('Você precisa definir uma data informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-11-2019', parse_mode='HTML')

@dp.message_handler(state=EMA_sessao.ema_inicio_periodo)
async def define_ema_periodo_inicial(msg: Message, state: FSMContext):
    async with state.proxy() as dados_sessao:
        await state.update_data(ema_inicio_periodo=utils.valida_inicio_operacao(dados_sessao["ema"], msg.text))
        await msg.reply('Agora iremos definer o final da série temporal.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')
        await EMA_sessao.next()

# Valida entrada e formato de data
@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=EMA_sessao.ema_fim_periodo)
async def valida_ema_fim_periodo(msg: Message):
    return await msg.reply('Você precisa definir a data informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')

@dp.message_handler(state=EMA_sessao.ema_fim_periodo)
async def define_ema_fim_periodo(msg: Message, state: FSMContext):
    await bot.send_message(msg.chat.id, 'Escolha a <b>Variável Climática</b>', reply_markup=menu_vars_climaticas, parse_mode='HTML')
    async with state.proxy() as dados_sessao:
        await state.update_data(ema_fim_periodo=utils.valida_fim_operacao(dados_sessao['ema_inicio_periodo'], msg.text))
        await EMA_sessao.next()

@dp.callback_query_handler(state=EMA_sessao.ema_var_climatica)
async def define_ema_var_climatica(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as dados_sessao:
        dados_sessao['ema_var_climatica']=utils.opcoes_inline_vars_climaticas[call.data]
        
        await bot.send_message(call.message.chat.id, 
            f"<b>Estação Adotada</b>: {dados_sessao['ema']}\n<b>Intervalo Temporal</b>: {dados_sessao['ema_inicio_periodo']} até {dados_sessao['ema_fim_periodo']}\n<b>Varíavel Climática</b>: {utils.vars_climaticas[dados_sessao['ema_var_climatica']]}", parse_mode='HTML')
        await bot.send_photo(call.message.chat.id, utils.plotar_dados_estacao(call.message.chat.id, dados_sessao['ema'], dados_sessao['ema_var_climatica'], dados_sessao['ema_inicio_periodo'], dados_sessao['ema_fim_periodo']))
        await bot.send_message(call.message.chat.id, '<b>Atenção</b>:\n\nPara observar dados de outra estação meteorológica, janela temporal ou escolher uma nova variável climátic <b>é preciso retornar ao menu principal</b>.\nPara isso basta usar os comandos /menu ou /iniciar.', parse_mode='HTML')
        utils.limpa_dados_gerados()
        await state.finish()
        

####################################################################################
#                            COORDENADAS GEOGRÁFICAS                               #
####################################################################################

@dp.callback_query_handler(lambda c: c.data == 'informa_latlong')
async def latlong(call: CallbackQuery):
    await bot.send_message(call.message.chat.id,'Como definir as <b>Coordenadas Geográficas</b>.\n\nAs suas coordenadas podem ser informadas como <b>Grau-Minuto-Segundo (GMS)</b> ou <b>Grau-Decimal (GD)</b>.', parse_mode='HTML')
    await bot.send_message(call.message.chat.id, "<b>Padrão GMS</b>:\n\nTemos as informações dispostas da seguinte maneira: Latitude 22°55'3'' S e Longitude 43°5'9'' O.\nSe quiser usar esse padrão, basta fornecer os <b>dados separados por traço</b>, informando <b>latitude e longitude separados por vírgula</b>, sem a necessidade de mencionar as posições (Sul ou Oeste).\n\n<b>Exemplo</b>: 22-5-3, 42-5-3\n\n<b>Padrão GD</b>:\n\nTemos as informações dispostas da seguinte maneira: Latitude -22.9175 e Longitude -43.0858.\nSe quiser usar esse padrão, basta <b>preencher os dados sem o sinal negativo</b>, usando <b>ponto para a parte fracionada</b>, informando <b>latitude e longitude separados por vírgula</b>,.\n\n<b>Exemplo</b>: 22.9175, 43.0858\n\nOs valores são negativos pois latitudes abaixo da Linha do Equador são valores negativos, assim como valores de longitude a oeste do Meridiano de Greenwich são negativos.", parse_mode='HTML')
    await bot.send_message(call.message.chat.id, 'Informe agora a <b>latitude</b> e <b>longitude</b> da sua coordenada.', parse_mode='HTML')
    await COORD_sessao.next()

@dp.message_handler(lambda msg: not utils.valida_coordenadas(msg.text), state=COORD_sessao.coordenadas)
async def valida_coordenadas(msg: Message):
    await msg.reply('As coordenadas informadas não são válidas.\n\nInforme <b>coordenadas válidas</b> contendo latitude e longitude conforme os exemplos citados.', parse_mode='HTML')
    return await bot.send_message(msg.chat.id, 'Reveja as instruções assim como as coordenadas para o seu ponto de referência. Lembre-se que temos outros métodos para definir pontos de referência para obtenção de dados climáticos.')

@dp.message_handler(state=COORD_sessao.coordenadas)
async def processa_coordenadas(msg: Message, state: FSMContext):
    async with state.proxy() as dados_sessao:
        dados_sessao['coordenadas'] = msg.text
        coordenadas_dividida = dados_sessao['coordenadas'].split(',')
        latitude = utils.converte_gms_gd(coordenadas_dividida[0].strip())
        longitude = utils.converte_gms_gd(coordenadas_dividida[1].strip())
        dados_sessao['coord_ema'] = utils.busca_estacao_usando_coordenadas(latitude, longitude)
        await COORD_sessao.next()
        await bot.send_message(msg.chat.id, f'<b>Coordenadas Geográficas</b>\n\n<b>Latitude</b>: {latitude}\n<b>Longitude</b>: {longitude}', parse_mode='HTML')
        await bot.send_message(msg.chat.id, f'A estação mais próxima é a <b>{dados_sessao["coord_ema"]}</b>. Essa estação iniciou suas operações em: <b>{utils.trata_data_completa(utils.inicio_operacao[dados_sessao["coord_ema"]])}</b>.\n\nPossuímos dados registrados pelo Inmet até <b>31 de agosto de 2022</b>. com isso podemos criar visualizações de seus dados climáticos.', parse_mode='HTML')
        await bot.send_photo(msg.chat.id, utils.plota_mapa_coord(msg.chat.id, latitude, longitude))
        await COORD_sessao.next()
        await bot.send_message(msg.chat.id, 'Agora informe data para definir o início da série temporal, informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-11-2019', parse_mode='HTML')


@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=COORD_sessao.coord_inicio_periodo)
async def valida_periodo_inicial_coord(msg: Message):
    return await msg.reply('Você precisa definir a data informando mês e ano, separados por um traço (-).\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\nExemplo: 01-12-2019')

@dp.message_handler(state=COORD_sessao.coord_inicio_periodo)
async def define_periodo_inicial_coord(msg: Message, state: FSMContext):
    async with state.proxy() as dados_sessao:
        await state.update_data(coord_inicio_periodo=utils.valida_inicio_operacao(dados_sessao["coord_ema"], msg.text))
        await msg.reply('Agora iremos definer o final da série temporal.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')
        await COORD_sessao.next()

# Valida entrada e formato de data
@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=COORD_sessao.coord_fim_periodo)
async def valida_fim_periodo_coord(msg: Message):
    return await msg.reply('Você precisa definir a data informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')

@dp.message_handler(state=COORD_sessao.coord_fim_periodo)
async def define_periodo_final_coord(msg: Message, state: FSMContext):
    await bot.send_message(msg.chat.id, 'Agora é preciso escolher a variável climática.', reply_markup=menu_vars_climaticas)
    async with state.proxy() as dados_sessao:
        await state.update_data(coord_fim_periodo=utils.valida_fim_operacao(dados_sessao['coord_inicio_periodo'], msg.text))
        await COORD_sessao.next()

@dp.callback_query_handler(state=COORD_sessao.coord_var_climatica)
async def define_var_climatica(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as dados_sessao:
        dados_sessao['coord_var_climatica']=utils.opcoes_inline_vars_climaticas[call.data]
        
        await bot.send_message(call.message.chat.id, 
            f"<b>Estação Adotada</b>: {dados_sessao['coord_ema']}\n<b>Intervalo Temporal</b>: {dados_sessao['coord_inicio_periodo']} até {dados_sessao['coord_fim_periodo']}\n<b>Varíavel Climática</b>: {utils.vars_climaticas[dados_sessao['coord_var_climatica']]}", parse_mode='HTML')
        await bot.send_photo(call.message.chat.id, utils.plotar_dados_estacao(call.message.chat.id, dados_sessao['coord_ema'], dados_sessao['coord_var_climatica'], dados_sessao['coord_inicio_periodo'], dados_sessao['coord_fim_periodo']))
        await bot.send_message(call.message.chat.id, '<b>Atenção</b>:\n\nPara observar dados de outra estação meteorológica, janela temporal ou escolher uma nova variável climátic <b>é preciso retornar ao menu principal</b>.\nPara isso basta usar os comandos /menu ou /iniciar.', parse_mode='HTML')
        utils.limpa_dados_gerados()
        await state.finish()

####################################################################################
#                                DEFINE MUNICÍPIO                                  #
####################################################################################

@dp.callback_query_handler(lambda c: c.data == 'informa_municipio')
async def municipio(call: CallbackQuery):
    await MUNICIPIO_sessao.municipio.set()
    await bot.send_message(call.message.chat.id, 'Informe o <b>nome do município</b> do estado do Rio de Janeiro.', parse_mode='HTML')

@dp.message_handler(lambda msg: not msg.text in utils.municipios_rj, state=MUNICIPIO_sessao.municipio)
async def processa_municipio_invalido(msg: Message):
    return await msg.reply(f'O <b>município "{msg.text}"</b> é inválido. Não deve ser um município do Rio de Janeiro ou foi escrito incorretamente.\n\nInforme o nome do município <b>novamente</b>.', parse_mode='HTML')

@dp.message_handler(lambda msg: msg.text in utils.municipios_rj, state=MUNICIPIO_sessao.municipio)
async def processa_municipio(msg: Message, state: FSMContext):
    await MUNICIPIO_sessao.next()
    
    await state.update_data(municipio=msg.text)
    estacao_adotada = utils.descobrir_ema_com_municipio(msg.text)
    latitude_municipio = utils.coordenada_municipio(msg.text, "latitude")
    longitude_municipio = utils.coordenada_municipio(msg.text, "longitude")

    await bot.send_message(msg.chat.id, f'O município {msg.text} tem sua sede georreferenciada nas coordenadas latitude {latitude_municipio} longitude {longitude_municipio} e será usado como ponto de referência.\n\nA estação mais próxima é a <b>{estacao_adotada}</b>, que iniciou suas operações em: <b>{utils.trata_data_completa(utils.inicio_operacao[estacao_adotada])}</b>.', parse_mode='HTML')
    await bot.send_photo(msg.chat.id, utils.plota_mapa_coord(msg.chat.id, latitude_municipio, longitude_municipio))
    await bot.send_message(msg.chat.id, f'Informe agora o período inicial para observação das variáveis climáticas na região do <b>município {msg.text}</b>.', parse_mode='HTML')
    await bot.send_message(msg.chat.id, 'Agora informe data para definir o início da série temporal, informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-11-2019', parse_mode='HTML')
      
@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=MUNICIPIO_sessao.municipio_inicio_periodo)
async def valida_municipio_inicio_periodo(msg: Message):
    return await msg.reply('Você precisa definir a data informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-11-2019', parse_mode='HTML')

@dp.message_handler(state=MUNICIPIO_sessao.municipio_inicio_periodo)
async def define_periodo_inicial_municipio(msg: Message, state: FSMContext):
    async with state.proxy() as dados_sessao:
        await state.update_data(municipio_inicio_periodo=utils.valida_inicio_operacao(utils.descobrir_ema_com_municipio(dados_sessao["municipio"]), msg.text))
        await msg.reply('Agora iremos definer o final da série temporal.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')
        await MUNICIPIO_sessao.next()

@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=MUNICIPIO_sessao.municipio_fim_periodo)
async def valida_municipio_fim_periodo(msg: Message):
    return await msg.reply('Você precisa definir a data informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')

@dp.message_handler(state=MUNICIPIO_sessao.municipio_fim_periodo)
async def define_periodo_final_municipio(msg: Message, state: FSMContext):
    async with state.proxy() as dados_sessao:
        await state.update_data(municipio_fim_periodo=utils.valida_fim_operacao(dados_sessao['municipio_inicio_periodo'], msg.text))
        await bot.send_message(msg.chat.id, 'Agora é preciso escolher a variável climática.', reply_markup=menu_vars_climaticas)
        await MUNICIPIO_sessao.next()

@dp.callback_query_handler(state=MUNICIPIO_sessao.municipio_var_climatica)
async def define_var_climatica(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as dados_sessao:
        dados_sessao['municipio_var_climatica']=utils.opcoes_inline_vars_climaticas[call.data]
        estacao_adotada = utils.descobrir_ema_com_municipio(dados_sessao['municipio'])
        await bot.send_message(call.message.chat.id, 
            f"<b>Estação Adotada</b>: {estacao_adotada}\n<b>Intervalo Temporal</b>: {dados_sessao['municipio_inicio_periodo']} até {dados_sessao['municipio_fim_periodo']}\n<b>Varíavel Climática</b>: {utils.vars_climaticas[dados_sessao['municipio_var_climatica']]}", parse_mode='HTML')

        await bot.send_photo(call.message.chat.id, utils.plotar_dados_estacao(call.message.chat.id, estacao_adotada, dados_sessao['municipio_var_climatica'], dados_sessao['municipio_inicio_periodo'], dados_sessao['municipio_fim_periodo']))
        await bot.send_message(call.message.chat.id, '<b>Atenção</b>:\n\nPara observar dados de outra estação meteorológica, janela temporal ou escolher uma nova variável climátic <b>é preciso retornar ao menu principal</b>.\nPara isso basta usar os comandos /menu ou /iniciar.', parse_mode='HTML')
        utils.limpa_dados_gerados()
        await state.finish()

####################################################################################
#                                   DEFINE CEP                                     #
####################################################################################

@dp.callback_query_handler(lambda c: c.data == 'informa_cep')
async def cep(call: CallbackQuery):
    await CEP_sessao.cep.set()
    await bot.send_message(call.message.chat.id, 'Informe o <b>CEP</b> de um endereço do estado do Rio de Janeiro, sem usar traços ou pontos.\n\n<b>Exemplo</b>: 24342240', parse_mode='HTML')

@dp.message_handler(lambda msg: not utils.valida_cep(msg.text), state=CEP_sessao.cep)
async def processa_cep_invalido(msg: Message):
    return await msg.reply(f'<b>CEP informado "{msg.text}"</b> é inválido ou não é encontrado no sistema.\n\nVerifique o CEP, confira se foi digitado corretamente e tente novamente ou considere outra opção para buscar dados climáticos no /menu_principal.', parse_mode='HTML')

@dp.message_handler(state=CEP_sessao.cep)
async def registra_cep(msg: Message, state: FSMContext):
    await CEP_sessao.next()
    await state.update_data(cep=(msg.text).strip().replace('-', ''))
    cep_df = utils.geolocaliza_endereco(msg.text)
    latitude_cep = round(cep_df.latitude[0], 4)
    longitude_cep = round(cep_df.longitude[0], 4)
    cep_ema = utils.busca_estacao_usando_coordenadas(latitude_cep, longitude_cep)
    await bot.send_message(msg.chat.id, f'<b>Coordenadas Geográficas</b>\n\n<b>Latitude</b>: {latitude_cep}\n<b>Longitude</b>: {longitude_cep}', parse_mode='HTML')
    await bot.send_photo(msg.chat.id, utils.plota_mapa_coord(msg.chat.id, latitude_cep, longitude_cep))
    await bot.send_message(msg.chat.id, f'A estação mais próxima é a <b>{cep_ema}</b>. Essa estação iniciou suas operações em: <b>{utils.trata_data_completa(utils.inicio_operacao[cep_ema])}</b>.\n\nPossuímos dados registrados pelo Inmet até <b>31 de agosto de 2022</b>. com isso podemos criar visualizações de seus dados climáticos.', parse_mode='HTML')
    await bot.send_message(msg.chat.id, 'Agora iremos definir o início da série temporal, com <b>dia</b>, <b>mês</b> e <b>ano</b> separados por um traço.\n\n<b>Exemplo</b>: 01-11-2019', parse_mode='HTML')

@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=CEP_sessao.cep_inicio_periodo)
async def valida_inicio_periodo_cep(msg: Message):
    return await msg.reply('Você precisa definir a data informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-11-2019', parse_mode='HTML')

@dp.message_handler(state=CEP_sessao.cep_inicio_periodo)
async def define_periodo_inicial_cep(msg: Message, state: FSMContext):
    async with state.proxy() as dados_sessao:
        cep = dados_sessao['cep']
        cep_df = utils.geolocaliza_endereco(cep)
        latitude_cep = round(cep_df.latitude[0], 4)
        longitude_cep = round(cep_df.longitude[0], 4)
        cep_ema = utils.busca_estacao_usando_coordenadas(latitude_cep, longitude_cep)
        await state.update_data(cep_inicio_periodo=utils.valida_inicio_operacao(cep_ema, msg.text))
        await msg.reply('Agora iremos definer o final da série temporal.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')
        await CEP_sessao.next()

@dp.message_handler(lambda msg: not utils.valida_data(msg.text), state=CEP_sessao.cep_fim_periodo)
async def valida_fim_periodo_cep(msg: Message):
    return await msg.reply('Você precisa definir a data informando <b>dia</b>, <b>mês</b> e <b>ano</b>, separados por um traço <b>(-)</b>.\n\nÉ preciso seguir o <b>padrão do exemplo</b> para dar continuidade.\n\n<b>Exemplo</b>: 01-12-2019', parse_mode='HTML')

@dp.message_handler(state=CEP_sessao.cep_fim_periodo)
async def define_periodo_inicial_ema(msg: Message, state: FSMContext):
    await bot.send_message(msg.chat.id, 'Agora é preciso escolher a variável climática.', reply_markup=menu_vars_climaticas)
    async with state.proxy() as dados_sessao:
        await state.update_data(cep_fim_periodo=utils.valida_fim_operacao(dados_sessao['cep_inicio_periodo'], msg.text))
        await CEP_sessao.next()

@dp.callback_query_handler(state=CEP_sessao.cep_var_climatica)
async def define_var_climatica(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as dados_sessao:
        dados_sessao['cep_var_climatica']=utils.opcoes_inline_vars_climaticas[call.data]
        cep = dados_sessao['cep']
        cep_df = utils.geolocaliza_endereco(cep)
        latitude_cep = round(cep_df.latitude[0], 4)
        longitude_cep = round(cep_df.longitude[0], 4)
        cep_ema = utils.busca_estacao_usando_coordenadas(latitude_cep, longitude_cep)        
        await bot.send_message(call.message.chat.id, 
            f"<b>Estação Adotada</b>: {cep_ema}\n<b>Intervalo Temporal</b>: {dados_sessao['cep_inicio_periodo']} até {dados_sessao['cep_fim_periodo']}\n<b>Varíavel Climática</b>: {utils.vars_climaticas[dados_sessao['cep_var_climatica']]}", parse_mode='HTML')
        await bot.send_photo(call.message.chat.id, utils.plotar_dados_estacao(call.message.chat.id, cep_ema, dados_sessao['cep_var_climatica'], dados_sessao['cep_inicio_periodo'], dados_sessao['cep_fim_periodo']))
        await bot.send_message(call.message.chat.id, '<b>Atenção</b>:\n\nPara observar dados de outra estação meteorológica, janela temporal ou escolher uma nova variável climática<b> é preciso retornar ao menu principal</b>.\nPara isso basta usar os comandos /menu ou /iniciar.', parse_mode='HTML')
        utils.limpa_dados_gerados()
        await state.finish()

print('>>>>>>>>RODANDO<<<<<<<<')    

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
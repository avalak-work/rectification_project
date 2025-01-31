import glob
import pandas as pd
import numpy as np
import plotly.express as px
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from app import app

from app_data import *
from functions.column_functions import Calculations as clc
from functions.column_functions import Figures as figures
from functions.equipment_functions import Calculations as eq

#таблицы
heaters_table = pd.read_excel('tables/Параметры кожухотрубчатых теплообменников и холодильников.xlsx',
                   header=[2])
evaporator_table = pd.read_excel('tables/Параметры кожухотрубчатых испарителей и конденсаторов по ГОСТ15119-79 и ГОСТ 5121-79.xlsx',
                   header=[2])
exclude_list = ['d труб, мм']
heaters_table[exclude_list] = heaters_table[exclude_list].apply(eq.get_diameter)
evaporator_table[exclude_list] = evaporator_table[exclude_list].apply(eq.get_diameter)

def get_all_diagrams():
    def filter_diagrams(diagram):
        exclude_list = ['H2O', 'H2O_p', 'HCl']
        for substance in exclude_list:
            if substance in diagram:
                return False
        return True

    file_list = [file_name[:-5] for file_name in glob.glob('*.xlsx', root_dir='l_v')]
    diagrams_list = [[file_name[0:file_name.find('-')],file_name[file_name.find('-')+1:]] for file_name in file_list]
    diagrams = list(filter(filter_diagrams, diagrams_list))

    return diagrams
diagrams = get_all_diagrams()

def get_diagrams_options():
    diagrams_labels = []
    diagrams_values = []
    for diagram in diagrams:
        diagrams_values.append(
            diagram[0] + '-' + diagram[1])
        diagrams_labels.append(
            str(*ph_organic[ph_organic['formula'] == diagram[0]]['name'].values)
            +'-'
            +str(*ph_organic[ph_organic['formula'] == diagram[1]]['name'].values))
    return diagrams_labels, diagrams_values
diagrams_labels, diagrams_values = get_diagrams_options()

def get_heaters_dropdown():
    pipes_names = ['1', '1.5', '2', '3', '4', '6', '9']
    evaporator_pipes_names = [2,3,4,6]

    def get_heater_index(row):
        i = (str(int(row[0]))
                + ' ' + str(row[1] + np.double(0.004))
                + ' ' + str(int(row[2]))
                + ' ' + str(int(row[3])))
        return i

    def get_evaporator_index(row):
            i = (str(int(row['D кожуха, мм']))
                    + ' ' + str(row['d труб, мм'] + np.double(0.004))
                    + ' ' + str(int(row['Число ходов']))
                    + ' ' + str(int(row['Общее число труб, шт'])))
            return i
            
    evaporator = pd.DataFrame(columns=evaporator_pipes_names)
    evaporator['name'] = evaporator_table.apply(get_evaporator_index, axis=1)
    evaporator.index = evaporator['name']
    evaporator = evaporator.drop('name', axis=1)
    
    heaters = pd.DataFrame(columns=pipes_names)
    heaters['name'] = heaters_table.apply(get_heater_index, axis=1)
    heaters.index = heaters['name']
    heaters = heaters.drop('name', axis=1)
    return heaters.index, evaporator.index
heaters_label, evaporators_label = get_heaters_dropdown()
evaporators_label = list(filter(lambda x: x.split()[1] == '0.025' and x.split()[2] == '1',evaporators_label))
pipes_names = ['1', '1.5', '2', '3', '4', '6', '9']
evaporator_pipes_names = [2,3,4,6]

def get_a_name(name):
    return name[0:name.find('-')]

def get_b_name(name):
    return name[name.find('-')+1:]


Substance = {'A':Сomponent(name='Толуол'), 'B':Сomponent(name='Тетрахлорметан')}
diagram = pd.read_excel('l_v/C6H5CH3-CCl4.xlsx')

if diagram['x'].values.max() > 1:
    diagram['x'] = diagram['x']/100
    
if diagram['y'].values.max() > 1:
    diagram['y'] = diagram['y']/100
    
diagram.sort_values(by = ['t'], ascending=False,ignore_index=True, inplace=True)
xy_diagram = dfс.get_coeffs(diagram['x'], diagram['y'])

F = np.double(5)                  #Производительность по исходной смеси кг/с
FEED_TEMPERATURE = np.double(20)  #Начальная температура
FEED = np.double(0.35)            #В исходной смеси %масс Ллт 
DISTILLATE = np.double(0.98)      #В дистилляте(ректификате) %масс 
BOTTOM = np.double(0.017)         #В кубовом остатке %масс ллт
PRESSURE = np.double(10**5)       #Давление в колонне в Па. Влияет на коэфф. диффузии пара в колонне

balance = clc.material_balance(F, FEED, DISTILLATE, BOTTOM, xy_diagram, Substance)
balance.apply(lambda x: np.round(x,2))

phlegm_number_fig, R, Ngraf = clc.get_range_phlegm_number(
    balance['yf'],
    balance['xw'],
    balance['xf'],
    balance['xp'],
    balance['Rmin'],
    xy_diagram,
    diagram,
    Bt_range=20,#изменяемый параметр
    plot_type='plotly')

Ropt_fig, Ropt = clc.get_optimal_phlegm_number(R, Ngraf, plot_type='plotly')
properties = clc.calculate_properties(diagram, balance, Substance)
transfer_numbers_fig, bottom, top = clc.get_transfer_numbers(balance, Ropt, xy_diagram, plot_type='plotly')
diameter = clc.calculate_diameter(balance, Ropt, properties, filling_name='50x50x5')

height = clc.calculate_height(
    balance,
    properties,
    diameter,
    xy_diagram,
    bottom,
    top,
    Substance,
    Ropt,
    PRESSURE,
    filling_name='50x50x5')

thermal_balance = clc.calculate_thermal_balance(balance, properties, Ropt)

#выпадающие списки, слайдеры
diagram_sort_dropdown = dcc.Dropdown(
    id='diagram-sort-dropdown',
    options=['x', 'y', 't'],
    value='t')

properties_dropdown = dcc.Dropdown(
    id='properties-dropdown',
    options=[{'label':column, 'value':column} for column in properties.columns],
    value=list(properties.columns[0:6]),
    multi=True)

diagrams_dropdown = dcc.Dropdown(
    id='diagrams-dropdown',
    options=[{'label':label, 'value':value} for label,value in list(zip(diagrams_labels, diagrams_values))],
    value=diagrams_values[0])

heaters_dropdown = dcc.Dropdown(
    id='heaters-dropdown',
    options=[{'label':value, 'value':value} for value in heaters_label],
    value=heaters_label[0])

heaters_pipes_dropdown = dcc.Dropdown(
    id='heaters-pipes-dropdown',
    options=[{'label':value, 'value':value} for value in pipes_names],
    value=pipes_names[0])

evaporators_dropdown = dcc.Dropdown(
    id='evaporators-dropdown',
    options=[{'label':value, 'value':value} for value in evaporators_label],
    value=evaporators_label[0])

evaporators_pipes_dropdown = dcc.Dropdown(
    id='evaporators-pipes-dropdown',
    options=[{'label':value, 'value':value} for value in evaporator_pipes_names],
    value=evaporator_pipes_names[0])

capacitors_dropdown = dcc.Dropdown(
    id='capacitors-dropdown',
    options=[{'label':value, 'value':value} for value in heaters_label],
    value=heaters_label[0])

capacitors_pipes_dropdown = dcc.Dropdown(
    id='capacitors-pipes-dropdown',
    options=[{'label':value, 'value':value} for value in pipes_names],
    value=pipes_names[0])

distillate_coolers_dropdown = dcc.Dropdown(
    id='distillate-coolers-dropdown',
    options=[{'label':value, 'value':value} for value in heaters_label],
    value=heaters_label[0])

distillate_coolers_pipes_dropdown = dcc.Dropdown(
    id='distillate-coolers-pipes-dropdown',
    options=[{'label':value, 'value':value} for value in pipes_names],
    value=pipes_names[0])

bottom_coolers_dropdown = dcc.Dropdown(
    id='bottom-coolers-dropdown',
    options=[{'label':value, 'value':value} for value in heaters_label],
    value=heaters_label[0])

bottom_coolers_pipes_dropdown = dcc.Dropdown(
    id='bottom-coolers-pipes-dropdown',
    options=[{'label':value, 'value':value} for value in pipes_names],
    value=pipes_names[0])

ropt_slider = html.Div([
    dcc.RangeSlider(5, 30, 1, value=[20], id='ropt-range-slider')
])
heater_slider = html.Div([
    dcc.RangeSlider(1, 12, 1, value=[3], id='heater-pressure-slider')
])
evaporator_slider = html.Div([    
    dcc.RangeSlider(1, 12, 1, value=[3], id='evaporator-pressure-slider')
])
capacitor_slider = html.Div([
    dcc.RangeSlider(10, 50, 5, value=[20,30], id='capacitor-t-slider')
])

#импуты, кнопки
a_component_input = html.Div([dbc.Input(id='a-component-input', placeholder="Название компонента А", size="sm")])
b_component_input = html.Div([dbc.Input(id='b-component-input', placeholder="Название компонента Б", size="sm")])
x_input = html.Div([dbc.Input(id='x-input', placeholder="жидкая фаза, sep=' '", size="sm")])
y_input = html.Div([dbc.Input(id='y-input', placeholder="паровая фаза, sep=' '", size="sm")])
t_input = html.Div([dbc.Input(id='t-input', placeholder="температура, sep=' '", size="sm")])

calculation_inputs = html.Div(
    [html.Div('Исходные данные на проектирование'),
     dbc.Input(id='F', placeholder="производительность, кг/с", size="sm"),
     dbc.Input(id='FEED-TEMPERATURE', placeholder="температура смеси, °С", size="sm"),
     dbc.Input(id='FEED', placeholder="МАСС. доля ЛЛТ в исходной смеси", size="sm"),
     dbc.Input(id='DISTILLATE', placeholder="МАСС. доля ЛЛТ в дистилляте", size="sm"),
     dbc.Input(id='BOTTOM', placeholder="МАСС. доля ЛЛТ в кубе", size="sm"),
     dbc.Input(id='PRESSURE', placeholder="давление внутри колонны, Па (10**5)", size="sm"),
     dbc.Input(id='ROPT', placeholder="выберите флегмовое число число", size="sm"),
    ])

distillate_cooler_inputs = html.Div(
    [dbc.Input(id='distillate-cooler-aq-t', placeholder="температура воды на охлаждение ~5-20°С (по умолчанию 20)", size="sm"),
     dbc.Input(id='distillate-cooler-tk', placeholder="до какой температуры охлаждать дистиллят, °С (по умолчанию 30)", size="sm")])

bottom_cooler_inputs = html.Div(
    [dbc.Input(id='bottom-cooler-aq-t', placeholder="температура воды на охлаждение ~5-20°С (по умолчанию 20)", size="sm"),
     dbc.Input(id='bottom-cooler-tk', placeholder="до какой температуры охлаждать кубовый остаток, °С (по умолчанию 30)", size="sm")])

filling_radioitems = html.Div(
    [dbc.Label("Выберите размер насадки"),
     dbc.RadioItems(
            options=[
                {"label": "50x50x5", "value": '50x50x5'},
                {"label": '35x35x4', "value": '35x35x4'},
                {"label": '25x25x3', "value": '25x25x3'},
            ],
            value='50x50x5',
            id="filling-input",
            inline=True)])

heater_radioitems = html.Div(
    [dbc.RadioItems(
        options=[
            {"label": 'вертикальный', "value": 'вертикальный'},
            {"label": 'горизонтальный', "value": 'горизонтальный'}],
        value='вертикальный',
        id="heater-radioitems",
        inline=True )])

capacitor_radioitems = html.Div(
    [dbc.RadioItems(
        options=[
            {"label": 'вертикальный', "value": 'вертикальный'},
            {"label": 'горизонтальный', "value": 'горизонтальный'}],
        value='вертикальный',
        id="capacitor-radioitems",
        inline=True)])

distillate_cooler_radioitems = html.Div(
    [dbc.RadioItems(
        options=[
            {"label": 'продукт', "value": 'продукт'},
            {"label": 'вода', "value": 'вода'}],
        value='продукт',
        id="distillate-cooler-radioitems",
        inline=True)])

bottom_cooler_radioitems = html.Div(
    [dbc.RadioItems(
        options=[
            {"label": 'продукт', "value": 'продукт'},
            {"label": 'вода', "value": 'вода'}],
        value='продукт',
        id="bottom-cooler-radioitems",
        inline=True)])

button = html.Div([dbc.Button("Выполнить расчет", size="lg", id='main-button')])
heaters_button = html.Div([dbc.Button("Подобрать кожухотрубчатые теплообменники", size="lg", id='heaters-button')])

#фронт
filling_layout = html.Div([
    dbc.Row([dbc.Col([a_component_input], width=2),
             dbc.Col([b_component_input], width=2),
             dbc.Col([diagram_sort_dropdown], width=1),
             dbc.Col([x_input], width=2),
             dbc.Col([y_input], width=2),
             dbc.Col([t_input], width=2),             
             dbc.Col()],
            style={"margin-top":"20px"}),    
    dbc.Row([dbc.Col([html.Div('Выберите бинарную смесь '),
                      html.Div([diagrams_dropdown, calculation_inputs, filling_radioitems, html.Hr(), button])], width=3),
             dbc.Col([html.Div(id='diagram-table')], width={"size": 2, "offset": 0}),
             dbc.Col([dcc.Graph(id='diagram-figure')])]),
    html.Hr(style={"margin-bottom":"20px"}),
    dbc.Row([dbc.Col([html.Div(id='balance-table')], width={"size": 3, "offset": 0}),
             dbc.Col([html.Div('Таблица обновится после выбора свойств'),
                      html.Div(properties_dropdown),
                      html.Div(id='properties-table')], width=9)]),
    html.Hr(style={"margin-bottom":"20px"}),
    dbc.Row([dbc.Col([html.Div(ropt_slider, style={"margin-bottom":"20px"}),
                      dcc.Graph(id='range-phlegm-number-figure')], width={"size": 10, "offset": 1})]),
    html.Hr(style={"margin-bottom":"20px"}),
    dbc.Row([dbc.Col([dcc.Graph(id='ropt-figure')], width={"size": 4, "offset": 0}),
             dbc.Col([dcc.Graph(id='transfer-numbers-figure')], width={"size": 8, "offset": 0})]),
    html.Hr(style={"margin-bottom":"20px"}),
    dbc.Row([dbc.Col([html.Div(id='diameter-table'),
                      html.Hr(style={"margin-bottom":"270px"}),
                      html.Div(id='thermal-balance-table'),], width={"size": 5, "offset": 0}),
             dbc.Col([html.Div(id='height-table')], width={"size": 6, "offset": 1})]),
    html.Hr(style={"margin-bottom":"20px"}),
    dbc.Row([dbc.Col([html.Div([heaters_button])], width={"size": 4, "offset": 4}, style={"margin-bottom":"20px"})]),
    dbc.Row([dbc.Col([html.Div([heater_radioitems, heater_slider, dbc.Label("Давление водяного пара в подогревателе"),]),
                      dcc.Graph(id='heater-figure')],width={"size": 4, "offset": 0}),
             dbc.Col([html.Div([evaporator_slider, dbc.Label("Давление водяного пара в испарителе")]),
                      dcc.Graph(id='evaporator-figure')],width={"size": 4, "offset": 0}, style={"margin-top":"25px"}),
             dbc.Col([html.Div([capacitor_radioitems, capacitor_slider, dbc.Label("Температура воды на входе и выходе дефлегматора"),]),
                      dcc.Graph(id='capacitor-figure')],width={"size": 4, "offset": 0})]),
    dbc.Row([dbc.Col([html.Div([heaters_dropdown])], width={"size": 3, "offset": 0}),
             dbc.Col([html.Div([heaters_pipes_dropdown])], width={"size": 1, "offset": 0}),
             dbc.Col([html.Div([evaporators_dropdown])], width={"size": 3, "offset": 0}),
             dbc.Col([html.Div([evaporators_pipes_dropdown])], width={"size": 1, "offset": 0}),
             dbc.Col([html.Div([capacitors_dropdown])], width={"size": 3, "offset": 0}),
             dbc.Col([html.Div([capacitors_pipes_dropdown])], width={"size": 1, "offset": 0}),]),
    dbc.Row([dbc.Col([html.Div(id='heater-table')], width={"size": 4, "offset": 0}),
             dbc.Col([html.Div(id='evaporator-table')], width={"size": 4, "offset": 0}),
             dbc.Col([html.Div(id='capacitor-table')], width={"size": 4, "offset": 0}),]),
    html.Hr(style={"margin-bottom":"20px"}),
    dbc.Row([dbc.Col([html.Div([dbc.Label("Холодильник дистиллята. В трубы можно пустить продукт или воду"),
                                distillate_cooler_radioitems, distillate_cooler_inputs]),
                      dcc.Graph(id='distillate-cooler-figure')],width={"size": 6, "offset": 0}),
             dbc.Col([html.Div([dbc.Label("Холодильник кубового остатка. В трубы можно пустить продукт или воду"),
                                bottom_cooler_radioitems, bottom_cooler_inputs]),
                      dcc.Graph(id='bottom-cooler-figure')],width={"size": 6, "offset": 0})]),
    dbc.Row([dbc.Col([html.Div([distillate_coolers_dropdown])], width={"size": 5, "offset": 0}),
             dbc.Col([html.Div([distillate_coolers_pipes_dropdown])], width={"size": 1, "offset": 0}),
             dbc.Col([html.Div([bottom_coolers_dropdown])], width={"size": 5, "offset": 0}),
             dbc.Col([html.Div([bottom_coolers_pipes_dropdown])], width={"size": 1, "offset": 0})]),
    dbc.Row([dbc.Col([html.Div(id='distillate-cooler-table')], width={"size": 6, "offset": 0}),
             dbc.Col([html.Div(id='bottom-cooler-table')], width={"size": 6, "offset": 0})]),
    ],
    style={'margin-left': '10px',
           'margin-right': '10px'}
)

@app.callback(
    Output(component_id='properties-table', component_property='children'),
    Input(component_id='properties-dropdown', component_property='value')
)
def create_properties_table(properties_list):
    return dbc.Table.from_dataframe(round(properties[properties_list], 3), index=True)

@app.callback(
    Output('diagram-table', 'children'),
    Output('diagram-figure', 'figure'),
    Input('diagrams-dropdown', 'value'),
    State('a-component-input', 'value'),
    State('b-component-input', 'value'),
    Input('diagram-sort-dropdown', 'value'),
    State('x-input', 'value'),
    State('y-input', 'value'),
    State('t-input', 'value'),
)
def get_diagram(SUBSTANCE, A_COMPONENT, B_COMPONENT, SORT, LIQUID, VAPOR, TEMPERATURE):
    
    global diagram
    global Substance
    
    def ends(df, x=5):
        return pd.concat([df.head(x), df.tail(x)])
    
    #получаем черновик диаграмы
    if (A_COMPONENT == None or len(A_COMPONENT) < 1) and (B_COMPONENT == None or len(B_COMPONENT) < 1):
        path = 'l_v/'+SUBSTANCE+'.xlsx'
        diagram = pd.read_excel(path)

        if diagram['x'].values.max() > 1:
            diagram['x'] = diagram['x']/100
            
        if diagram['y'].values.max() > 1:
            diagram['y'] = diagram['y']/100
        
        
        Substance = {'A':Сomponent(name=str(*ph_organic[ph_organic.formula == get_a_name(SUBSTANCE)].name.values)),
                     'B':Сomponent(name=str(*ph_organic[ph_organic.formula == get_b_name(SUBSTANCE)].name.values))}
        
        if TEMPERATURE != None and len(TEMPERATURE) > 0:
            tails = TEMPERATURE.split(sep=',')
            for t in tails:
                if t[0][0] == '-':
                    diagram = pd.DataFrame(np.insert(diagram.values, 0, values=[0,0,t[1:]], axis=0), columns=['x','y','t'])
                elif t[0][0] == '+':
                    diagram = pd.DataFrame(np.insert(diagram.values, len(diagram), values=[1,1,t[1:]], axis=0), columns=['x','y','t'])
                else:
                    pass
        diagram.sort_values(by = [SORT], ascending=True,ignore_index=True, inplace=True)
        return (html.Div(dbc.Table.from_dataframe(df=round(ends(diagram),2), index=True)),
                figures.plot_xy_diagram(diagram, get_a_name(SUBSTANCE), plot_type='plotly'))
        
    else:
        diagram = pd.DataFrame({
            'x':[float(val) for val in LIQUID.split(sep=' ')],
            'y':[float(val) for val in VAPOR.split(sep=' ')],
            't':[float(val) for val in TEMPERATURE.split(sep=' ')]
        })
        
        diagram.sort_values(by = [SORT], ascending=True,ignore_index=True, inplace=True)
        
        Substance = {'A':Сomponent(name=A_COMPONENT),
                     'B':Сomponent(name=B_COMPONENT)}
    
    return (html.Div(dbc.Table.from_dataframe(df=round(ends(diagram),2), index=True)),
            figures.plot_xy_diagram(diagram, get_a_name(A_COMPONENT), plot_type='plotly'))
    
@app.callback(
    Output("balance-table", "children"),
    Output("range-phlegm-number-figure", "figure"),
    Output("ropt-figure", "figure"),
    Output("transfer-numbers-figure", "figure"),
    Output("diameter-table", "children"),
    Output("height-table", "children"),
    Output("thermal-balance-table", "children"),
    [State("F", "value"),
     State("FEED-TEMPERATURE", "value"),
     State("FEED", "value"),
     State("DISTILLATE", "value"),
     State("BOTTOM", "value"),
     State("PRESSURE", "value"),
     State("ROPT", 'value'),
     State("filling-input", 'value'),
     State('ropt-range-slider','value'),
     Input("main-button", "n_clicks"),
     ]
)
def on_button_click(F, FEED_TEMPERATURE, FEED, DISTILLATE, BOTTOM, PRESSURE, ROPT,
                    FILLING, BT_RANGE, BUTTON):
    
    global diagram
    global balance        
    global Substance
    global xy_diagram
    global balance
    global properties
    global thermal_balance
    global Ropt
    
    if BUTTON == 0:
        pass
    else:        
        def get_values_list(value_list):
            init_values = np.double([5, 20, 0.35, 0.98, 0.017, 10**5])
            for i,value in enumerate(init_values):
                if value_list[i] == None or len(value_list[i]) < 1:
                    value_list[i] = value
            return np.double(value_list)
        
        value_list = get_values_list([F, FEED_TEMPERATURE, FEED, DISTILLATE, BOTTOM, PRESSURE])
        F = value_list[0]
        FEED_TEMPERATURE = value_list[1]
        FEED = value_list[2]
        DISTILLATE = value_list[3]
        BOTTOM = value_list[4]
        PRESSURE = value_list[5]
        BT_RANGE = int(*BT_RANGE)
        
        xy_diagram = dfс.get_coeffs(diagram['x'], diagram['y'])
        
        balance = clc.material_balance(F, FEED, DISTILLATE, BOTTOM, xy_diagram, Substance)
        balance = balance.apply(lambda x: np.round(x,2))
        
        properties = clc.calculate_properties(diagram, balance, Substance)
        
        phlegm_number_fig, R, Ngraf = clc.get_range_phlegm_number(
            balance['yf'],
            balance['xw'],
            balance['xf'],
            balance['xp'],
            balance['Rmin'],
            xy_diagram,
            diagram,
            Bt_range=BT_RANGE,
            plot_type='plotly')
        
        Ropt_fig, Ropt = clc.get_optimal_phlegm_number(R, Ngraf, plot_type='plotly')
        Ropt_fig.update_layout(title_text='Определение рабочего флегмового числа', title_font_size=14, title_x=0.5)
                
        if ROPT != None:
            if len(ROPT) > 0:
                Ropt = np.double(ROPT)
        
        transfer_numbers_fig, bottom, top = clc.get_transfer_numbers(balance, Ropt, xy_diagram, plot_type='plotly')
        transfer_numbers_fig.update_layout(
            title_text=f'Определение числа единиц переноса. Интеграл нижней части n={bottom}, Интеграл верхней части n={top}',
            title_font_size=14, 
            title_x=0.5)
        
        diameter = clc.calculate_diameter(balance, Ropt, properties, filling_name=FILLING)
        height = clc.calculate_height(
            balance,
            properties,
            diameter,
            xy_diagram,
            bottom,
            top,
            Substance,
            Ropt,
            PRESSURE,
            filling_name=FILLING)
        thermal_balance = clc.calculate_thermal_balance(balance, properties, Ropt)
               
        return (dbc.Table.from_dataframe(balance, index=True, header=False),
                phlegm_number_fig,
                Ropt_fig,
                transfer_numbers_fig,
                dbc.Table.from_dataframe(diameter, index=True, header=False),
                dbc.Table.from_dataframe(height, index=True, header=False),
                dbc.Table.from_dataframe(thermal_balance, index=True, header=False),
                )
        
@app.callback(
    Output("heater-figure", "figure"),
    Output("evaporator-figure", "figure"),
    Output("capacitor-figure", "figure"),
    Output("distillate-cooler-figure", "figure"),
    Output("bottom-cooler-figure", "figure"),
    [State("FEED-TEMPERATURE", "value"),
     State("heater-radioitems", "value"),
     State('heater-pressure-slider', "value"),
     State('evaporator-pressure-slider', "value"),
     State("capacitor-radioitems", "value"),
     State('capacitor-t-slider', "value"),
     State("distillate-cooler-radioitems", "value"),
     State("distillate-cooler-aq-t", "value"),
     State("distillate-cooler-tk", "value"),
     State("bottom-cooler-radioitems", "value"),
     State("bottom-cooler-aq-t", "value"),
     State("bottom-cooler-tk", "value"),
     Input("heaters-button", "n_clicks"),]
    
)
def on_heaters_button_click(FEED_TEMPERATURE, HEATER_ORIENTACION, HEATER_AQ_PRESSURE, 
                            EVAPORATOR_AQ_PRESSURE, CAPACITOR_ORIENTACION, CAPACITOR_T,
                            DISTILLATE_PIPES, DISTILLATE_AQ_T, DISTILLATE_TK, 
                            BOTTOM_PIPES, BOTTOM_AQ_T, BOTTOM_TK, BUTTON):
    
    global balance        
    global Substance
    global xy_diagram
    global balance
    global properties
    global thermal_balance
    global Ropt
    
    if BUTTON == 0:
        pass
    else:
        def get_values_list(value_list):
            init_values = np.double([20, 20, 30, 20, 30])
            for i,value in enumerate(init_values):
                if value_list[i] == None or len(value_list[i]) < 1:
                    value_list[i] = value
            return np.double(value_list)
        
        value_list = get_values_list([FEED_TEMPERATURE, DISTILLATE_AQ_T, DISTILLATE_TK, BOTTOM_AQ_T, BOTTOM_TK])        
        FEED_TEMPERATURE = value_list[0]
        DISTILLATE_AQ_T = value_list[1]
        DISTILLATE_TK = value_list[2]
        BOTTOM_AQ_T = value_list[3] 
        BOTTOM_TK = value_list[4]
        
        heater = eq.calculate_equipment(
            heaters_table,
            aqua_vapor_saturation_by_pressure,
            aqua_liquid_saturation,
            aqua_vapor_saturation,
            balance,
            properties,
            FEED_TEMPERATURE,
            thermal_balance,
            Ropt,
            EQ_NAME = 'подогреватель',
            ORIENTACION = HEATER_ORIENTACION, 
            AQ_PRESSURE = int(*HEATER_AQ_PRESSURE))
        heater_figure = px.imshow(
            round(heater),
            labels=dict(x="Длина труб", y="Хараеткристики теплообменника", color=" %"),
            range_color=[-40,80],
            color_continuous_scale=["rgb(178, 50, 34)", "rgb(34, 149, 34)", "rgb(25, 65, 225)"],
            x=heater.columns,
            y=heater.index,
            text_auto=True, aspect="auto",
            #width=500,
            height=1000
                    )

        evaporator = eq.calculate_equipment(
            evaporator_table,
            aqua_vapor_saturation_by_pressure,
            aqua_liquid_saturation,
            aqua_vapor_saturation,
            balance,
            properties,
            FEED_TEMPERATURE,
            thermal_balance,
            Ropt,
            EQ_NAME = 'испаритель',
            AQ_PRESSURE = int(*EVAPORATOR_AQ_PRESSURE))
        evaporator_figure = px.imshow(
            round(evaporator),
            labels=dict(x="Длина труб", y="Хараеткристики теплообменника", color=" %"),
            range_color=[-40,80],
            color_continuous_scale=["rgb(178, 50, 34)", "rgb(34, 149, 34)", "rgb(25, 65, 225)"],
            x=evaporator.columns,
            y=evaporator.index,
            text_auto=True, aspect="auto",
            #width=500,
            height=1000
                    )
        
        capacitor = eq.calculate_equipment(
            heaters_table,
            aqua_vapor_saturation_by_pressure,
            aqua_liquid_saturation,
            aqua_vapor_saturation,
            balance,
            properties,
            FEED_TEMPERATURE,
            thermal_balance,
            Ropt,
            EQ_NAME = 'дефлегматор',
            ORIENTACION=CAPACITOR_ORIENTACION,
            Tn=CAPACITOR_T[0],
            Tk=CAPACITOR_T[1]
            )
        capacitor_figure = px.imshow(
            round(capacitor),
            labels=dict(x="Длина труб", y="Хараеткристики теплообменника", color=" %"),
            range_color=[-40,80],
            color_continuous_scale=["rgb(178, 50, 34)", "rgb(34, 149, 34)", "rgb(25, 65, 225)"],
            x=capacitor.columns,
            y=capacitor.index,
            text_auto=True, aspect="auto",
            #width=500,
            height=1000
            )
    
        distillate_cooler = eq.calculate_equipment(
            heaters_table,
            aqua_vapor_saturation_by_pressure,
            aqua_liquid_saturation,
            aqua_vapor_saturation,
            balance,
            properties,
            FEED_TEMPERATURE,
            thermal_balance,
            Ropt,
            EQ_NAME = 'холодильник',
            COOLER_NAME = 'дистиллята',
            pipes = DISTILLATE_PIPES,
            aq_t = DISTILLATE_AQ_T, 
            tk = DISTILLATE_TK
            )
        distillate_cooler_figure = px.imshow(
            round(distillate_cooler),
            labels=dict(x="Длина труб", y="Хараеткристики теплообменника", color=" %"),
            range_color=[-40,80],
            color_continuous_scale=["rgb(178, 50, 34)", "rgb(34, 149, 34)", "rgb(25, 65, 225)"],
            x=distillate_cooler.columns,
            y=distillate_cooler.index,
            text_auto=True, aspect="auto",
            #width=500,
            height=1000
            )
        
        bottom_cooler = eq.calculate_equipment(
            heaters_table,
            aqua_vapor_saturation_by_pressure,
            aqua_liquid_saturation,
            aqua_vapor_saturation,
            balance,
            properties,
            FEED_TEMPERATURE,
            thermal_balance,
            Ropt,
            EQ_NAME = 'холодильник',
            COOLER_NAME = 'куба',
            pipes = BOTTOM_PIPES, #изменяемый параметр может быть 'вода'
            aq_t = BOTTOM_AQ_T, #изменяемый параметр
            tk = BOTTOM_TK #изменяемый параметр
            )
        bottom_cooler_figure = px.imshow(
            round(bottom_cooler),
            labels=dict(x="Длина труб", y="Хараеткристики теплообменника", color="%"),
            range_color=[-40,80],
            color_continuous_scale=["rgb(178, 50, 34)", "rgb(34, 149, 34)", "rgb(25, 65, 225)"],
            x=bottom_cooler.columns,
            y=bottom_cooler.index,
            text_auto=True, aspect="auto",
            #width=500,
            height=1000
            )
        
        return (heater_figure,
                evaporator_figure,
                capacitor_figure,
                distillate_cooler_figure,
                bottom_cooler_figure)
        
@app.callback(
    Output(component_id='heater-table', component_property='children'),
    [State("FEED-TEMPERATURE", "value"),
     Input("heater-radioitems", "value"),
     Input('heater-pressure-slider', "value"),
     Input("heaters-dropdown", "value"),
     Input("heaters-pipes-dropdown", "value"),
     ]
)
def create_heater_table(FEED_TEMPERATURE, HEATER_ORIENTACION, HEATER_AQ_PRESSURE, HEATER_MODEL, PIPES):
    global balance
    global properties
    global Ropt
    
    def get_values_list(value_list):
            init_values = np.double([20])
            for i,value in enumerate(init_values):
                if value_list[i] == None or len(value_list[i]) < 1:
                    value_list[i] = value
            return np.double(value_list)
        
    value_list = get_values_list([FEED_TEMPERATURE])
    FEED_TEMPERATURE = value_list[0]
    
    row = heaters_table[heaters_table[heaters_table.columns[3]] == int(HEATER_MODEL.split()[3])].squeeze()
    if len(row) > 1 and len(row) < 14:
        row = row[row[row.columns[0]] == int(HEATER_MODEL.split()[0])].squeeze()
    
    if row[PIPES] == '—':
        return
    heater = eq.get_heater(row,
        PIPES,
        aqua_vapor_saturation_by_pressure,
        aqua_liquid_saturation,
        aqua_vapor_saturation,
        balance, properties,
        FEED_TEMPERATURE,
        Ropt,
        ORIENTACION=HEATER_ORIENTACION,
        AQ_PRESSURE=int(*HEATER_AQ_PRESSURE), 
        call='app')
    
    return dbc.Table.from_dataframe(heater, index=True, header=False)

@app.callback(
    Output(component_id='evaporator-table', component_property='children'),
    [Input('evaporator-pressure-slider', "value"),     
     Input("evaporators-dropdown", "value"),
     Input("evaporators-pipes-dropdown", "value"),
     ]
)
def create_evaporator_table(EVAPOREATOR_AQ_PRESSURE, EVAPORATOR_MODEL, PIPES):
    global properties
    global thermal_balance
    
    row = evaporator_table[evaporator_table[evaporator_table.columns[3]] == int(EVAPORATOR_MODEL.split()[3])].squeeze()
    if row[PIPES] == '—':
        return
        
    evaporator = eq.get_evaporator(row,
            int(PIPES),                  
            aqua_vapor_saturation_by_pressure, 
            aqua_liquid_saturation,
            aqua_vapor_saturation,
            properties,
            thermal_balance,
            AQ_PRESSURE = int(*EVAPOREATOR_AQ_PRESSURE),
            call = 'direct')
    
    return dbc.Table.from_dataframe(evaporator, index=True, header=False)

@app.callback(
    Output(component_id='capacitor-table', component_property='children'),
    [Input("capacitor-radioitems", "value"),
     Input('capacitor-t-slider', "value"),
     Input("capacitors-dropdown", "value"),
     Input("capacitors-pipes-dropdown", "value"),
     ]
)
def create_capacitor_table(CAPACITOR_ORIENTACION, CAPACITOR_T, CAPACITOR_MODEL, PIPES):
    global balance
    global Ropt
    global properties
    
    row = heaters_table[heaters_table[heaters_table.columns[3]] == int(CAPACITOR_MODEL.split()[3])].squeeze()
    if len(row) > 1 and len(row) < 14:
        row = row[row[row.columns[0]] == int(CAPACITOR_MODEL.split()[0])].squeeze()
        
    if row[PIPES] == '—':
        return
    
    capacitor = eq.get_capacitor(
        row,
        PIPES,        
        aqua_liquid_saturation,        
        thermal_balance,
        balance,
        properties,        
        Ropt,
        Tn=CAPACITOR_T[0],
        Tk=CAPACITOR_T[1],
        ORIENTACION = CAPACITOR_ORIENTACION,
        call = 'direct')
    
    return dbc.Table.from_dataframe(capacitor, index=True, header=False)

@app.callback(
    Output(component_id='bottom-cooler-table', component_property='children'),
    [Input("bottom-cooler-radioitems", "value"),
     Input("bottom-cooler-aq-t", "value"),
     Input("bottom-cooler-tk", "value"),
     Input("bottom-coolers-dropdown", "value"),
     Input("bottom-coolers-pipes-dropdown", "value"),
     ]
)
def create_bottom_cooler_table(BOTTOM_PIPES, BOTTOM_AQ_T, BOTTOM_TK, BOTTOM_MODEL, PIPES):
    global balance
    global properties    
    
    def get_values_list(value_list):
            init_values = np.double([20, 30])
            for i,value in enumerate(init_values):
                if value_list[i] == None or len(value_list[i]) < 1:
                    value_list[i] = value
            return np.double(value_list)
        
    value_list = get_values_list([BOTTOM_AQ_T, BOTTOM_TK])
    BOTTOM_AQ_T = value_list[0]
    BOTTOM_TK = value_list[1]
    
    row = heaters_table[heaters_table[heaters_table.columns[3]] == int(BOTTOM_MODEL.split()[3])].squeeze()
    if len(row) > 1 and len(row) < 14:
        row = row[row[row.columns[0]] == int(BOTTOM_MODEL.split()[0])].squeeze()
    
    bottom_cooler = eq.get_cooler(
        row,
        PIPES,
        aqua_liquid_saturation,
        aqua_vapor_saturation,
        properties,
        balance,
        COOLER_NAME = 'куба',
        pipes = BOTTOM_PIPES,
        aq_t = int(BOTTOM_AQ_T),
        tk = int(BOTTOM_TK),
        call = 'direct')
    
    return dbc.Table.from_dataframe(bottom_cooler, index=True, header=False)

@app.callback(
    Output(component_id='distillate-cooler-table', component_property='children'),
    [Input("distillate-cooler-radioitems", "value"),
     Input("distillate-cooler-aq-t", "value"),
     Input("distillate-cooler-tk", "value"),
     Input("distillate-coolers-dropdown", "value"),
     Input("distillate-coolers-pipes-dropdown", "value"),
     ]
)
def create_distillate_cooler_table(DISTILLATE_PIPES, DISTILLATE_AQ_T, DISTILLATE_TK, DISTILLATE_MODEL, PIPES):
    global balance
    global properties    
    
    def get_values_list(value_list):
            init_values = np.double([20, 30])
            for i,value in enumerate(init_values):
                if value_list[i] == None or len(value_list[i]) < 1:
                    value_list[i] = value
            return np.double(value_list)
        
    value_list = get_values_list([DISTILLATE_AQ_T, DISTILLATE_TK])
    DISTILLATE_AQ_T = value_list[0]
    DISTILLATE_TK = value_list[1]
    
    row = heaters_table[heaters_table[heaters_table.columns[3]] == int(DISTILLATE_MODEL.split()[3])].squeeze()
    if len(row) > 1 and len(row) < 14:
        row = row[row[row.columns[0]] == int(DISTILLATE_MODEL.split()[0])].squeeze()
    
    distillate_cooler = eq.get_cooler(
        row,
        PIPES,
        aqua_liquid_saturation,
        aqua_vapor_saturation,
        properties,
        balance,
        COOLER_NAME = 'дистиллята',
        pipes = DISTILLATE_PIPES,
        aq_t = int(DISTILLATE_AQ_T),
        tk = int(DISTILLATE_TK),
        call = 'direct')
    
    return dbc.Table.from_dataframe(distillate_cooler, index=True, header=False)
    
    
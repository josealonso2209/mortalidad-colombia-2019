"""Dashboard Dash de mortalidad no fetal en Colombia durante 2019.
Ejecutar: python estadistica.py. Producción: gunicorn estadistica:server.
"""
from pathlib import Path
import json
import os
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, dash_table
from analisis import ROOT, MESES, EDADES, SEXO, cargar_datos, filtrar, resumir

APP_TITLE='Mortalidad en Colombia · 2019'
BLUE='#2463A6'
COLORS={'Hombres':'#2463A6','Mujeres':'#D8793B','Indeterminado':'#8E73AA','Sin información':'#6B7280'}
DF=cargar_datos()
GEO_PATH=ROOT/'data/colombia.geo.json'
GEO=json.loads(GEO_PATH.read_text(encoding='utf-8')) if GEO_PATH.exists() else None
# Coordenadas de referencia de las capitales, solo para respaldo sin GeoJSON.
CENTROS={5:(6.24,-75.58),8:(10.98,-74.80),11:(4.71,-74.07),13:(10.40,-75.51),15:(5.54,-73.36),17:(5.07,-75.51),18:(1.61,-75.61),19:(2.44,-76.61),20:(10.46,-73.25),23:(8.75,-75.88),25:(4.90,-74.30),27:(5.69,-76.66),41:(2.93,-75.28),44:(11.54,-72.91),47:(11.24,-74.20),50:(4.14,-73.63),52:(1.21,-77.28),54:(7.89,-72.50),63:(4.53,-75.68),66:(4.81,-75.69),68:(7.12,-73.12),70:(9.30,-75.40),73:(4.44,-75.23),76:(3.45,-76.53),81:(7.08,-70.76),85:(5.34,-72.40),86:(1.15,-76.65),88:(12.58,-81.70),91:(-4.21,-69.94),94:(3.87,-67.92),95:(2.57,-72.65),97:(1.25,-70.23),99:(6.19,-67.49)}


def estilo(f, height=400):
    f.update_layout(template='plotly_white',font=dict(family='Arial, sans-serif',color='#24364B',size=12),
                    paper_bgcolor='white',plot_bgcolor='white',height=height,
                    margin=dict(l=65,r=25,t=20,b=65),separators=',.',
                    legend=dict(orientation='h',y=-.20,x=0),uirevision='2019')
    f.update_xaxes(showgrid=False,automargin=True)
    f.update_yaxes(gridcolor='#E8EDF3',automargin=True,rangemode='tozero',tickformat=',d')
    return f


def vacio(mensaje='Sin registros para esta selección'):
    f=go.Figure().add_annotation(text=mensaje,x=.5,y=.5,xref='paper',yref='paper',showarrow=False,font=dict(size=16))
    f.update_xaxes(visible=False);f.update_yaxes(visible=False)
    return estilo(f)


def figuras(r,meses=None):
    if not r['total']: return [vacio() for _ in range(6)]
    dep=r['departamentos']
    if GEO:
        mapa=go.Figure(go.Choropleth(geojson=GEO,locations=dep.COD_DEPARTAMENTO.astype(str).str.zfill(2),
            featureidkey='properties.COD_DPTO',z=dep.TOTAL,colorscale='Blues',
            text=dep.DEPARTAMENTO.astype(str),zmin=0,zmax=max(int(dep.TOTAL.max()),1),colorbar=dict(title='Muertes',tickformat=',d'),
            hovertemplate='<b>%{text}</b><br>Defunciones: %{z:,.0f}<extra></extra>',marker_line_width=.5,marker_line_color='white'))
        mapa.update_geos(fitbounds='geojson',visible=False,projection_type='mercator')
    else:
        mapa=go.Figure(go.Scattergeo(lat=[CENTROS[int(x)][0] for x in dep.COD_DEPARTAMENTO],
            lon=[CENTROS[int(x)][1] for x in dep.COD_DEPARTAMENTO],text=dep.DEPARTAMENTO.astype(str),
            customdata=dep.TOTAL,mode='markers',marker=dict(size=dep.TOTAL.pow(.5)/6+7,color=dep.TOTAL,
            colorscale='Blues',showscale=True,colorbar=dict(title='Muertes'),line=dict(color='white',width=1)),
            hovertemplate='<b>%{text}</b><br>Defunciones: %{customdata:,.0f}<extra></extra>'))
        mapa.update_geos(visible=False,projection_type='mercator',lataxis_range=[-5,14],lonaxis_range=[-83,-66])
    estilo(mapa,470);mapa.update_layout(margin=dict(l=0,r=0,t=0,b=0))
    mes=r['meses'].copy()
    # Meses excluidos del filtro se representan como huecos, no como ceros observados.
    y=[None if meses and m not in meses else int(n) for m,n in zip(mes.MES,mes.TOTAL)]
    linea=go.Figure(go.Scatter(x=mes.NOMBRE_MES,y=y,mode='lines+markers',connectgaps=False,
        line=dict(color=BLUE,width=3),marker=dict(size=7),hovertemplate='%{x}<br>Defunciones: %{y:,.0f}<extra></extra>'))
    estilo(linea);linea.update_xaxes(title='Mes de ocurrencia',tickangle=-35);linea.update_yaxes(title='Defunciones')
    v=r['violentas'].iloc[::-1]
    barras=vacio('Sin defunciones con código X95 en esta selección') if v.empty else go.Figure(go.Bar(
        x=v.TOTAL,y=v.MUNICIPIO.astype(str)+'<br>'+v.DEPARTAMENTO.astype(str),orientation='h',marker_color=BLUE,text=v.TOTAL,textposition='outside',
        cliponaxis=False,hovertemplate='%{y}<br>Casos X95: %{x:,.0f}<extra></extra>'))
    estilo(barras);barras.update_layout(margin=dict(l=25,r=55,t=20,b=55));barras.update_xaxes(title='Defunciones con código X95')
    menores=r['menores']
    pie=go.Figure(go.Pie(labels=menores.LUGAR.astype(str),values=menores.TOTAL,hole=.52,sort=False,
        textinfo='value',marker=dict(colors=['#164D7A','#2463A6','#3E80BC','#5C99CC','#80B4DB','#D8793B','#EAA267','#8E73AA','#5C8B79','#B89C51']),
        hovertemplate='%{label}<br>Defunciones: %{value}<br>%{percent} del grupo mostrado<extra></extra>'))
    estilo(pie,460);pie.update_layout(legend=dict(orientation='v',x=1,y=1,font=dict(size=10)),margin=dict(l=10,r=10,t=15,b=15))
    apiladas=go.Figure()
    orden=dep.DEPARTAMENTO.astype(str).tolist()
    for s in SEXO.values():
        sub=r['sexo'].loc[r['sexo'].SEXO_DESC==s]
        if len(sub): apiladas.add_bar(name=s,x=sub.DEPARTAMENTO.astype(str),y=sub.TOTAL,marker_color=COLORS[s],
           hovertemplate='%{x}<br>'+s+': %{y:,.0f}<extra></extra>')
    estilo(apiladas,490);apiladas.update_layout(barmode='stack',legend=dict(orientation='h',y=1.10,x=0),margin=dict(l=65,r=20,t=30,b=120))
    apiladas.update_xaxes(title='Departamento',categoryorder='array',categoryarray=orden,tickangle=-50, tickmode='array',tickvals=orden,ticktext=[('San Andrés y Providencia' if x.startswith('ARCHIPIÉLAGO') else x.title()) for x in orden],tickfont=dict(size=10))
    apiladas.update_yaxes(title='Defunciones')
    # Histograma de frecuencias preagrupadas: todos los intervalos definidos,
    # con barras contiguas y orden fijo. Evita enviar 244.355 filas al cliente.
    edad=r['edad']
    hist=go.Figure(go.Bar(x=edad.CATEGORIA_EDAD.astype(str),y=edad.TOTAL,text=edad.TOTAL,
        texttemplate='%{text:,.0f}',textposition='outside',cliponaxis=False,marker_color=BLUE,
        customdata=[f'Códigos {a}–{b}: {rango}' for _,a,b,rango in EDADES],
        hovertemplate='%{x}<br>%{customdata}<br>Defunciones: %{y:,.0f}<extra></extra>'))
    estilo(hist,430);hist.update_layout(bargap=.04,margin=dict(l=65,r=20,t=35,b=100))
    hist.update_xaxes(title='Categoría de GRUPO_EDAD1',tickangle=-35);hist.update_yaxes(title='Defunciones')
    return [mapa,linea,barras,pie,apiladas,hist]


app=Dash(__name__,title=APP_TITLE,assets_folder=str(ROOT/'assets'),update_title='Actualizando…')
server=app.server

@server.get('/healthz')
def healthz(): return {'status':'ok','registros':len(DF),'anio':2019}

CONFIG={'topojsonURL':'/assets/','responsive':True,'displaylogo':False,'toImageButtonOptions':{'format':'png','scale':2}}
IDS=['mapa','linea','violentas','menores','sexo-dep','edad']

def panel(id,titulo,nota):
    return html.Section([html.H2(titulo),html.P(nota,className='nota'),dcc.Graph(id=id,config=CONFIG,style={'height':str({'mapa':470,'linea':470,'violentas':460,'menores':460,'sexo-dep':570,'edad':460}[id])+'px'})],className='panel',id='panel-'+id)


def control(nombre,id,options):
    return html.Div([html.Label(nombre,htmlFor=id),dcc.Dropdown(id=id,options=options,value=[],multi=True,placeholder='Todos',clearable=True)],className='control')

DEPS=DF[['COD_DEPARTAMENTO','DEPARTAMENTO']].drop_duplicates().sort_values('DEPARTAMENTO')
app.layout=html.Div([
    html.Header([html.Div('ESTADÍSTICAS VITALES / ANÁLISIS DESCRIPTIVO',className='eyebrow'),
                 html.H1('Mortalidad en Colombia'),html.P('2019 · Defunciones no fetales',className='subtitle'),
                 html.P('Explora la distribución territorial, temporal y demográfica de 244.355 registros.',className='intro')]),
    html.Main([
        html.Section([
            html.Div([html.H2('Explorar los datos'),html.Button('Restablecer filtros',id='reset',n_clicks=0)],className='section-head'),
            html.Div([
                control('Departamento','f-dep',[{'label':str(r.DEPARTAMENTO),'value':int(r.COD_DEPARTAMENTO)} for r in DEPS.itertuples()]),
                control('Mes','f-mes',[{'label':v,'value':k} for k,v in MESES.items()]),
                control('Sexo','f-sexo',[{'label':v,'value':k} for k,v in SEXO.items() if k in DF.SEXO.unique()]),
                control('Ciclo de vida','f-edad',[{'label':n,'value':n} for n,_,_,_ in EDADES]),
            ],className='filters'),
            html.P('Combina filtros para actualizar todas las visualizaciones. Una selección vacía incluye todas las categorías.',className='nota'),
        ],className='filter-panel'),
        html.Div(id='contexto',className='contexto',role='status'),
        html.Div([html.Div([html.Strong(id='kpi-total'),html.Span('Defunciones')],className='kpi'),
                  html.Div([html.Strong(id='kpi-dep'),html.Span('Departamentos y Bogotá D. C.')],className='kpi'),
                  html.Div([html.Strong(id='kpi-mun'),html.Span('Unidades territoriales con registros')],className='kpi'),
                  html.Div([html.Strong(id='kpi-x95'),html.Span('Defunciones con código X95')],className='kpi')],className='kpis'),
        html.Div([
            panel('mapa','1 Distribución por departamento','Conteos por lugar de ocurrencia. Bogotá D. C. se presenta separada de Cundinamarca.'),
            panel('linea','2 Comportamiento mensual','Totales por mes. La duración de los meses influye en los conteos; no se infiere estacionalidad de un solo año.'),
        ],className='charts-grid'),
        html.Div([
            panel('violentas','3 Cinco municipios con más casos X95','Incluye X95 y sus subcategorías. Ranking por conteo de agresiones con otras armas de fuego y las no especificadas; no representa la totalidad de homicidios.'),
            panel('menores','4 Diez municipios con menos defunciones','Solo unidades con al menos un registro. Empates por nombre y departamento. Los porcentajes corresponden a estos diez municipios; no son tasas poblacionales.'),
        ],className='charts-grid'),
        html.Section([html.H2('5 Diez principales causas de muerte'),
            html.P('Códigos completos CIE-10 ordenados por número de registros. Desplaza la tabla para leer las descripciones.',className='nota'),
            dash_table.DataTable(id='causas',columns=[{'name':'Código CIE-10','id':'CODIGO'},
                {'name':'Causa de muerte','id':'DESCRIPCION'},{'name':'Defunciones','id':'TOTAL','type':'numeric'}],
                page_size=10,sort_action='native',sort_by=[{'column_id':'TOTAL','direction':'desc'}],
                style_table={'overflowX':'auto'},style_cell={'fontFamily':'Arial','fontSize':13,'padding':'12px','textAlign':'left','whiteSpace':'normal','height':'auto'},
                style_cell_conditional=[{'if':{'column_id':'CODIGO'},'width':'110px'},{'if':{'column_id':'TOTAL'},'textAlign':'right','width':'110px'}],
                style_header={'backgroundColor':'#E8F0F8','fontWeight':'bold','border':'1px solid #DAE3ED'},
                style_data_conditional=[{'if':{'row_index':'odd'},'backgroundColor':'#F7FAFD'}]),
        ],className='panel',id='panel-causas'),
        panel('sexo-dep','6 Defunciones por sexo y departamento','Barras apiladas en orden descendente del total departamental. Haz clic en la leyenda para mostrar u ocultar una categoría.'),
        panel('edad','7 Distribución por ciclo de vida','Histograma de frecuencias por intervalos de códigos GRUPO_EDAD1. Los códigos no representan años de edad.'),
        html.Details([html.Summary('Metodología y límites del análisis'),
            html.P('Cada fila equivale a una defunción no fetal de 2019. La geografía corresponde al lugar de ocurrencia registrado y no necesariamente al de residencia. Los municipios se identifican mediante el código DANE completo; se incluyen áreas no municipalizadas presentes en el archivo.'),
            html.P('El gráfico de menores conteos muestra las diez unidades territoriales con menor número positivo de defunciones. No se dispone de población para calcular tasas por 100.000 habitantes. Los municipios sin registros no se consideran municipios con cero defunciones.'),
            html.P('El código X95 identifica agresión con disparo de otras armas de fuego y las no especificadas. Excluye, entre otras causas, X93, X94 y agresiones con otros medios. Un conteo alto no prueba mayor riesgo individual.'),
            html.Table([html.Thead(html.Tr([html.Th('Categoría'),html.Th('Códigos'),html.Th('Edad aproximada')])),html.Tbody([
                html.Tr([html.Td(n),html.Td(str(a) if a==b else f'{a}–{b}'),html.Td(r)]) for n,a,b,r in EDADES])]),
            html.P(id='mapa-nota'),
        ],className='panel'),
        html.Footer([html.P('Fuente estadística: DANE · Estadísticas Vitales 2019. Integración de defunciones no fetales, DIVIPOLA y catálogo CIE-10.'),
                     html.A('Consultar cifras definitivas del DANE',href='https://www.dane.gov.co/files/investigaciones/poblacion/cifras-definitivas-2019.pdf',target='_blank')]),
    ])
],className='app-shell')


@app.callback([Output(i,'value') for i in ['f-dep','f-mes','f-sexo','f-edad']],Input('reset','n_clicks'),prevent_initial_call=True)
def resetear(_): return [],[],[],[]


@app.callback([Output(i,'figure') for i in IDS]+[Output('causas','data')]+[Output(i,'children') for i in ['kpi-total','kpi-dep','kpi-mun','kpi-x95','contexto','mapa-nota']],
              [Input(i,'value') for i in ['f-dep','f-mes','f-sexo','f-edad']])
def actualizar(deps,meses,sexos,edades):
    data=filtrar(DF,deps,meses,sexos,edades)
    r=resumir(data)
    conteo=f"{r['total']:,}".replace(',','.')
    proporcion=f"{100*r['total']/len(DF):.2f}".replace('.',',')
    contexto=f"Selección actual: {conteo} defunciones de 2019 ({proporcion} % de la base)."
    if not r['total']: contexto='Sin registros para esta combinación de filtros. Prueba otra selección o restablece los filtros.'
    nota='Mapa con polígonos departamentales incluidos en el proyecto.' if GEO else 'Respaldo geográfico por puntos de referencia de las capitales; no representa límites departamentales.'
    return figuras(r,meses)+[r['causas'].to_dict('records')]+[f"{r[k]:,}".replace(',','.') for k in ['total','n_departamentos','municipios','x95']]+[contexto,nota]


if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','8050')),debug=os.getenv('DASH_DEBUG','0')=='1')

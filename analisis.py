"""Carga validada y agregaciones de defunciones no fetales de 2019."""
from pathlib import Path
import os
import pandas as pd

ROOT = Path(__file__).resolve().parent
MESES = dict(enumerate(['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'], 1))
# Los intervalos son códigos GRUPO_EDAD1, no edades expresadas en años.
EDADES = [
    ('Mortalidad neonatal',0,4,'Menor de 1 mes'),
    ('Mortalidad infantil',5,6,'1 a 11 meses'),
    ('Primera infancia',7,8,'1 a 4 años'),
    ('Niñez',9,10,'5 a 14 años'),
    ('Adolescencia',11,11,'15 a 19 años'),
    ('Juventud',12,13,'20 a 29 años'),
    ('Adultez temprana',14,16,'30 a 44 años'),
    ('Adultez intermedia',17,19,'45 a 59 años'),
    ('Vejez',20,24,'60 a 84 años'),
    ('Longevidad y centenarios',25,28,'85 a 100 años o más'),
    ('Edad desconocida',29,29,'Sin información'),
]
SEXO = {1:'Hombres',2:'Mujeres',3:'Indeterminado',9:'Sin información'}
REQ = ['COD_DANE','COD_DEPARTAMENTO','COD_MUNICIPIO','AÑO','DEPARTAMENTO','MUNICIPIO','MES','SEXO','GRUPO_EDAD1','COD_MUERTE']


def clasificar_edad(codigo):
    try:
        n = float(codigo)
        if not n.is_integer(): return 'Edad desconocida'
        for nombre,a,b,_ in EDADES:
            if a <= n <= b: return nombre
    except (TypeError,ValueError,OverflowError): pass
    return 'Edad desconocida'


def cargar_datos(path=None):
    """No elimina filas idénticas: no hay identificador único de certificado."""
    if path is None:
        override = os.getenv('DATA_FILE')
        path = Path(override).expanduser() if override else next((p for p in [ROOT/'data/mortalidad_2019.csv',ROOT/'data/mortalidad_2019.csv.gz',ROOT/'data/registros'] if p.exists()), ROOT/'data/registros')
        if not path.is_absolute(): path = ROOT/path
    path = Path(path)
    if not path.exists(): raise FileNotFoundError(f'No se encontró la base: {path}')
    # Solo se leen variables usadas; los microdatos nunca se envían al navegador.
    if path.is_dir():
        partes=sorted(path.rglob('parte*.csv'))
        if not partes:raise FileNotFoundError('No hay particiones CSV en '+str(path))
        d=pd.concat([pd.read_csv(f) for f in partes],ignore_index=True)
        if set(d.columns)!={'COD_DANE','MES','SEXO','GRUPO_EDAD1','COD_MUERTE'}:raise ValueError('Esquema de particiones incorrecto.')
        d['COD_DEPARTAMENTO']=d.COD_DANE//1000
        d['COD_MUNICIPIO']=d.COD_DANE%1000
        d['AÑO']=2019
        geo=pd.read_csv(ROOT/'data/catalogos/territorios.csv')
        cat=pd.read_csv(ROOT/'data/catalogos/causas.csv')
        d=d.merge(geo,on='COD_DANE',how='left',validate='many_to_one',sort=False)
        d=d.merge(cat,on='COD_MUERTE',how='left',validate='many_to_one',sort=False)
        d['TOTAL']=1
    elif path.name.lower().endswith(('.csv','.csv.gz')):
        d = pd.read_csv(path, usecols=lambda c: c in REQ+['TOTAL','NOMBRE_CAUSA','NOMBRE_MUERTE','NOMBRE_MUERTE_x','NOMBRE_MUERTE_y'], low_memory=False)
    else: d = pd.read_excel(path, engine='openpyxl')
    missing = set(REQ)-set(d.columns)
    if missing: raise ValueError('Faltan columnas: '+', '.join(sorted(missing)))
    for c in ['COD_DANE','COD_DEPARTAMENTO','COD_MUNICIPIO','AÑO','MES','SEXO','GRUPO_EDAD1']:
        d[c]=pd.to_numeric(d[c],errors='raise').astype('int64')
    if not d['AÑO'].eq(2019).all(): raise ValueError('La base debe contener únicamente 2019.')
    if not d.MES.between(1,12).all(): raise ValueError('Mes fuera del rango 1 a 12.')
    if not d.GRUPO_EDAD1.between(0,29).all(): raise ValueError('Código de edad fuera de 0 a 29.')
    if not d.SEXO.isin(SEXO).all(): raise ValueError('Código de sexo no reconocido.')
    if not d.COD_DANE.eq(d.COD_DEPARTAMENTO*1000+d.COD_MUNICIPIO).all():
        raise ValueError('COD_DANE no coincide con departamento y municipio.')
    if 'TOTAL' in d and not pd.to_numeric(d.TOTAL,errors='raise').eq(1).all():
        raise ValueError('Se esperan microdatos: cada fila debe representar una defunción.')
    for c in ['DEPARTAMENTO','MUNICIPIO']:
        if d[c].isna().any() or d[c].astype(str).str.strip().eq('').any(): raise ValueError(f'{c} contiene nombres vacíos.')
        d[c]=d[c].astype(str).str.strip()
    geo=d[['COD_DANE','COD_DEPARTAMENTO','DEPARTAMENTO','MUNICIPIO']].drop_duplicates()
    if geo.COD_DANE.duplicated().any(): raise ValueError('Un código DANE tiene varios nombres.')
    if geo[['COD_DEPARTAMENTO','DEPARTAMENTO']].drop_duplicates().COD_DEPARTAMENTO.duplicated().any():
        raise ValueError('Un departamento tiene varios nombres.')
    d['CODIGO']=d.COD_MUERTE.astype('string').str.upper().str.strip().str.replace('.','',regex=False)
    if not d.CODIGO.str.fullmatch(r'[A-Z][0-9]{2}[A-Z0-9]{0,2}',na=False).all(): raise ValueError('Hay códigos de causa inválidos.')
    nombres=[c for c in ['NOMBRE_CAUSA','NOMBRE_MUERTE','NOMBRE_MUERTE_x','NOMBRE_MUERTE_y'] if c in d]
    desc=pd.Series(pd.NA,index=d.index,dtype='string')
    for c in nombres:
        s=d[c].astype('string').str.strip().replace({'':'', 'nan':'', 'None':'','NAN':''}).replace('',pd.NA)
        desc=desc.fillna(s)
    # Un solo nombre por código, elegido por frecuencia en el catálogo consolidado.
    pares=pd.DataFrame({'CODIGO':d.CODIGO,'DESCRIPCION':desc}).dropna()
    catalogo=(pares.groupby(['CODIGO','DESCRIPCION']).size().rename('N').reset_index()
              .sort_values(['N','DESCRIPCION'],ascending=[False,True]).drop_duplicates('CODIGO')
              .set_index('CODIGO').DESCRIPCION.to_dict())
    d['DESCRIPCION']=d.CODIGO.map(catalogo).fillna('Sin descripción en el archivo consolidado')
    d['X95']=d.CODIGO.str.startswith('X95').astype(bool)
    d['CATEGORIA_EDAD']=pd.Categorical(d.GRUPO_EDAD1.map(clasificar_edad),categories=[r[0] for r in EDADES],ordered=True)
    d['SEXO_DESC']=d.SEXO.map(SEXO)
    d['LUGAR']=d.MUNICIPIO+' · '+d.DEPARTAMENTO
    d['TOTAL']=1
    keep=REQ+['CODIGO','DESCRIPCION','X95','CATEGORIA_EDAD','SEXO_DESC','LUGAR','TOTAL']
    d=d[keep].copy()
    for c in ['DEPARTAMENTO','MUNICIPIO','CODIGO','DESCRIPCION','SEXO_DESC','LUGAR']:
        d[c]=d[c].astype('category')
    return d


def filtrar(d, departamentos=None, meses=None, sexos=None, edades=None):
    """Ninguna selección equivale a todas las categorías de ese filtro."""
    mask=pd.Series(True,index=d.index)
    for col,val in [('COD_DEPARTAMENTO',departamentos),('MES',meses),('SEXO',sexos),('CATEGORIA_EDAD',edades)]:
        if val: mask &= d[col].isin(val)
    return d.loc[mask]


def resumir(d):
    dep=d.groupby(['COD_DEPARTAMENTO','DEPARTAMENTO'],observed=True).size().reset_index(name='TOTAL')
    dep=dep.sort_values(['TOTAL','COD_DEPARTAMENTO'],ascending=[False,True])
    mes=d.groupby('MES',observed=True).size().reindex(range(1,13),fill_value=0).rename('TOTAL').reset_index()
    mes['NOMBRE_MES']=mes.MES.map(MESES)
    cols=['COD_DANE','MUNICIPIO','DEPARTAMENTO','LUGAR']
    ciudades=d.groupby(cols,observed=True).size().reset_index(name='TOTAL')
    violentas=d.loc[d.X95].groupby(cols,observed=True).size().reset_index(name='TOTAL')
    violentas=violentas.sort_values(['TOTAL','COD_DANE'],ascending=[False,True]).head(5)
    menores=ciudades.sort_values(['TOTAL','MUNICIPIO','DEPARTAMENTO','COD_DANE']).head(10)
    causas=d.groupby(['CODIGO','DESCRIPCION'],observed=True).size().reset_index(name='TOTAL')
    causas=causas.sort_values(['TOTAL','CODIGO'],ascending=[False,True]).head(10)
    sexo=d.groupby(['COD_DEPARTAMENTO','DEPARTAMENTO','SEXO_DESC'],observed=True).size().reset_index(name='TOTAL')
    edad=d.groupby('CATEGORIA_EDAD',observed=False).size().rename('TOTAL').reset_index()
    return dict(departamentos=dep,meses=mes,violentas=violentas,menores=menores,causas=causas,sexo=sexo,edad=edad,
                total=len(d),municipios=d.COD_DANE.nunique(),x95=int(d.X95.sum()),n_departamentos=d.COD_DEPARTAMENTO.nunique())

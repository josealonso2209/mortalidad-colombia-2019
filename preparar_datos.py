"""Construye una base reproducible a partir de defunciones, DIVIPOLA y CIE-10."""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parent
ARCHIVOS={'defunciones':'Anexo1.NoFetal2019_CE_15-03-23.xlsx',
          'territorios':'Divipola_CE_.xlsx',
          'causas':'Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx'}


def catalogo_causas(path):
    """Prioriza códigos completos y conserva los códigos válidos de tres caracteres."""
    cat=pd.read_excel(path,sheet_name='Final',header=8,engine='openpyxl')
    pares=[]
    for col_codigo,col_nombre in [(4,5),(2,3)]:
        par=pd.DataFrame({'COD_MUERTE':cat.iloc[:,col_codigo].astype('string').str.strip().str.upper().str.replace('.','',regex=False),
                          'NOMBRE_CAUSA':cat.iloc[:,col_nombre].astype('string').str.strip()}).dropna()
        par=par.loc[par.COD_MUERTE.str.fullmatch(r'[A-Z][0-9]{2}[A-Z0-9]{0,2}')&par.NOMBRE_CAUSA.ne('')]
        pares.append(par)
    # La prioridad y el orden del catálogo determinan un único nombre por código.
    return pd.concat(pares,ignore_index=True).drop_duplicates('COD_MUERTE',keep='first')


def construir(originales,output):
    paths={k:Path(originales)/v for k,v in ARCHIVOS.items()}
    for path in paths.values():
        if not path.is_file():raise FileNotFoundError(path)
    raw=pd.read_excel(paths['defunciones'],sheet_name='No_Fetales_2019',engine='openpyxl')
    geo=pd.read_excel(paths['territorios'],sheet_name='Hoja1',engine='openpyxl')
    catalogo=catalogo_causas(paths['causas'])
    for col in ['COD_DANE','COD_DEPARTAMENTO','COD_MUNICIPIO']:
        raw[col]=pd.to_numeric(raw[col],errors='raise').astype('int64')
        geo[col]=pd.to_numeric(geo[col],errors='raise').astype('int64')
    if geo.COD_DANE.duplicated().any():raise ValueError('DIVIPOLA contiene códigos territoriales duplicados.')
    if not raw.COD_DANE.eq(raw.COD_DEPARTAMENTO*1000+raw.COD_MUNICIPIO).all():raise ValueError('Códigos territoriales inconsistentes.')
    raw['COD_MUERTE']=raw.COD_MUERTE.astype('string').str.strip().str.upper().str.replace('.','',regex=False)
    n=len(raw)
    # Ambos cruces son muchos a uno y deben conservar el número y orden de las filas.
    d=raw.merge(geo[['COD_DANE','DEPARTAMENTO','MUNICIPIO']],on='COD_DANE',how='left',validate='many_to_one',sort=False)
    d=d.merge(catalogo,on='COD_MUERTE',how='left',validate='many_to_one',sort=False)
    for c in ['DEPARTAMENTO','MUNICIPIO','NOMBRE_CAUSA']:
        if d[c].isna().any():raise ValueError(f'Cruce incompleto en {c}: {d[c].isna().sum()} registros.')
    if len(d)!=n:raise ValueError('La consolidación alteró el número de defunciones.')
    if not d['AÑO'].eq(2019).all():raise ValueError('Se encontraron registros de otro año.')
    d['TOTAL']=1
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    comp={'method':'gzip','mtime':0} if output.name.endswith('.gz') else None
    d.to_csv(output,index=False,compression=comp)
    controles={'filas_fuente':n,'filas_consolidadas':len(d),'anio':2019,'codigos_territoriales':int(d.COD_DANE.nunique()),
               'departamentos_y_bogota':int(d.COD_DEPARTAMENTO.nunique()),'causas_distintas':int(d.COD_MUERTE.nunique()),
               'registros_sin_territorio':int(d.MUNICIPIO.isna().sum()),'registros_sin_descripcion':int(d.NOMBRE_CAUSA.isna().sum()),
               'cruces':'many_to_one','fuentes':[{'archivo':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths.values()]}
    (ROOT/'data/validacion_fuentes.json').write_text(json.dumps(controles,ensure_ascii=False,indent=2),encoding='utf-8')
    return d,controles


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--originales',type=Path,default=ROOT/'data/originales')
    ap.add_argument('--output',type=Path,default=ROOT/'data/mortalidad_2019.csv.gz')
    args=ap.parse_args();_,control=construir(args.originales,args.output)
    print(json.dumps(control,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

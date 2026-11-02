"""Pruebas de integridad con el CSV real y casos de regresión geográfica."""
import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analisis import cargar_datos,filtrar,resumir,clasificar_edad,EDADES,ROOT

class Datos(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.d=cargar_datos();cls.r=resumir(cls.d)
    def test_cifras_nacionales(self):
        self.assertEqual((len(self.d),self.r['municipios'],self.r['n_departamentos'],self.r['x95']),(244355,1110,33,9273))
    def test_base_comprimida(self):
        comprimida=cargar_datos(ROOT/'data/mortalidad_2019.csv.gz')
        self.assertTrue(self.d.equals(comprimida))
        self.assertTrue(self.d.equals(cargar_datos(ROOT/'data/registros')))
    def test_particiones_conservan_registros(self):
        for k in ['departamentos','meses','sexo','edad']:
            with self.subTest(k=k): self.assertEqual(int(self.r[k].TOTAL.sum()),len(self.d))
    def test_ranking_x95(self):
        self.assertEqual(self.r['violentas'].COD_DANE.tolist(),[76001,11001,5001,8001,54001])
        self.assertEqual(self.r['violentas'].TOTAL.tolist(),[971,601,428,260,206])
    def test_catalogo_completo(self):
        self.assertFalse(self.d.DESCRIPCION.str.contains('Sin descripción').any())
        self.assertEqual(self.d.CODIGO.nunique(),3271)
    def test_top_causas_descripciones(self):
        t=self.r['causas'];self.assertEqual((str(t.iloc[0].CODIGO),int(t.iloc[0].TOTAL)),('I219',35088))
        self.assertTrue(t.TOTAL.is_monotonic_decreasing);self.assertFalse(t.CODIGO.duplicated().any())
        self.assertFalse(t.DESCRIPCION.str.contains('Sin descripción').any())
    def test_municipios_homonimos(self):
        # ARMENIA (Antioquia) no debe sumarse con ARMENIA (Quindío).
        a=self.d.loc[self.d.MUNICIPIO=='ARMENIA']
        self.assertEqual(a.COD_DANE.nunique(),2)
        self.assertEqual(resumir(a)['municipios'],2)
    def test_edades_bordes_y_desconocida(self):
        for nombre,a,b,_ in EDADES:
            self.assertEqual(clasificar_edad(a),nombre);self.assertEqual(clasificar_edad(b),nombre)
        for v in [None,float('nan'),-1,30,2.9,'error']: self.assertEqual(clasificar_edad(v),'Edad desconocida')
        self.assertEqual(int(self.r['edad'].loc[self.r['edad'].CATEGORIA_EDAD=='Vejez','TOTAL'].iloc[0]),115453)
    def test_filtros_por_separado(self):
        for kwargs,col,val in [({'departamentos':[5]},'COD_DEPARTAMENTO',5),({'meses':[2]},'MES',2),({'sexos':[2]},'SEXO',2),({'edades':['Juventud']},'CATEGORIA_EDAD','Juventud')]:
            with self.subTest(col=col):
                f=filtrar(self.d,**kwargs)
                self.assertEqual(len(f),int(self.d[col].eq(val).sum()));self.assertTrue(f[col].eq(val).all())
    def test_filtro_combinado(self):
        f=filtrar(self.d,[5],[2],[2],['Vejez'])
        esperado=self.d.loc[(self.d.COD_DEPARTAMENTO==5)&(self.d.MES==2)&(self.d.SEXO==2)&(self.d.CATEGORIA_EDAD=='Vejez')]
        self.assertEqual(f.index.tolist(),esperado.index.tolist());self.assertGreater(len(f),0)
    def test_vacio_y_restablecer(self):
        self.assertEqual(len(filtrar(self.d,[],[],[],[])),244355)
        r=resumir(filtrar(self.d,[999]))
        self.assertEqual(r['total'],0);self.assertEqual(len(r['edad']),11);self.assertEqual(len(r['meses']),12)
    def test_empates_menores(self):
        self.assertEqual(len(self.r['menores']),10);self.assertEqual(self.r['menores'].TOTAL.tolist(),[1]*10)
        self.assertEqual((self.d.groupby('COD_DANE',observed=True).size()==1).sum(),13)

class Aplicacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import estadistica
        cls.m=estadistica;cls.c=estadistica.server.test_client()
    def test_rutas(self):
        for p in ['/','/_dash-layout','/_dash-dependencies','/healthz','/assets/estilos.css','/assets/world_110m.json']:
            with self.subTest(p=p):
                response=self.c.get(p);self.assertEqual(response.status_code,200);response.close()
    def test_poligonos_completos(self):
        self.assertIsNotNone(self.m.GEO)
        mapa={f['properties']['COD_DPTO'] for f in self.m.GEO['features']}
        self.assertEqual(mapa,set(self.m.DF.COD_DEPARTAMENTO.astype(str).str.zfill(2)))
    def test_callbacks_sin_error(self):
        for vals in [([],[],[],[]),([5],[2],[2],['Vejez']),([999],[],[],[]),([],[],[3],[])]:
            with self.subTest(vals=vals):
                o=self.m.actualizar(*vals);self.assertEqual(len(o),13)
                for f in o[:6]: self.assertIsNotNone(f.to_plotly_json())
    def test_callback_http(self):
        key=[k for k in self.m.app.callback_map if 'mapa.figure' in k][0]
        props=[{'id':i,'property':'figure'} for i in self.m.IDS]+[{'id':'causas','property':'data'}]+[{'id':i,'property':'children'} for i in ['kpi-total','kpi-dep','kpi-mun','kpi-x95','contexto','mapa-nota']]
        r=self.c.post('/_dash-update-component',json={'output':key,'outputs':props,'inputs':[{'id':i,'property':'value','value':v} for i,v in zip(['f-dep','f-mes','f-sexo','f-edad'],[[5],[],[],[]])],'state':[],'changedPropIds':['f-dep.value']})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['response']['kpi-total']['children'],'34.473')
    def test_meses_excluidos_son_huecos(self):
        f=self.m.actualizar([],[2],[],[])[1]
        self.assertEqual(f.data[0].y[1],17974)
        self.assertIsNone(f.data[0].y[0])
    def test_restablecer(self): self.assertEqual(self.m.resetear(1),([],[],[],[]))

if __name__=='__main__':unittest.main(verbosity=2)

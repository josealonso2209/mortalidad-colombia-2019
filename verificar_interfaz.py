"""Prueba real de navegador y capturas. Requiere requirements-validacion.txt.
Ejecutar desde la raíz: python verificar_interfaz.py
"""
from pathlib import Path
import threading
import json
from werkzeug.serving import make_server, WSGIRequestHandler
from playwright.sync_api import sync_playwright
import estadistica
from analisis import ROOT,filtrar

class Quiet(WSGIRequestHandler):
    def log_request(self,*args): pass


def main():
    destino=ROOT/'docs/capturas';destino.mkdir(parents=True,exist_ok=True)
    server=make_server('127.0.0.1',0,estadistica.server,threaded=True,request_handler=Quiet)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    errores=[];fallos=[];resultados=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1040},device_scale_factor=1.5)
            page.on('pageerror',lambda e:errores.append(str(e)))
            page.on('requestfailed',lambda req:fallos.append(req.url))
            page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle')
            page.locator('#kpi-total').get_by_text('244.355',exact=True).wait_for()
            page.wait_for_function("document.querySelectorAll('#mapa .choroplethlayer path').length===33")
            page.screenshot(path=str(destino/'00_vista_general.png'))
            for id in ['mapa','linea','violentas','menores','causas','sexo-dep','edad']:
                page.locator('#panel-'+id).screenshot(path=str(destino/(id+'.png')))
            print('Paso completado',flush=True);resultados.append('Vista nacional: 244.355 registros, seis gráficos y tabla, 33 polígonos.')
            # Entradas a través de los controles reales de Dash, sin modificar estado interno.
            def elegir(id,texto):
                campo=page.locator('#'+id+' input')
                campo.fill(texto)
                page.locator('#'+id+' .VirtualizedSelectOption').filter(has_text=texto).click()
            elegir('f-dep','ANTIOQUIA')
            page.locator('#kpi-total').get_by_text('34.473',exact=True).wait_for()
            print('Paso completado',flush=True);resultados.append('Filtro de departamento: Antioquia = 34.473.')
            page.locator('header').scroll_into_view_if_needed()
            page.screenshot(path=str(destino/'08_filtro_antioquia.png'))
            elegir('f-mes','Febrero');elegir('f-sexo','Mujeres');elegir('f-edad','Vejez')
            esperado=len(filtrar(estadistica.DF,[5],[2],[2],['Vejez']))
            page.locator('#kpi-total').get_by_text(f'{esperado:,}'.replace(',','.'),exact=True).wait_for()
            print('Paso completado',flush=True);resultados.append(f'Cuatro filtros simultáneos: Antioquia, febrero, mujeres, vejez = {esperado}.')
            page.locator('header').scroll_into_view_if_needed()
            page.screenshot(path=str(destino/'09_filtros_combinados.png'))
            page.get_by_role('button',name='Restablecer filtros').click()
            page.locator('#kpi-total').get_by_text('244.355',exact=True).wait_for()
            print('Paso completado',flush=True);resultados.append('Restablecer recupera el total nacional.')
            elegir('f-dep','VAUPÉS');elegir('f-sexo','Indeterminado');elegir('f-edad','Longevidad y centenarios')
            page.locator('#kpi-total').get_by_text('0',exact=True).wait_for()
            page.locator('#contexto').get_by_text('Sin registros',exact=False).wait_for()
            print('Paso completado',flush=True);resultados.append('Selección sin datos: mensaje visible y gráficos vacíos sin excepción.')
            page.locator('header').scroll_into_view_if_needed()
            page.screenshot(path=str(destino/'10_sin_registros.png'))
            page.get_by_role('button',name='Restablecer filtros').click()
            page.locator('#kpi-total').get_by_text('244.355',exact=True).wait_for()
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_function('document.documentElement.scrollWidth <= window.innerWidth',timeout=10000)
            page.locator('header').scroll_into_view_if_needed()
            page.screenshot(path=str(destino/'11_movil.png'))
            ancho=page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            if not ancho: raise AssertionError('Desbordamiento horizontal en móvil')
            print('Paso completado',flush=True);resultados.append('Vista móvil de 390 px sin desbordamiento horizontal de la página.')
            browser.close()
        if errores: raise AssertionError(errores)
        if fallos: raise AssertionError(fallos)
        salida={'estado':'correcto','pruebas':resultados,'errores_javascript':errores,'solicitudes_fallidas':fallos}
        (ROOT/'docs/validacion_interfaz.json').write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(salida,ensure_ascii=False,indent=2))
    finally: server.shutdown()

if __name__=='__main__':main()

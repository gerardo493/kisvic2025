import requests
import json
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Archivo donde se guardará la última tasa
ULTIMA_TASA_BCV_FILE = 'ultima_tasa_bcv.json'

def guardar_ultima_tasa_bcv(tasa):
    """Guarda la última tasa BCV en un archivo JSON"""
    try:
        data = {
            'tasa': tasa,
            'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(ULTIMA_TASA_BCV_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error al guardar la tasa BCV: {str(e)}")
        return False

def cargar_ultima_tasa_bcv():
    """Carga la última tasa BCV guardada del archivo JSON"""
    try:
        with open(ULTIMA_TASA_BCV_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            tasa = float(data.get('tasa', 0))
            if tasa > 10:
                return tasa
            else:
                return None
    except Exception:
        return None

def obtener_tasa_bcv():
    """Obtiene la tasa BCV del archivo JSON"""
    try:
        with open(ULTIMA_TASA_BCV_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return float(data.get('tasa', 0))
    except Exception:
        return 0

def obtener_tasa_bcv_dia():
    """Obtiene la tasa oficial USD/BS del BCV desde la web. Devuelve float o None si falla."""
    url = 'https://www.bcv.org.ve/glosario/cambio-oficial'
    try:
        resp = requests.get(url, timeout=10, verify=False)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        tasa = None
        
        # Buscar por id='dolar'
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            strong = dolar_div.find('strong')
            if strong:
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10:
                        tasa = posible
                except:
                    pass
        
        # Buscar por strong con texto que parezca una tasa
        if not tasa:
            for strong in soup.find_all('strong'):
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10:
                        tasa = posible
                        break
                except:
                    continue
        
        # Buscar cualquier número grande en el texto plano
        if not tasa:
            import re
            matches = re.findall(r'(\d{2,}[.,]\d{2})', resp.text)
            for m in matches:
                try:
                    posible = float(m.replace('.', '').replace(',', '.'))
                    if posible > 10:
                        tasa = posible
                        break
                except:
                    continue
        
        if tasa and tasa > 10:
            # Guardar la tasa en el archivo
            guardar_ultima_tasa_bcv(tasa)
            return tasa
        else:
            return None
    except Exception as e:
        print(f"Error al obtener la tasa BCV: {str(e)}")
        return None

def actualizar_tasa_bcv():
    """Actualiza la tasa BCV y devuelve un diccionario con el resultado"""
    try:
        # Intentar obtener la tasa del día
        tasa = obtener_tasa_bcv_dia()
        
        if tasa is None or tasa <= 0:
            # Si falla, intentar obtener la tasa del archivo
            tasa = cargar_ultima_tasa_bcv()
            if tasa is None or tasa <= 0:
                return {
                    'success': False, 
                    'error': 'No se pudo obtener la tasa BCV. Por favor, intente más tarde.'
                }
        
        # Guardar la nueva tasa
        guardar_ultima_tasa_bcv(tasa)
        
        return {
            'success': True,
            'tasa': tasa,
            'message': f'Tasa BCV actualizada exitosamente: {tasa}',
            'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"Error al actualizar tasa BCV: {str(e)}")
        return {
            'success': False,
            'error': f'Error al actualizar la tasa BCV: {str(e)}'
        }

# Ejemplo de uso
if __name__ == "__main__":
    # Actualizar la tasa BCV
    resultado = actualizar_tasa_bcv()
    
    if resultado['success']:
        print(f"Tasa BCV actualizada: {resultado['tasa']}")
        print(f"Fecha de actualización: {resultado['fecha_actualizacion']}")
    else:
        print(f"Error: {resultado['error']}")
        
    # Obtener la tasa actual
    tasa_actual = obtener_tasa_bcv()
    print(f"Tasa BCV actual: {tasa_actual}") 
"""
Aplicación Web SCADA - Panel de Control (Versión SiOME NodeSet2)
Puerto: 5000
"""

from flask import Flask, render_template, jsonify, request
from opcua import Client
import logging
import threading
import time

app = Flask(__name__, static_folder='static', template_folder='templates')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Almacén de datos
sistema_data = {
    'nivel_mm': 0.0, 'volumen_l': 0.0, 'temperatura': 0.0, 'setpoint': 45.0,
    'calentador_on': False, 'caudal_in': 0.0, 'caudal_out': 0.0,
    'rpm_bomba': 0.0, 'posicion_valvula': 0.0, 'amperios': 0.0,
    'totalizador': 0.0, 'estado_sistema': 'CONECTANDO...',
    'alerta_fuga': False, 'tiempo_llenado': 0.0, 'estado_sensor': True
}

clients = {}
nodes = {}
URI = "http://upv.edu/TanqueIndustrial"

def conectar_servidores():
    """Conecta a servidores OPC UA usando IDs de SiOME"""
    global clients, nodes
    try:
        # --- NIVEL (4840) ---
        clients['nivel'] = Client("opc.tcp://localhost:4840/freeopcua/server/")
        clients['nivel'].connect()
        idx = clients['nivel'].get_namespace_index(URI)
        nodes['nivel_mm'] = clients['nivel'].get_node(f"ns={idx};i=6016")
        nodes['volumen_l'] = clients['nivel'].get_node(f"ns={idx};i=6017")
        logger.info("✓ Web: Conectado a Nivel")

        # --- TEMPERATURA (4841) ---
        clients['temp'] = Client("opc.tcp://localhost:4841/freeopcua/server/")
        clients['temp'].connect()
        idx = clients['temp'].get_namespace_index(URI)
        nodes['temperatura'] = clients['temp'].get_node(f"ns={idx};i=6022")
        nodes['setpoint'] = clients['temp'].get_node(f"ns={idx};i=6023")
        nodes['calentador_on'] = clients['temp'].get_node(f"ns={idx};i=6024")
        logger.info("✓ Web: Conectado a Temperatura")

        # --- ENTRADA (4842) ---
        clients['entrada'] = Client("opc.tcp://localhost:4842/freeopcua/server/")
        clients['entrada'].connect()
        idx = clients['entrada'].get_namespace_index(URI)
        nodes['caudal_in'] = clients['entrada'].get_node(f"ns={idx};i=6009")
        nodes['rpm_bomba'] = clients['entrada'].get_node(f"ns={idx};i=6010")
        nodes['amperios'] = clients['entrada'].get_node(f"ns={idx};i=6011")
        logger.info("✓ Web: Conectado a Entrada")

        # --- SALIDA (4843) ---
        clients['salida'] = Client("opc.tcp://localhost:4843/freeopcua/server/")
        clients['salida'].connect()
        idx = clients['salida'].get_namespace_index(URI)
        nodes['caudal_out'] = clients['salida'].get_node(f"ns={idx};i=6019")
        nodes['posicion_valvula'] = clients['salida'].get_node(f"ns={idx};i=6020")
        nodes['totalizador'] = clients['salida'].get_node(f"ns={idx};i=6021")
        logger.info("✓ Web: Conectado a Salida")

        # --- MIDDLEWARE (4845) ---
        clients['middleware'] = Client("opc.tcp://localhost:4845/freeopcua/server/")
        clients['middleware'].connect()
        idx = clients['middleware'].get_namespace_index(URI)
        nodes['estado_sistema'] = clients['middleware'].get_node(f"ns={idx};i=6014")
        nodes['alerta_fuga'] = clients['middleware'].get_node(f"ns={idx};i=6013")
        nodes['tiempo_llenado'] = clients['middleware'].get_node(f"ns={idx};i=6015")
        logger.info("✓ Web: Conectado a Middleware")

        return True
    except Exception as e:
        logger.error(f"Error conectando Web a OPC UA: {e}")
        return False

def actualizar_datos():
    """Hilo de lectura"""
    global sistema_data
    while True:
        try:
            sistema_data['nivel_mm'] = nodes['nivel_mm'].get_value()
            sistema_data['volumen_l'] = nodes['volumen_l'].get_value()
            sistema_data['temperatura'] = nodes['temperatura'].get_value()
            sistema_data['setpoint'] = nodes['setpoint'].get_value()
            sistema_data['calentador_on'] = nodes['calentador_on'].get_value()
            sistema_data['caudal_in'] = nodes['caudal_in'].get_value()
            sistema_data['rpm_bomba'] = nodes['rpm_bomba'].get_value()
            sistema_data['amperios'] = nodes['amperios'].get_value()
            sistema_data['caudal_out'] = nodes['caudal_out'].get_value()
            sistema_data['posicion_valvula'] = nodes['posicion_valvula'].get_value()
            sistema_data['totalizador'] = nodes['totalizador'].get_value()
            sistema_data['estado_sistema'] = nodes['estado_sistema'].get_value()
            sistema_data['alerta_fuga'] = nodes['alerta_fuga'].get_value()
            sistema_data['tiempo_llenado'] = nodes['tiempo_llenado'].get_value()
        except Exception as e:
            logger.error(f"Error lectura datos: {e}")
        time.sleep(0.5)

# --- RUTAS FLASK (Sin cambios) ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/datos')
def obtener_datos(): return jsonify(sistema_data)

@app.route('/api/control/rpm', methods=['POST'])
def control_rpm():
    try:
        rpm = float(request.json.get('rpm', 0))
        nodes['rpm_bomba'].set_value(rpm)
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/control/valvula', methods=['POST'])
def control_valvula():
    try:
        pos = float(request.json.get('posicion', 0))
        nodes['posicion_valvula'].set_value(pos)
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/control/setpoint', methods=['POST'])
def control_setpoint():
    try:
        sp = float(request.json.get('setpoint', 45))
        nodes['setpoint'].set_value(sp)
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

def iniciar_app():
    logger.info("Iniciando Web SCADA...")
    time.sleep(5) # Espera a servidores
    if conectar_servidores():
        threading.Thread(target=actualizar_datos, daemon=True).start()
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    iniciar_app()
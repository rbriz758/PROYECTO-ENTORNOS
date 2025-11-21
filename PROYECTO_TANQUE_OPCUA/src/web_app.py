"""
Aplicación Web SCADA - Panel de Control
Puerto: 5000
Interfaz industrial oscura con visualización en tiempo real
"""

from flask import Flask, render_template, jsonify, request
from opcua import Client
import logging
import threading
import time

app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables globales para almacenar datos
sistema_data = {
    'nivel_mm': 0.0,
    'volumen_l': 0.0,
    'temperatura': 0.0,
    'setpoint': 45.0,
    'calentador_on': False,
    'caudal_in': 0.0,
    'caudal_out': 0.0,
    'rpm_bomba': 0.0,
    'posicion_valvula': 0.0,
    'amperios': 0.0,
    'totalizador': 0.0,
    'estado_sistema': 'INICIALIZANDO',
    'alerta_fuga': False,
    'tiempo_llenado': 0.0,
    'estado_sensor': True
}

# Clientes OPC UA
clients = {}
nodes = {}

def conectar_servidores():
    """Conecta a todos los servidores OPC UA"""
    global clients, nodes
    
    try:
        # Servidor Nivel
        clients['nivel'] = Client("opc.tcp://localhost:4840/freeopcua/server/")
        clients['nivel'].connect()
        root = clients['nivel'].get_objects_node()
        nivel_obj = root.get_child(["2:Nivel"])
        nodes['nivel_mm'] = nivel_obj.get_child(["2:Nivel_mm"])
        nodes['volumen_l'] = nivel_obj.get_child(["2:Volumen_L"])
        logger.info("✓ Conectado a Servidor Nivel")
        
        # Servidor Temperatura
        clients['temp'] = Client("opc.tcp://localhost:4841/freeopcua/server/")
        clients['temp'].connect()
        root = clients['temp'].get_objects_node()
        temp_obj = root.get_child(["2:Temperatura"])
        nodes['temperatura'] = temp_obj.get_child(["2:Temperatura"])
        nodes['setpoint'] = temp_obj.get_child(["2:SetPoint"])
        nodes['calentador_on'] = temp_obj.get_child(["2:Calentador_On"])
        logger.info("✓ Conectado a Servidor Temperatura")
        
        # Servidor Entrada
        clients['entrada'] = Client("opc.tcp://localhost:4842/freeopcua/server/")
        clients['entrada'].connect()
        root = clients['entrada'].get_objects_node()
        entrada_obj = root.get_child(["2:Entrada"])
        nodes['caudal_in'] = entrada_obj.get_child(["2:Caudal_In"])
        nodes['rpm_bomba'] = entrada_obj.get_child(["2:RPM_Bomba"])
        nodes['amperios'] = entrada_obj.get_child(["2:Amperios"])
        logger.info("✓ Conectado a Servidor Entrada")
        
        # Servidor Salida
        clients['salida'] = Client("opc.tcp://localhost:4843/freeopcua/server/")
        clients['salida'].connect()
        root = clients['salida'].get_objects_node()
        salida_obj = root.get_child(["2:Salida"])
        nodes['caudal_out'] = salida_obj.get_child(["2:Caudal_Out"])
        nodes['posicion_valvula'] = salida_obj.get_child(["2:Posicion_Valvula"])
        nodes['totalizador'] = salida_obj.get_child(["2:Totalizador"])
        logger.info("✓ Conectado a Servidor Salida")
        
        # Middleware
        clients['middleware'] = Client("opc.tcp://localhost:4845/freeopcua/server/")
        clients['middleware'].connect()
        root = clients['middleware'].get_objects_node()
        middleware_obj = root.get_child(["2:Middleware"])
        nodes['estado_sistema'] = middleware_obj.get_child(["2:Estado_Sistema"])
        nodes['alerta_fuga'] = middleware_obj.get_child(["2:Alerta_Fuga"])
        nodes['tiempo_llenado'] = middleware_obj.get_child(["2:Tiempo_Llenado"])
        logger.info("✓ Conectado a Middleware")
        
        return True
    except Exception as e:
        logger.error(f"Error conectando a servidores: {e}")
        return False

def actualizar_datos():
    """Hilo que actualiza los datos continuamente"""
    global sistema_data
    
    while True:
        try:
            sistema_data['nivel_mm'] = nodes['nivel_mm'].get_value()
            sistema_data['volumen_l'] = nodes['volumen_l'].get_value()
            sistema_data['temperatura'] = nodes['temperatura'].get_value()
            sistema_data['setpoint'] = nodes['setpoint'].get_value()
            sistema_data['calentador_on'] = nodes['calentador_on'].get_value()
            sistema_data['caudal_in'] = nodes['caudal_in'].get_value()
            sistema_data['caudal_out'] = nodes['caudal_out'].get_value()
            sistema_data['rpm_bomba'] = nodes['rpm_bomba'].get_value()
            sistema_data['posicion_valvula'] = nodes['posicion_valvula'].get_value()
            sistema_data['amperios'] = nodes['amperios'].get_value()
            sistema_data['totalizador'] = nodes['totalizador'].get_value()
            sistema_data['estado_sistema'] = nodes['estado_sistema'].get_value()
            sistema_data['alerta_fuga'] = nodes['alerta_fuga'].get_value()
            sistema_data['tiempo_llenado'] = nodes['tiempo_llenado'].get_value()
        except Exception as e:
            logger.error(f"Error actualizando datos: {e}")
        
        time.sleep(0.5)  # Actualizar cada 500ms

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/datos')
def obtener_datos():
    """API para obtener todos los datos del sistema"""
    return jsonify(sistema_data)

@app.route('/api/control/rpm', methods=['POST'])
def control_rpm():
    """Controlar RPM de la bomba"""
    try:
        rpm = float(request.json.get('rpm', 0))
        rpm = max(0, min(3000, rpm))  # Limitar entre 0-3000
        nodes['rpm_bomba'].set_value(rpm)
        return jsonify({'success': True, 'rpm': rpm})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/control/valvula', methods=['POST'])
def control_valvula():
    """Controlar posición de válvula"""
    try:
        posicion = float(request.json.get('posicion', 0))
        posicion = max(0, min(100, posicion))  # Limitar entre 0-100%
        nodes['posicion_valvula'].set_value(posicion)
        return jsonify({'success': True, 'posicion': posicion})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/control/setpoint', methods=['POST'])
def control_setpoint():
    """Controlar setpoint de temperatura"""
    try:
        setpoint = float(request.json.get('setpoint', 45))
        setpoint = max(15, min(100, setpoint))  # Limitar entre 15-100°C
        nodes['setpoint'].set_value(setpoint)
        return jsonify({'success': True, 'setpoint': setpoint})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def iniciar_app():
    """Iniciar la aplicación web"""
    logger.info("Iniciando Web SCADA...")
    
    # Esperar a que los servidores estén listos
    time.sleep(5)
    
    # Conectar a servidores
    if not conectar_servidores():
        logger.error("No se pudo conectar a los servidores OPC UA")
        return
    
    # Iniciar hilo de actualización
    thread = threading.Thread(target=actualizar_datos, daemon=True)
    thread.start()
    
    logger.info("=" * 60)
    logger.info("✓ Web SCADA iniciado en http://localhost:5000")
    logger.info("=" * 60)
    
    # Iniciar Flask
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    iniciar_app()

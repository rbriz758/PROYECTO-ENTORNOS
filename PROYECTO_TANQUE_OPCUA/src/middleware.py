"""
MIDDLEWARE - MOTOR DE FÍSICA MAESTRO (Versión SiOME NodeSet2)
Puerto: 4845
"""

from opcua import Server, Client
import time
import logging
import requests
import threading
import math
import os
from database import DatabaseManager

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MIDDLEWARE")

# CONFIGURACIÓN TELEGRAM
TELEGRAM_TOKEN ="8320295019:AAGWkjjsodtc7XNoiAZ0N0cvAhxwughIHpU"
TELEGRAM_CHAT_ID ="5636254828"

def enviar_alerta_telegram(mensaje):
    """Envía una alerta a Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info("✓ Alerta enviada a Telegram")
        else:
            logger.warning(f"Error enviando a Telegram: {response.status_code}")
    except Exception as e:
        logger.error(f"Fallo al conectar con Telegram: {e}")

class PhysicsEngine:
    """Motor de Física Centralizado"""
    def __init__(self):
        self.NIVEL_MAX = 3000.0  # mm
        self.CAPACIDAD_MAX = 10000.0  # Litros
        self.nivel_actual = 0.0
        self.temp_actual = 20.0
        self.totalizador = 0.0
        self.nivel_anterior = 0.0
        self.ciclos_sin_cambio = 0
        self.caudal_in = 0.0
        self.caudal_out = 0.0
        
    def calcular_fisica_entrada(self, rpm_bomba, nivel_actual):
        if nivel_actual >= self.NIVEL_MAX:
            caudal_in = 0.0
        else:
            caudal_in = rpm_bomba * 0.05
        amperios = 2.0 + (caudal_in * 0.15)
        self.caudal_in = caudal_in
        return caudal_in, amperios
    
    def calcular_fisica_salida(self, posicion_valvula, nivel_mm):
        if nivel_mm <= 0:
            factor_presion = 0.0
        else:
            factor_presion = math.sqrt(nivel_mm / 3000.0)
        caudal_out = (posicion_valvula / 100.0) * 50.0 * factor_presion
        self.caudal_out = caudal_out
        return caudal_out
    
    def actualizar_totalizador(self, caudal_out, dt=1.0):
        self.totalizador += (caudal_out / 60.0) / 1000.0 * dt
        return self.totalizador
    
    def calcular_fisica_tanque(self, caudal_in, caudal_out, nivel_actual, dt=1.0):
        delta_nivel = (caudal_in - caudal_out) * 0.5 * dt
        nivel_nuevo = nivel_actual + delta_nivel
        if nivel_nuevo > self.NIVEL_MAX: nivel_nuevo = self.NIVEL_MAX
        if nivel_nuevo < 0: nivel_nuevo = 0.0
        volumen = (nivel_nuevo / self.NIVEL_MAX) * self.CAPACIDAD_MAX
        self.nivel_actual = nivel_nuevo
        return nivel_nuevo, volumen
    
    def calcular_termodinamica(self, temp_actual, setpoint, calentador_on):
        if temp_actual < (setpoint - 2.0): calentador_on = True
        elif temp_actual > (setpoint + 2.0): calentador_on = False
        
        if calentador_on: temp_nueva = temp_actual + 0.08
        else: temp_nueva = temp_actual - 0.01
        
        temp_nueva = max(15.0, min(100.0, temp_nueva))
        self.temp_actual = temp_nueva
        return temp_nueva, calentador_on
    
    def calcular_tiempo_llenado(self, nivel_actual, caudal_in, caudal_out):
        if nivel_actual >= self.NIVEL_MAX: return 0.0
        if caudal_in <= caudal_out: return 9999.0
        volumen_actual = (nivel_actual / self.NIVEL_MAX) * self.CAPACIDAD_MAX
        volumen_faltante = self.CAPACIDAD_MAX - volumen_actual
        caudal_neto = caudal_in - caudal_out
        return volumen_faltante / caudal_neto if caudal_neto > 0 else 9999.0
    
    def detectar_fuga(self, caudal_in, caudal_out, nivel_actual, nivel_anterior):
        exceso_entrada = caudal_in > (caudal_out + 10.0)
        nivel_no_sube = (nivel_actual - nivel_anterior) < 0.1
        no_lleno = nivel_actual < 2990.0
        
        if abs(nivel_actual - nivel_anterior) < 0.1: self.ciclos_sin_cambio += 1
        else: self.ciclos_sin_cambio = 0
        
        alerta_fuga = exceso_entrada and nivel_no_sube and no_lleno and (self.ciclos_sin_cambio >= 3)
        self.nivel_anterior = nivel_actual
        return alerta_fuga
    
    def determinar_estado_sistema(self, alerta_fuga, nivel_actual):
        if alerta_fuga: return "ALERTA: FUGA DETECTADA"
        elif nivel_actual >= self.NIVEL_MAX: return "TANQUE LLENO"
        elif nivel_actual >= (self.NIVEL_MAX * 0.9): return "ALERTA: NIVEL ALTO"
        elif nivel_actual <= 0: return "TANQUE VACÍO"
        else: return "OPERACIÓN NORMAL"

def get_node_safe(client, idx, node_id):
    """Ayuda a obtener nodo formateado"""
    return client.get_node(f"ns={idx};i={node_id}")

def main():
    # 1. SERVER CONFIG (Middleware)
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4845/freeopcua/server/")
    server.set_server_name("Middleware Maestro")
    
    # Cargar modelo XML Oficial
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelos_xml", "tanque_nodeset.xml")
    if not os.path.exists(xml_path):
        logger.error("NO SE ENCUENTRA EL XML DE SIOME. Verifica el nombre del archivo.")
        return

    logger.info("Cargando modelo SiOME...")
    server.import_xml(xml_path)
    
    # Identificar Namespace
    uri = "http://upv.edu/TanqueIndustrial"
    idx_srv = server.get_namespace_index(uri)
    
    # Obtener variables PROPIAS (Middleware) usando IDs SiOME
    try:
        estado_sistema = server.get_node(f"ns={idx_srv};i=6014")
        alerta_fuga = server.get_node(f"ns={idx_srv};i=6013")
        tiempo_llenado = server.get_node(f"ns={idx_srv};i=6015")
    except Exception as e:
        logger.error(f"Error cargando variables del propio server: {e}")
        return

    server.start()
    logger.info("✓ Middleware Server iniciado (4845)")
    time.sleep(3)

    # 2. CLIENT CONFIG (Conectar a los otros)
    logger.info("Conectando a servidores sensores...")
    
    try:
        # --- CLIENTE NIVEL ---
        c_nivel = Client("opc.tcp://localhost:4840/freeopcua/server/")
        c_nivel.connect()
        idx_niv = c_nivel.get_namespace_index(uri)
        node_nivel = get_node_safe(c_nivel, idx_niv, 6016)
        node_volumen = get_node_safe(c_nivel, idx_niv, 6017)
        logger.info("✓ Conectado a Nivel")

        # --- CLIENTE TEMP ---
        c_temp = Client("opc.tcp://localhost:4841/freeopcua/server/")
        c_temp.connect()
        idx_tmp = c_temp.get_namespace_index(uri)
        node_temp = get_node_safe(c_temp, idx_tmp, 6022)
        node_sp = get_node_safe(c_temp, idx_tmp, 6023)
        node_cal = get_node_safe(c_temp, idx_tmp, 6024)
        logger.info("✓ Conectado a Temperatura")

        # --- CLIENTE ENTRADA ---
        c_ent = Client("opc.tcp://localhost:4842/freeopcua/server/")
        c_ent.connect()
        idx_ent = c_ent.get_namespace_index(uri)
        node_caudal_in = get_node_safe(c_ent, idx_ent, 6009)
        node_rpm = get_node_safe(c_ent, idx_ent, 6010)
        node_amp = get_node_safe(c_ent, idx_ent, 6011)
        logger.info("✓ Conectado a Entrada")

        # --- CLIENTE SALIDA ---
        c_sal = Client("opc.tcp://localhost:4843/freeopcua/server/")
        c_sal.connect()
        idx_sal = c_sal.get_namespace_index(uri)
        node_caudal_out = get_node_safe(c_sal, idx_sal, 6019)
        node_valvula = get_node_safe(c_sal, idx_sal, 6020)
        node_total = get_node_safe(c_sal, idx_sal, 6021)
        logger.info("✓ Conectado a Salida")

    except Exception as e:
        logger.error(f"Error conectando clientes: {e}")
        server.stop()
        return

    # Inicializar motores
    physics = PhysicsEngine()
    db = DatabaseManager()
    logger.info("MOTOR DE FÍSICA ACTIVO")

    ciclo = 0
    ultimo_envio = 0
    
    try:
        while True:
            ciclo += 1
            
            # --- LEER INPUTS ---
            rpm_val = node_rpm.get_value()
            valvula_val = node_valvula.get_value()
            setpoint_val = node_sp.get_value()
            calentador_state = node_cal.get_value()
            
            # --- CÁLCULOS ---
            c_in, amps = physics.calcular_fisica_entrada(rpm_val, physics.nivel_actual)
            c_out = physics.calcular_fisica_salida(valvula_val, physics.nivel_actual)
            tot_val = physics.actualizar_totalizador(c_out)
            niv_new, vol_new = physics.calcular_fisica_tanque(c_in, c_out, physics.nivel_actual)
            temp_new, cal_on = physics.calcular_termodinamica(physics.temp_actual, setpoint_val, calentador_state)
            t_llenado = physics.calcular_tiempo_llenado(physics.nivel_actual, c_in, c_out)
            is_fuga = physics.detectar_fuga(c_in, c_out, physics.nivel_actual, physics.nivel_anterior)
            est_sys = physics.determinar_estado_sistema(is_fuga, physics.nivel_actual)
            
            # --- TELEGRAM ---
            tiempo_now = time.time()
            if (is_fuga or est_sys == "TANQUE LLENO"):
                if (tiempo_now - ultimo_envio > 60):
                    msg = f"🚨 ALERTA SCADA: {est_sys}\nNivel: {niv_new:.1f} mm"
                    threading.Thread(target=enviar_alerta_telegram, args=(msg,)).start()
                    ultimo_envio = tiempo_now

            # --- ESCRIBIR RESULTADOS (A sensores y a sí mismo) ---
            # Sensores
            node_caudal_in.set_value(c_in)
            node_amp.set_value(amps)
            node_caudal_out.set_value(c_out)
            node_total.set_value(tot_val)
            node_nivel.set_value(niv_new)
            node_volumen.set_value(vol_new)
            node_temp.set_value(temp_new)
            node_cal.set_value(cal_on)
            
            # Propios (Middleware)
            estado_sistema.set_value(est_sys)
            alerta_fuga.set_value(is_fuga)
            tiempo_llenado.set_value(t_llenado)

            # --- DB & LOGGING ---
            if ciclo % 10 == 0:
                logger.info(f"Nivel: {niv_new:.1f}mm | In: {c_in:.1f} | Out: {c_out:.1f} | Temp: {temp_new:.1f}")
            
            if ciclo % 5 == 0:
                est_temp = "CALENTANDO" if cal_on else "OK"
                db.insert_data(niv_new, temp_new, c_in, c_out, est_sys, cal_on, est_temp)

            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Deteniendo...")
    finally:
        c_nivel.disconnect()
        c_temp.disconnect()
        c_ent.disconnect()
        c_sal.disconnect()
        server.stop()

if __name__ == "__main__":
    main()
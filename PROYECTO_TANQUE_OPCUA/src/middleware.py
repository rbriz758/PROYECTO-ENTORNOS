"""
MIDDLEWARE - MOTOR DE FÍSICA MAESTRO
Puerto: 4845
Este es el cerebro del sistema que:
1. Lee inputs (RPM, Posición Válvula, SetPoint)
2. Calcula toda la física (caudales, nivel, temperatura, etc.)
3. Escribe los resultados en los servidores esclavos
4. Detecta anomalías (fugas, tiempos de llenado)
"""

from opcua import Server, Client
import time
import logging
import requests
import threading
import math
import os
import xml.etree.ElementTree as ET
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
            logger.warning(f"Error enviando a Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Fallo al conectar con Telegram: {e}")

class PhysicsEngine:
    """Motor de Física Centralizado"""
    
    def __init__(self):
        # Constantes del tanque
        self.NIVEL_MAX = 3000.0  # mm
        self.CAPACIDAD_MAX = 10000.0  # Litros
        self.AREA_BASE = self.CAPACIDAD_MAX / (self.NIVEL_MAX / 1000.0)  # m²
        
        # Estado actual del sistema
        self.nivel_actual = 0.0
        self.temp_actual = 20.0
        self.totalizador = 0.0
        self.nivel_anterior = 0.0  # Para detectar fugas
        self.ciclos_sin_cambio = 0
        
        # Variables de física
        self.caudal_in = 0.0
        self.caudal_out = 0.0
        
    def calcular_fisica_entrada(self, rpm_bomba, nivel_actual):
        """
        Física de Entrada (Bomba)
        Caudal_In = RPM * 0.05
        Si Nivel >= MAX, Caudal_In = 0 (Físicamente imposible meter más)
        Amperios = 2.0 + (Caudal_In * 0.15)
        """
        if nivel_actual >= self.NIVEL_MAX:
            caudal_in = 0.0
        else:
            caudal_in = rpm_bomba * 0.05  # L/min
            
        amperios = 2.0 + (caudal_in * 0.15)
        
        self.caudal_in = caudal_in
        return caudal_in, amperios
    
    def calcular_fisica_salida(self, posicion_valvula, nivel_mm):
        """
        Física de Salida (Válvula + Gravedad)
        Factor_Presion = sqrt(Nivel_mm / 3000)
        Caudal_Out = (Posicion_Valvula / 100) * 50.0 * Factor_Presion
        """
        if nivel_mm <= 0:
            factor_presion = 0.0
        else:
            factor_presion = math.sqrt(nivel_mm / 3000.0)
        
        caudal_out = (posicion_valvula / 100.0) * 50.0 * factor_presion
        
        self.caudal_out = caudal_out
        return caudal_out
    
    def actualizar_totalizador(self, caudal_out, dt=1.0):
        """
        Actualiza el totalizador (metros cúbicos acumulados)
        Totalizador += (Caudal_Out / 60) / 1000 * dt
        """
        self.totalizador += (caudal_out / 60.0) / 1000.0 * dt
        return self.totalizador
    
    def calcular_fisica_tanque(self, caudal_in, caudal_out, nivel_actual, dt=1.0):
        """
        Física del Tanque (Balance de Masas)
        Delta_Nivel = (Caudal_In - Caudal_Out) * 0.5
        """
        delta_nivel = (caudal_in - caudal_out) * 0.5 * dt
        nivel_nuevo = nivel_actual + delta_nivel
        
        # CLAMPING (Vital)
        if nivel_nuevo > self.NIVEL_MAX:
            nivel_nuevo = self.NIVEL_MAX
        if nivel_nuevo < 0:
            nivel_nuevo = 0.0
        
        # Calcular volumen (relación lineal)
        volumen = (nivel_nuevo / self.NIVEL_MAX) * self.CAPACIDAD_MAX
        
        self.nivel_actual = nivel_nuevo
        return nivel_nuevo, volumen
    
    def calcular_termodinamica(self, temp_actual, setpoint, calentador_on):
        """
        Termodinámica con Histéresis
        Si Calentador ON: Temp += 0.08
        Si OFF: Temp -= 0.01
        """
        # Lógica de histéresis (±2°C)
        if temp_actual < (setpoint - 2.0):
            calentador_on = True
        elif temp_actual > (setpoint + 2.0):
            calentador_on = False
        
        # Actualizar temperatura
        if calentador_on:
            temp_nueva = temp_actual + 0.08
        else:
            temp_nueva = temp_actual - 0.01
        
        # Limitar temperatura (mínimo ambiente 15°C, máximo 100°C)
        temp_nueva = max(15.0, min(100.0, temp_nueva))
        
        self.temp_actual = temp_nueva
        return temp_nueva, calentador_on
    
    def calcular_tiempo_llenado(self, nivel_actual, caudal_in, caudal_out):
        """
        Tiempo de Llenado
        Si Nivel >= 3000: Tiempo = 0 (Lleno)
        Si Caudal_In <= Caudal_Out: Tiempo = 9999 (Infinito/Vaciando)
        Else: (10000 - Volumen) / (Caudal_In - Caudal_Out)
        """
        if nivel_actual >= self.NIVEL_MAX:
            return 0.0
        
        if caudal_in <= caudal_out:
            return 9999.0
        
        volumen_actual = (nivel_actual / self.NIVEL_MAX) * self.CAPACIDAD_MAX
        volumen_faltante = self.CAPACIDAD_MAX - volumen_actual
        caudal_neto = caudal_in - caudal_out
        
        tiempo_minutos = volumen_faltante / caudal_neto if caudal_neto > 0 else 9999.0
        return tiempo_minutos
    
    def detectar_fuga(self, caudal_in, caudal_out, nivel_actual, nivel_anterior):
        """
        Detección de Fugas (Lógica Corregida)
        Alerta_Fuga = True SI:
        - (Caudal_In > Caudal_Out + 10) Y
        - (Nivel NO sube) Y
        - (Nivel < 2990)
        """
        # Condición 1: Hay más entrada que salida
        exceso_entrada = caudal_in > (caudal_out + 10.0)
        
        # Condición 2: El nivel no está subiendo (tolerancia 0.1mm)
        nivel_no_sube = (nivel_actual - nivel_anterior) < 0.1
        
        # Condición 3: El tanque no está completamente lleno
        no_lleno = nivel_actual < 2990.0
        
        # Si el nivel no ha cambiado, incrementar contador
        if abs(nivel_actual - nivel_anterior) < 0.1:
            self.ciclos_sin_cambio += 1
        else:
            self.ciclos_sin_cambio = 0
        
        # Alerta de fuga solo si se cumplen todas las condiciones
        # y han pasado al menos 3 ciclos sin cambio
        alerta_fuga = exceso_entrada and nivel_no_sube and no_lleno and (self.ciclos_sin_cambio >= 3)
        
        self.nivel_anterior = nivel_actual
        return alerta_fuga
    
    def determinar_estado_sistema(self, alerta_fuga, nivel_actual):
        """Determina el estado general del sistema"""
        if alerta_fuga:
            return "ALERTA: FUGA DETECTADA"
        elif nivel_actual >= self.NIVEL_MAX:
            return "TANQUE LLENO"
        elif nivel_actual >= (self.NIVEL_MAX * 0.9):
            return "ALERTA: NIVEL ALTO"
        elif nivel_actual <= 0:
            return "TANQUE VACÍO"
        else:
            return "OPERACIÓN NORMAL"

def load_xml_model(server, xml_path):
    """Carga el modelo XML unificado"""
    tree = ET.parse(xml_path)
    root_xml = tree.getroot()
    
    uri = "http://tanque.industrial/model"
    idx = server.register_namespace(uri)
    
    objects = server.get_objects_node()
    model_name = root_xml.get("name")
    model_obj = objects.add_object(idx, model_name)
    
    nodes_map = {"Objects": {}}
    
    for obj_xml in root_xml.findall("Object"):
        obj_name = obj_xml.get("name")
        opcua_obj = model_obj.add_object(idx, obj_name)
        nodes_map["Objects"][obj_name] = {"Variables": {}}
        
        for node_xml in obj_xml.findall("Node"):
            var_name = node_xml.get("name")
            var_type = node_xml.get("type")
            var_initial = node_xml.get("initial")
            
            val = 0.0
            if var_type == "Double": val = float(var_initial)
            elif var_type == "Boolean": val = (var_initial.lower() == "true")
            elif var_type == "String": val = str(var_initial)
                
            opcua_var = opcua_obj.add_variable(idx, var_name, val)
            opcua_var.set_writable()
            nodes_map["Objects"][obj_name]["Variables"][var_name] = opcua_var
            
    return idx, nodes_map


def main():
    # Crear servidor middleware
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4845/freeopcua/server/")
    server.set_server_name("Middleware Maestro")
    
    # Cargar modelo XML unificado
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelos_xml", "modelo_unificado.xml")
    idx, nodes_map = load_xml_model(server, xml_path)
    
    # Obtener referencias a las variables propias del middleware
    # Estructura: TanqueIndustrial -> Middleware -> Variables
    middleware_vars = nodes_map["Objects"]["Middleware"]["Variables"]
    estado_sistema = middleware_vars["Estado_Sistema"]
    alerta_fuga = middleware_vars["Alerta_Fuga"]
    tiempo_llenado = middleware_vars["Tiempo_Llenado"]
    
    # Iniciar servidor
    server.start()
    logger.info("✓ Servidor Middleware iniciado en opc.tcp://0.0.0.0:4845")
    
    # Esperar a que otros servidores se inicien
    time.sleep(3)
    
    # Conectar a los servidores esclavos como cliente
    logger.info("Conectando a servidores esclavos...")
    
    try:
        client_nivel = Client("opc.tcp://localhost:4840/freeopcua/server/")
        client_nivel.connect()
        # Navegar por el árbol de objetos
        # Navegar por el árbol de objetos (Estructura Unificada)
        # Root -> Objects -> TanqueIndustrial -> Nivel
        root = client_nivel.get_objects_node()
        tanque_obj = root.get_child(["2:TanqueIndustrial"])
        nivel_obj = tanque_obj.get_child(["2:Nivel"])
        
        nivel_mm_node = nivel_obj.get_child(["2:Nivel_mm"])
        volumen_l_node = nivel_obj.get_child(["2:Volumen_L"])
        logger.info("✓ Conectado a Servidor Nivel")
    except Exception as e:
        logger.error(f"Error conectando a Servidor Nivel: {e}")
        logger.error(f"Detalles: {type(e).__name__}")
        return
    
    try:
        client_temp = Client("opc.tcp://localhost:4841/freeopcua/server/")
        client_temp.connect()
        root = client_temp.get_objects_node()
        tanque_obj = root.get_child(["2:TanqueIndustrial"])
        temp_obj = tanque_obj.get_child(["2:Temperatura"])
        
        temperatura_node = temp_obj.get_child(["2:Temperatura"])
        setpoint_node = temp_obj.get_child(["2:SetPoint"])
        calentador_node = temp_obj.get_child(["2:Calentador_On"])
        logger.info("✓ Conectado a Servidor Temperatura")
    except Exception as e:
        logger.error(f"Error conectando a Servidor Temperatura: {e}")
        logger.error(f"Detalles: {type(e).__name__}")
        return
    
    try:
        client_entrada = Client("opc.tcp://localhost:4842/freeopcua/server/")
        client_entrada.connect()
        root = client_entrada.get_objects_node()
        tanque_obj = root.get_child(["2:TanqueIndustrial"])
        entrada_obj = tanque_obj.get_child(["2:Entrada"])
        
        caudal_in_node = entrada_obj.get_child(["2:Caudal_In"])
        rpm_bomba_node = entrada_obj.get_child(["2:RPM_Bomba"])
        amperios_node = entrada_obj.get_child(["2:Amperios"])
        logger.info("✓ Conectado a Servidor Entrada")
    except Exception as e:
        logger.error(f"Error conectando a Servidor Entrada: {e}")
        logger.error(f"Detalles: {type(e).__name__}")
        return
    
    try:
        client_salida = Client("opc.tcp://localhost:4843/freeopcua/server/")
        client_salida.connect()
        root = client_salida.get_objects_node()
        tanque_obj = root.get_child(["2:TanqueIndustrial"])
        salida_obj = tanque_obj.get_child(["2:Salida"])
        
        caudal_out_node = salida_obj.get_child(["2:Caudal_Out"])
        posicion_valvula_node = salida_obj.get_child(["2:Posicion_Valvula"])
        totalizador_node = salida_obj.get_child(["2:Totalizador"])
        logger.info("✓ Conectado a Servidor Salida")
    except Exception as e:
        logger.error(f"Error conectando a Servidor Salida: {e}")
        logger.error(f"Detalles: {type(e).__name__}")
        return
    
    # Inicializar motor de física
    physics = PhysicsEngine()
    
    # Inicializar Base de Datos
    db = DatabaseManager()
    logger.info("✓ Base de Datos conectada")
    
    logger.info("=" * 60)
    logger.info("MOTOR DE FÍSICA ACTIVO - Iniciando cálculos...")
    logger.info("=" * 60)
    
    # Bucle principal
    ciclo = 0
    ultimo_envio = 0
    try:
        while True:
            ciclo += 1
            
            # ===== LEER INPUTS (Control del usuario) =====
            rpm_bomba = rpm_bomba_node.get_value()
            posicion_valvula = posicion_valvula_node.get_value()
            setpoint = setpoint_node.get_value()
            
            # ===== CALCULAR FÍSICA =====
            
            # 1. Física de Entrada (Bomba)
            caudal_in, amperios = physics.calcular_fisica_entrada(rpm_bomba, physics.nivel_actual)
            
            # 2. Física de Salida (Válvula + Gravedad)
            caudal_out = physics.calcular_fisica_salida(posicion_valvula, physics.nivel_actual)
            
            # 3. Actualizar Totalizador
            totalizador_val = physics.actualizar_totalizador(caudal_out)
            
            # 4. Física del Tanque (Balance de Masas)
            nivel_nuevo, volumen = physics.calcular_fisica_tanque(
                caudal_in, caudal_out, physics.nivel_actual
            )
            
            # 5. Termodinámica
            temp_nueva, calentador_on = physics.calcular_termodinamica(
                physics.temp_actual, setpoint, calentador_node.get_value()
            )
            
            # 6. Tiempo de Llenado
            tiempo_llenado_val = physics.calcular_tiempo_llenado(
                physics.nivel_actual, caudal_in, caudal_out
            )
            
            # 7. Detección de Fugas
            alerta_fuga_val = physics.detectar_fuga(
                caudal_in, caudal_out, physics.nivel_actual, physics.nivel_anterior
            )
            
            # 8. Estado del Sistema
            estado_val = physics.determinar_estado_sistema(alerta_fuga_val, physics.nivel_actual)
            
            # ===== NOTIFICACIONES TELEGRAM =====
            tiempo_actual = time.time()
            if (alerta_fuga_val or estado_val == "TANQUE LLENO"):
                if (tiempo_actual - ultimo_envio > 60):
                    logger.info(f"Intentando enviar alerta a Telegram: {estado_val}")
                    mensaje = f"🚨 ALERTA SCADA: {estado_val}\nNivel actual: {physics.nivel_actual:.1f} mm"
                    # Enviar en un hilo separado para no bloquear el SCADA
                    threading.Thread(target=enviar_alerta_telegram, args=(mensaje,)).start()
                    ultimo_envio = tiempo_actual
                else:
                    # Log de debug opcional para saber que se está ignorando por spam
                    pass

            # ===== ESCRIBIR RESULTADOS EN LOS SERVIDORES =====
            
            # Servidor Entrada
            caudal_in_node.set_value(caudal_in)
            amperios_node.set_value(amperios)
            
            # Servidor Salida
            caudal_out_node.set_value(caudal_out)
            totalizador_node.set_value(totalizador_val)
            
            # Servidor Nivel
            nivel_mm_node.set_value(nivel_nuevo)
            volumen_l_node.set_value(volumen)
            
            # Servidor Temperatura
            temperatura_node.set_value(temp_nueva)
            calentador_node.set_value(calentador_on)
            
            # Middleware (propias)
            estado_sistema.set_value(estado_val)
            alerta_fuga.set_value(alerta_fuga_val)
            tiempo_llenado.set_value(tiempo_llenado_val)
            
            # Log cada 10 ciclos
            if ciclo % 10 == 0:
                logger.info(f"[Ciclo {ciclo}] Nivel: {nivel_nuevo:.1f}mm | "
                           f"Caudal In: {caudal_in:.1f} L/min | "
                           f"Caudal Out: {caudal_out:.1f} L/min | "
                           f"Temp: {temp_nueva:.1f}°C | "
                           f"Estado: {estado_val}")
            
            if alerta_fuga_val and ciclo % 5 == 0:
                logger.warning("⚠️  ALERTA DE FUGA ACTIVA")
            
            # Guardar en Base de Datos cada 5 segundos (aprox)
            if ciclo % 5 == 0:
                # Determinar estado de temperatura
                estado_temp = "CALENTANDO" if calentador_on else "TEMP ALCANZADA"
                
                db.insert_data(
                    nivel_nuevo, 
                    temp_nueva, 
                    caudal_in, 
                    caudal_out, 
                    estado_val,
                    calentador_on,
                    estado_temp
                )
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Deteniendo middleware...")
    finally:
        client_nivel.disconnect()
        client_temp.disconnect()
        client_entrada.disconnect()
        client_salida.disconnect()
        server.stop()
        logger.info("Middleware detenido")

if __name__ == "__main__":
    main()

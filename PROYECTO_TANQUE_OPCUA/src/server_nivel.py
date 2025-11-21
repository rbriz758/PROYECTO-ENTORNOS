"""
Servidor OPC UA - Sensor de Nivel
Puerto: 4840
Actúa como esclavo/sensor - Los valores son escritos por el Middleware
"""

from opcua import Server
import time
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Crear servidor
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("Servidor Nivel")
    
    # Configurar namespace
    uri = "http://tanque.industrial/nivel"
    idx = server.register_namespace(uri)
    
    # Crear objeto raíz
    objects = server.get_objects_node()
    nivel_obj = objects.add_object(idx, "Nivel")
    
    # Crear variables WRITABLES (para que el middleware pueda escribir)
    nivel_mm = nivel_obj.add_variable(idx, "Nivel_mm", 0.0)
    volumen_l = nivel_obj.add_variable(idx, "Volumen_L", 0.0)
    estado_sensor = nivel_obj.add_variable(idx, "Estado_Sensor", True)
    
    # IMPORTANTE: Hacer las variables escribibles
    nivel_mm.set_writable()
    volumen_l.set_writable()
    estado_sensor.set_writable()
    
    # Iniciar servidor
    server.start()
    logger.info("✓ Servidor Nivel iniciado en opc.tcp://0.0.0.0:4840")
    logger.info("  - Nivel_mm (Writable)")
    logger.info("  - Volumen_L (Writable)")
    logger.info("  - Estado_Sensor (Writable)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo servidor...")
    finally:
        server.stop()
        logger.info("Servidor detenido")

if __name__ == "__main__":
    main()

"""
Servidor OPC UA - Sensor de Temperatura
Puerto: 4841
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
    server.set_endpoint("opc.tcp://0.0.0.0:4841/freeopcua/server/")
    server.set_server_name("Servidor Temperatura")
    
    # Configurar namespace
    uri = "http://tanque.industrial/temperatura"
    idx = server.register_namespace(uri)
    
    # Crear objeto raíz
    objects = server.get_objects_node()
    temp_obj = objects.add_object(idx, "Temperatura")
    
    # Crear variables WRITABLES
    temperatura = temp_obj.add_variable(idx, "Temperatura", 20.0)
    setpoint = temp_obj.add_variable(idx, "SetPoint", 45.0)
    calentador_on = temp_obj.add_variable(idx, "Calentador_On", False)
    
    # IMPORTANTE: Hacer las variables escribibles
    temperatura.set_writable()
    setpoint.set_writable()
    calentador_on.set_writable()
    
    # Iniciar servidor
    server.start()
    logger.info("✓ Servidor Temperatura iniciado en opc.tcp://0.0.0.0:4841")
    logger.info("  - Temperatura (Writable)")
    logger.info("  - SetPoint (Writable)")
    logger.info("  - Calentador_On (Writable)")
    
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

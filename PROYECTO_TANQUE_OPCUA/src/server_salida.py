"""
Servidor OPC UA - Salida (Válvula)
Puerto: 4843
Actúa como esclavo/actuador - Los valores son escritos por el Middleware
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
    server.set_endpoint("opc.tcp://0.0.0.0:4843/freeopcua/server/")
    server.set_server_name("Servidor Salida")
    
    # Configurar namespace
    uri = "http://tanque.industrial/salida"
    idx = server.register_namespace(uri)
    
    # Crear objeto raíz
    objects = server.get_objects_node()
    salida_obj = objects.add_object(idx, "Salida")
    
    # Crear variables WRITABLES
    caudal_out = salida_obj.add_variable(idx, "Caudal_Out", 0.0)
    posicion_valvula = salida_obj.add_variable(idx, "Posicion_Valvula", 0.0)
    totalizador = salida_obj.add_variable(idx, "Totalizador", 0.0)
    
    # IMPORTANTE: Hacer las variables escribibles
    caudal_out.set_writable()
    posicion_valvula.set_writable()
    totalizador.set_writable()
    
    # Iniciar servidor
    server.start()
    logger.info("✓ Servidor Salida iniciado en opc.tcp://0.0.0.0:4843")
    logger.info("  - Caudal_Out (Writable)")
    logger.info("  - Posicion_Valvula (Writable)")
    logger.info("  - Totalizador (Writable)")
    
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

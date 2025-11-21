"""
Servidor OPC UA - Entrada (Bomba)
Puerto: 4842
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
    server.set_endpoint("opc.tcp://0.0.0.0:4842/freeopcua/server/")
    server.set_server_name("Servidor Entrada")
    
    # Configurar namespace
    uri = "http://tanque.industrial/entrada"
    idx = server.register_namespace(uri)
    
    # Crear objeto raíz
    objects = server.get_objects_node()
    entrada_obj = objects.add_object(idx, "Entrada")
    
    # Crear variables WRITABLES
    caudal_in = entrada_obj.add_variable(idx, "Caudal_In", 0.0)
    rpm_bomba = entrada_obj.add_variable(idx, "RPM_Bomba", 0.0)
    amperios = entrada_obj.add_variable(idx, "Amperios", 0.0)
    
    # IMPORTANTE: Hacer las variables escribibles
    caudal_in.set_writable()
    rpm_bomba.set_writable()
    amperios.set_writable()
    
    # Iniciar servidor
    server.start()
    logger.info("✓ Servidor Entrada iniciado en opc.tcp://0.0.0.0:4842")
    logger.info("  - Caudal_In (Writable)")
    logger.info("  - RPM_Bomba (Writable)")
    logger.info("  - Amperios (Writable)")
    
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

"""
Servidor OPC UA - Sensor de Salida (Versión SiOME NodeSet2)
Puerto: 4843
"""

from opcua import Server, ua
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4843/freeopcua/server/")
    server.set_server_name("Servidor Salida")

    # Ruta al XML SiOME
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelos_xml", "tanque_nodeset.xml")

    if not os.path.exists(xml_path):
        logger.error(f"❌ No se encuentra el archivo XML en: {xml_path}")
        return

    logger.info("Cargando modelo SiOME...")
    server.import_xml(xml_path)

    uri = "http://upv.edu/TanqueIndustrial"
    idx = server.get_namespace_index(uri)

    try:
        # IDs extraídos de tu XML SiOME para Salida
        caudal_out_node = server.get_node(f"ns={idx};i=6019")   # Caudal_Out
        pos_valvula_node = server.get_node(f"ns={idx};i=6020")  # Posicion_Valvula
        totalizador_node = server.get_node(f"ns={idx};i=6021")  # Totalizador
        
        logger.info("✓ Variables de Salida localizadas.")
        
        # Inicializar
        caudal_out_node.set_value(0.0)
        pos_valvula_node.set_value(0.0)
        totalizador_node.set_value(0.0)

    except Exception as e:
        logger.error(f"Error enganchando variables: {e}")

    server.start()
    logger.info("Servidor Salida corriendo en puerto 4843")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo servidor...")
    finally:
        server.stop()

if __name__ == "__main__":
    main()
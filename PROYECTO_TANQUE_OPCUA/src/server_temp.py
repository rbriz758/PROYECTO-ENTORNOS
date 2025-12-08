"""
Servidor OPC UA - Sensor de Temperatura (Versión SiOME NodeSet2)
Puerto: 4841
"""

from opcua import Server, ua
import time
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 1. Crear servidor
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4841/freeopcua/server/")
    server.set_server_name("Servidor Temperatura")

    # 2. Definir ruta del XML de SiOME
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelos_xml", "tanque_nodeset.xml")

    if not os.path.exists(xml_path):
        logger.error(f"❌ No se encuentra el archivo XML en: {xml_path}")
        return

    # 3. Importar XML
    logger.info(f"Cargando modelo SiOME desde: {xml_path}")
    server.import_xml(xml_path)

    # 4. Obtener Namespace e IDs
    uri = "http://upv.edu/TanqueIndustrial"
    idx = server.get_namespace_index(uri)
    logger.info(f"Namespace '{uri}' índice: {idx}")

    try:
        # IDs extraídos de tu XML SiOME para Temperatura
        temp_node = server.get_node(f"ns={idx};i=6022")       # Temperatura
        setpoint_node = server.get_node(f"ns={idx};i=6023")   # SetPoint
        calentador_node = server.get_node(f"ns={idx};i=6024") # Calentador_On
        
        logger.info("✓ Variables de Temperatura localizadas.")
        
        # Inicializar valores
        temp_node.set_value(20.0)
        setpoint_node.set_value(45.0)
        calentador_node.set_value(False)

    except Exception as e:
        logger.error(f"Error enganchando variables: {e}")

    # 5. Iniciar servidor
    server.start()
    logger.info("Servidor Temperatura corriendo en puerto 4841")
    
    try:
        while True:
            time.sleep(1)
            # Aquí podrías simular cambios de temperatura si quisieras
    except KeyboardInterrupt:
        logger.info("Deteniendo servidor...")
    finally:
        server.stop()
        logger.info("Servidor detenido")

if __name__ == "__main__":
    main()
"""
Servidor OPC UA - Sensor de Nivel (Versión SiOME NodeSet2)
Puerto: 4840
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
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("Servidor Nivel")

    # 2. Definir ruta del XML de SiOME
    # Asegúrate de que el archivo se llame así en tu carpeta
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelos_xml", "tanque_nodeset.xml")

    # 3. IMPORTAR el XML Oficial
    if not os.path.exists(xml_path):
        logger.error(f"No se encuentra el archivo: {xml_path}")
        return

    logger.info(f"Cargando modelo SiOME desde: {xml_path}")
    server.import_xml(xml_path)

    # 4. Obtener las variables usando los IDs de SiOME
    # Primero buscamos qué índice le dio Python a tu namespace "http://upv.edu/TanqueIndustrial"
    uri = "http://upv.edu/TanqueIndustrial"
    idx = server.get_namespace_index(uri)
    logger.info(f"Namespace '{uri}' registrado con índice: {idx}")

    # Ahora "enganchamos" las variables usando los IDs que viste en SiOME (i=6016, etc.)
    # Nota: Usamos f"ns={idx};i=XXXX" para que sea robusto
    try:
        # Estos IDs salen de tu captura de pantalla de SiOME
        nivel_node = server.get_node(f"ns={idx};i=6016")        # Nivel_mm
        volumen_node = server.get_node(f"ns={idx};i=6017")      # Volumen_L
        sensor_node = server.get_node(f"ns={idx};i=6018")       # Estado_Sensor
        
        logger.info("✓ Variables de Nivel localizadas correctamente en el XML")
        
        # Inicializamos valores para probar
        nivel_node.set_value(0.0)
        volumen_node.set_value(0.0)
        sensor_node.set_value(True)

    except Exception as e:
        logger.error(f"Error localizando variables: {e}")
        logger.warning("Verifica que los IDs en el código coincidan con tu XML de SiOME")

    # 5. Iniciar servidor
    server.start()
    logger.info("Servidor Nivel iniciado y rodando.")
    
    try:
        # Bucle de simulación simple (Opcional: Para que veas que se mueve)
        count = 0.0
        while True:
            time.sleep(1)
            # Descomenta esto si quieres que el servidor simule datos solo:
            # count += 0.5
            # if count > 100: count = 0
            # nivel_node.set_value(count)
            # volumen_node.set_value(count * 3.5)
            
    except KeyboardInterrupt:
        logger.info("Deteniendo servidor...")
    finally:
        server.stop()
        logger.info("Servidor detenido")

if __name__ == "__main__":
    main()
"""
Servidor OPC UA - Sensor de Salida (Válvula)
Puerto: 4843
"""

from opcua import Server
import time
import logging
import os
import xml.etree.ElementTree as ET

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    # Crear servidor
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4843/freeopcua/server/")
    server.set_server_name("Servidor Salida")
    
    # Cargar modelo XML unificado
    xml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelos_xml", "modelo_unificado.xml")
    idx, nodes_map = load_xml_model(server, xml_path)
    
    # Iniciar servidor
    server.start()
    logger.info("✓ Servidor Salida iniciado en opc.tcp://0.0.0.0:4843")
    logger.info("  - Modelo cargado desde XML Unificado")
    
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

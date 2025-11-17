import asyncio
from asyncua import Client, Server, ua
import traceback


SOURCE_ENDPOINTS = {
    "ph": "opc.tcp://127.0.0.1:4840/server_ph/",
    "temp": "opc.tcp://127.0.0.1:4841/server_temp/",
    "nivel": "opc.tcp://127.0.0.1:4845/server_nivel/",
    "bomba": "opc.tcp://127.0.0.1:4843/server_bomba/",
}


async def read_node_value(client: Client, node_identifier: str):
    try:
        # node_identifier expected like 'ns=2;s=PH_Actual' or just the name 'PH_Actual'
        if not node_identifier.startswith("ns="):
            nodeid = f"ns=2;s={node_identifier}"
        else:
            nodeid = node_identifier
        # NOTE: This function will be wrapped by a resolver that can cache resolved nodes.
        try:
            node = client.get_node(nodeid)
            val = await node.read_value()
            return val
        except Exception:
            pass

        try:
            node = client.get_node(ua.NodeId(node_identifier, 2))
            val = await node.read_value()
            return val
        except Exception:
            pass

        # Fallback: try to find the variable by browsing Objects -> Sensor_* -> variable
        try:
            objs = client.nodes.objects
            children = await objs.get_children()
            parent_map = {
                'PH_Actual': 'Sensor_PH',
                'Temperatura_Agua': 'Sensor_Temperatura',
                'Nivel_Agua_Porcentaje': 'Sensor_Nivel',
                'Bomba_Status': 'Sensor_Bomba',
            }
            search_name = node_identifier.replace('ns=2;s=', '')
            parent_name = parent_map.get(search_name, None)
            for child in children:
                try:
                    bn = await child.read_browse_name()
                    if parent_name and bn.Name == parent_name:
                        vars = await child.get_children()
                        for v in vars:
                            try:
                                vbn = await v.read_browse_name()
                                if vbn.Name == search_name:
                                    val = await v.read_value()
                                    return val
                            except Exception:
                                continue
                except Exception:
                    continue
        except Exception:
            pass

        return None
    except Exception:
        return None


async def middleware_loop():
    # Setup server (middleware exposes processed nodes)
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4844/middleware/")

    mw_obj = await server.nodes.objects.add_object(2, "Middleware_Piscina")
    estado_var = await mw_obj.add_variable(2, "Estado_Alerta_Global", "OK")
    dosis_var = await mw_obj.add_variable(2, "Dosis_Recomendada", 0.0)
    ph_proc_var = await mw_obj.add_variable(2, "PH_Procesado", 0.0)
    await estado_var.set_writable()
    await dosis_var.set_writable()
    await ph_proc_var.set_writable()

    await server.start()
    print("[middleware] Servidor OPC UA iniciado en opc.tcp://0.0.0.0:4844/middleware/")

    # Create clients
    clients = {}
    for key, ep in SOURCE_ENDPOINTS.items():
        clients[key] = Client(ep)

    # Connect clients (with retries)
    async def ensure_connect(client, name):
        while True:
            try:
                await client.connect()
                print(f"[middleware] Conectado a {name}")
                return
            except Exception as e:
                print(f"[middleware] Error conectando a {name}: {e}")
                await asyncio.sleep(2)

    try:
        await asyncio.gather(*(ensure_connect(clients[k], k) for k in clients))

        # resolved_nodes caches Node objects per client name and variable name
        resolved_nodes = {k: {} for k in clients}

        async def get_resolved_node(client_name, client, var_name):
            # return cached node if exists
            if var_name in resolved_nodes[client_name]:
                return resolved_nodes[client_name][var_name]
            # try to resolve and cache
            node = None
            # try by ns=2;s=var_name
            nodeid_str = f"ns=2;s={var_name}"
            try:
                n = client.get_node(nodeid_str)
                # validate by reading once
                await n.read_value()
                node = n
            except Exception:
                pass
            if node is None:
                # try to find by browsing
                try:
                    objs = client.nodes.objects
                    children = await objs.get_children()
                    parent_map = {
                        'PH_Actual': 'Sensor_PH',
                        'Temperatura_Agua': 'Sensor_Temperatura',
                        'Nivel_Agua_Porcentaje': 'Sensor_Nivel',
                        'Bomba_Status': 'Sensor_Bomba',
                    }
                    parent_name = parent_map.get(var_name, None)
                    for child in children:
                        try:
                            bn = await child.read_browse_name()
                            if parent_name and bn.Name == parent_name:
                                vars = await child.get_children()
                                for v in vars:
                                    try:
                                        vbn = await v.read_browse_name()
                                        if vbn.Name == var_name:
                                            node = v
                                            break
                                    except Exception:
                                        continue
                        except Exception:
                            continue
                        if node is not None:
                            break
                except Exception:
                    pass
            if node is not None:
                resolved_nodes[client_name][var_name] = node
            return node

        while True:
            try:
                # Use resolved cached nodes when possible
                ph_node = await get_resolved_node('ph', clients['ph'], 'PH_Actual')
                temp_node = await get_resolved_node('temp', clients['temp'], 'Temperatura_Agua')
                nivel_node = await get_resolved_node('nivel', clients['nivel'], 'Nivel_Agua_Porcentaje')
                bomba_node = await get_resolved_node('bomba', clients['bomba'], 'Bomba_Status')

                ph = await ph_node.read_value() if ph_node is not None else None
                temp = await temp_node.read_value() if temp_node is not None else None
                nivel = await nivel_node.read_value() if nivel_node is not None else None
                bomba = await bomba_node.read_value() if bomba_node is not None else None

                # Normalize values
                ph_val = float(ph) if ph is not None else 0.0
                nivel_val = int(nivel) if nivel is not None else 0
                bomba_val = bool(bomba) if bomba is not None else None

                # Compute alerts: build list of alert parts so multiple conditions are shown
                alert_parts = []
                dosis = 0.0

                if ph is None:
                    alert_parts.append("PH Desconocido")
                else:
                    if ph_val < 7.2:
                        alert_parts.append("PH Bajo")
                        dosis = round(100.0 * (7.2 - ph_val), 3)
                    elif ph_val > 7.8:
                        alert_parts.append("PH Alto")

                if nivel is None:
                    alert_parts.append("Nivel Desconocido")
                else:
                    if nivel_val < 90:
                        alert_parts.append("Nivel Bajo")

                if len(alert_parts) == 0:
                    estado = "OK"
                else:
                    estado = "ALERTA: " + " | ".join(alert_parts)

                # Publish to middleware nodes (use native types)
                await ph_proc_var.write_value(ph_val)
                await dosis_var.write_value(dosis)
                await estado_var.write_value(estado)

                print(f"[middleware] PH={ph_val} NIVEL={nivel_val} BOMBA={bomba_val} ESTADO={estado} DOSIS={dosis}")

            except Exception:
                print("[middleware] Error en ciclo de lectura:\n" + traceback.format_exc())

            await asyncio.sleep(2)

    finally:
        for c in clients.values():
            try:
                await c.disconnect()
            except Exception:
                pass
        print("[middleware] Deteniendo servidor...")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(middleware_loop())
    except KeyboardInterrupt:
        print("[middleware] Interrumpido por usuario")

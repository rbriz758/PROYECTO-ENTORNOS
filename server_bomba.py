import asyncio
from asyncua import Server, ua


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4843/server_bomba/")

    bomba_obj = await server.nodes.objects.add_object(2, "Sensor_Bomba")
    bomba_var = await bomba_obj.add_variable(2, "Bomba_Status", True)
    await bomba_var.set_writable()

    print("[server_bomba] Iniciando en opc.tcp://0.0.0.0:4843/server_bomba/")
    await server.start()

    try:
        status = True
        while True:
            status = not status
            await bomba_var.write_value(status)
            print(f"[server_bomba] Bomba_Status -> {status}")
            await asyncio.sleep(6)
    except asyncio.CancelledError:
        pass
    finally:
        print("[server_bomba] Deteniendo servidor...")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[server_bomba] Interrumpido por usuario")

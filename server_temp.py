import asyncio
import random
from asyncua import Server, ua


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4841/server_temp/")

    temp_obj = await server.nodes.objects.add_object(2, "Sensor_Temperatura")
    temp_var = await temp_obj.add_variable(2, "Temperatura_Agua", 25.0)
    await temp_var.set_writable()

    print("[server_temp] Iniciando en opc.tcp://0.0.0.0:4841/server_temp/")
    await server.start()

    try:
        while True:
            val = round(random.uniform(20.0, 35.0), 2)
            await temp_var.write_value(val)
            print(f"[server_temp] Temperatura_Agua -> {val}")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
    finally:
        print("[server_temp] Deteniendo servidor...")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[server_temp] Interrumpido por usuario")

import asyncio
import random
from asyncua import Server, ua


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/server_ph/")

    ph_obj = await server.nodes.objects.add_object(2, "Sensor_PH")
    ph_var = await ph_obj.add_variable(2, "PH_Actual", 7.0)
    await ph_var.set_writable()

    print("[server_ph] Iniciando en opc.tcp://0.0.0.0:4840/server_ph/")
    await server.start()

    try:
        while True:
            val = round(random.uniform(6.5, 8.5), 3)
            await ph_var.write_value(val)
            print(f"[server_ph] PH_Actual -> {val}")
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        pass
    finally:
        print("[server_ph] Deteniendo servidor...")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[server_ph] Interrumpido por usuario")

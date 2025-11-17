import asyncio
import random
from asyncua import Server, ua


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4845/server_nivel/")

    nivel_obj = await server.nodes.objects.add_object(2, "Sensor_Nivel")
    nivel_var = await nivel_obj.add_variable(2, "Nivel_Agua_Porcentaje", 95)
    await nivel_var.set_writable()

    print("[server_nivel] Iniciando en opc.tcp://0.0.0.0:4845/server_nivel/")
    await server.start()

    try:
        while True:
            val = random.randint(85, 100)
            await nivel_var.write_value(val)
            print(f"[server_nivel] Nivel_Agua_Porcentaje -> {val}")
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass
    finally:
        print("[server_nivel] Deteniendo servidor...")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[server_nivel] Interrumpido por usuario")

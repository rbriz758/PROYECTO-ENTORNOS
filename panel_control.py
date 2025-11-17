import asyncio
import threading
import queue
import tkinter as tk
from tkinter import ttk
from asyncua import Client, ua


MIDDLEWARE_ENDPOINT = "opc.tcp://127.0.0.1:4844/middleware/"


def start_async_client(q: queue.Queue, stop_event: threading.Event):
    async def client_loop():
        async with Client(MIDDLEWARE_ENDPOINT) as client:
            print("[panel] Conectado al middleware")
            n_estado = client.get_node(ua.NodeId('Estado_Alerta_Global', 2))
            n_dosis = client.get_node(ua.NodeId('Dosis_Recomendada', 2))
            n_ph = client.get_node(ua.NodeId('PH_Procesado', 2))

            while not stop_event.is_set():
                try:
                    estado = await n_estado.read_value()
                    dosis = await n_dosis.read_value()
                    ph = await n_ph.read_value()
                    q.put({'estado': str(estado), 'dosis': float(dosis), 'ph': float(ph)})
                except Exception as e:
                    q.put({'error': str(e)})
                await asyncio.sleep(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client_loop())
    finally:
        loop.close()


class PanelApp:
    def __init__(self, root):
        self.root = root
        root.title("Panel de Control - Middleware Piscina")

        self.q = queue.Queue()
        self.stop_event = threading.Event()

        frm = ttk.Frame(root, padding=10)
        frm.grid()

        ttk.Label(frm, text="PH Procesado:").grid(column=0, row=0, sticky="w")
        self.ph_var = tk.StringVar(value="--")
        self.ph_lbl = ttk.Label(frm, textvariable=self.ph_var, width=20)
        self.ph_lbl.grid(column=1, row=0)

        ttk.Label(frm, text="Dosis Recomendada:").grid(column=0, row=1, sticky="w")
        self.dosis_var = tk.StringVar(value="--")
        self.dosis_lbl = ttk.Label(frm, textvariable=self.dosis_var, width=20)
        self.dosis_lbl.grid(column=1, row=1)

        ttk.Label(frm, text="Estado Alerta Global:").grid(column=0, row=2, sticky="w")
        self.estado_var = tk.StringVar(value="--")
        self.estado_lbl = ttk.Label(frm, textvariable=self.estado_var, width=30)
        self.estado_lbl.grid(column=1, row=2)

        self._start_client_thread()
        self._poll_queue()

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start_client_thread(self):
        self.thread = threading.Thread(target=start_async_client, args=(self.q, self.stop_event), daemon=True)
        self.thread.start()

    def _poll_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                if 'error' in item:
                    self.estado_var.set(f"ERROR: {item['error']}")
                    self.estado_lbl.config(foreground='orange')
                else:
                    self.ph_var.set(f"{item['ph']:.3f}")
                    self.dosis_var.set(f"{item['dosis']:.3f}")
                    self.estado_var.set(item['estado'])
                    if 'ALERTA' in item['estado']:
                        self.estado_lbl.config(foreground='red')
                    else:
                        self.estado_lbl.config(foreground='green')
        except queue.Empty:
            pass
        finally:
            self.root.after(500, self._poll_queue)

    def _on_close(self):
        self.stop_event.set()
        self.root.after(200, self.root.destroy)


def main():
    root = tk.Tk()
    app = PanelApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

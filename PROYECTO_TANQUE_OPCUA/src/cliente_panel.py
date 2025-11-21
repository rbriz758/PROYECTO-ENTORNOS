import tkinter as tk
from tkinter import ttk
import asyncio
import threading
from asyncua import Client

class PanelCliente:
    def __init__(self, root):
        self.root = root
        self.root.title("Panel de Control - Tanque Industrial")
        self.root.geometry("400x500")
        
        # UI Elements
        self.lbl_titulo = tk.Label(root, text="Monitor OPC UA", font=("Arial", 16, "bold"))
        self.lbl_titulo.pack(pady=10)
        
        # Nivel
        self.frame_nivel = tk.LabelFrame(root, text="Nivel del Tanque")
        self.frame_nivel.pack(fill="x", padx=10, pady=5)
        
        self.progress_nivel = ttk.Progressbar(self.frame_nivel, orient="horizontal", length=300, mode="determinate")
        self.progress_nivel.pack(pady=10)
        self.lbl_nivel_val = tk.Label(self.frame_nivel, text="0 %")
        self.lbl_nivel_val.pack()

        # Temperatura
        self.frame_temp = tk.LabelFrame(root, text="Temperatura")
        self.frame_temp.pack(fill="x", padx=10, pady=5)
        self.lbl_temp = tk.Label(self.frame_temp, text="0.0 °C", font=("Arial", 14))
        self.lbl_temp.pack(pady=10)

        # Estado Sistema (Semaforo)
        self.frame_estado = tk.LabelFrame(root, text="Estado del Sistema")
        self.frame_estado.pack(fill="x", padx=10, pady=5)
        self.canvas_semaforo = tk.Canvas(self.frame_estado, width=100, height=100)
        self.canvas_semaforo.pack()
        self.light = self.canvas_semaforo.create_oval(25, 25, 75, 75, fill="gray")
        self.lbl_estado = tk.Label(self.frame_estado, text="Desconectado")
        self.lbl_estado.pack()
        
        # OPC UA Variables
        self.client = None
        self.running = True
        
        # Start OPC UA Loop in separate thread
        self.thread = threading.Thread(target=self.run_async_loop)
        self.thread.start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        self.root.destroy()

    def run_async_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.opcua_client_task())

    async def opcua_client_task(self):
        url = "opc.tcp://localhost:4845/freeopcua/server/"
        self.client = Client(url)
        
        connected = False
        while self.running:
            try:
                if not connected:
                    print(f"Connecting to {url}...")
                    await self.client.connect()
                    connected = True
                    print("Connected!")
                    
                    # Get Nodes
                    uri = "http://examples.freeopcua.github.io"
                    idx = await self.client.get_namespace_index(uri)
                    
                    try:
                        n_estado = self.client.get_node(f"ns={idx};i=5002")
                        n_nivel = self.client.get_node(f"ns={idx};i=5005") # New
                        n_temp = self.client.get_node(f"ns={idx};i=5006") # New
                        
                        # Store nodes to avoid re-fetching
                        self.nodes = (n_estado, n_nivel, n_temp)
                    except Exception as e:
                        print(f"Node Error: {e}")
                        continue

                # Read Values
                if hasattr(self, 'nodes'):
                    n_estado, n_nivel, n_temp = self.nodes
                    
                    try:
                        estado = await n_estado.read_value()
                        nivel = await n_nivel.read_value()
                        temp = await n_temp.read_value()
                        
                        # Update UI (Thread safe)
                        self.root.after(0, self.update_ui, estado, nivel, temp)
                    except Exception as e:
                        print(f"Read Error: {e}")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Connection Error: {e}")
                connected = False
                await asyncio.sleep(2)
        
        if connected:
            await self.client.disconnect()

    def update_ui(self, estado, nivel, temp):
        # Nivel (0-1000 mm)
        pct = (nivel / 1000) * 100
        self.progress_nivel['value'] = pct
        self.lbl_nivel_val.config(text=f"{int(pct)} % ({nivel} mm)")
        
        # Temp
        self.lbl_temp.config(text=f"{temp:.1f} °C")
        
        # Estado
        color = "green"
        text = "OK"
        if estado == 1:
            color = "yellow"
            text = "ALERTA"
        elif estado == 2:
            color = "red"
            text = "CRÍTICO"
            
        self.canvas_semaforo.itemconfig(self.light, fill=color)
        self.lbl_estado.config(text=text)

if __name__ == "__main__":
    root = tk.Tk()
    app = PanelCliente(root)
    root.mainloop()

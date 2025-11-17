# Sistema de Monitoreo y Alerta - Piscina (OPC UA Middleware)

Resumen rápido
- Proyecto académico que simula una arquitectura OPC UA: cuatro servidores fuente (sensores), un middleware que integra y procesa datos, y un panel de control que visualiza el estado.

Estructura de ficheros
- `server_ph.py` — Servidor OPC UA (puerto 4840) publicando `PH_Actual` (ns=2;s=PH_Actual).
- `server_temp.py` — Servidor OPC UA (puerto 4841) publicando `Temperatura_Agua` (ns=2;s=Temperatura_Agua).
- `server_nivel.py` — Servidor OPC UA (puerto 4842) publicando `Nivel_Agua_Porcentaje` (ns=2;s=Nivel_Agua_Porcentaje).
- `server_bomba.py` — Servidor OPC UA (puerto 4843) publicando `Bomba_Status` (ns=2;s=Bomba_Status).
- `middleware_integracion.py` — Cliente a los 4 servidores y servidor propio (puerto 4844). Expone: `Estado_Alerta_Global`, `Dosis_Recomendada`, `PH_Procesado` (ns=2).
- `panel_control.py` — Cliente OPC UA con interfaz Tkinter que muestra `PH_Procesado`, `Dosis_Recomendada` y `Estado_Alerta_Global` en tiempo real.
- `requirements.txt` — Dependencias.

Requisitos
- Python 3.8 o superior.
- Windows: PowerShell (instrucciones abajo).

Instalación de dependencias (PowerShell):
```powershell
python -m pip install -r .\requirements.txt
```

Ejecución (abrir terminales separados para cada servidor y componentes)

1) Arrancar los 4 servidores fuente (uno por terminal):
```powershell
python .\server_ph.py
python .\server_temp.py
python .\server_nivel.py
python .\server_bomba.py
```

2) Arrancar el middleware en otro terminal:
```powershell
python .\middleware_integracion.py
```

3) Abrir el panel de control (otro terminal o desde el explorador):
```powershell
python .\panel_control.py
```

Notas de diseño
- Los servidores fuente actualizan sus variables periódicamente con valores simulados dentro de los rangos solicitados.
- El middleware lee desde los endpoints locales (`127.0.0.1`) y publica los nodos procesados en su propio servidor (endpoint `opc.tcp://0.0.0.0:4844/middleware/`).
- Lógica de alerta en el middleware:
  - Alerta PH si `PH_Actual < 7.2` o `> 7.8`.
  - Alerta Nivel si `Nivel_Agua_Porcentaje < 90`.
  - Dosis recomendada (cuando pH < 7.2): `100 * (7.2 - PH_Actual)`.

Problemas posibles y soluciones rápidas
- Firewall: permite puertos 4840-4844 o ejecuta localmente con `127.0.0.1`.
- Si la GUI muestra errores de conexión, espera que el middleware esté arrancado y presiona cerrar/abrir.

¿Quieres que añada scripts PowerShell que lancen todos los servidores automáticamente en pestañas (o un `docker-compose` equivalente)?

**Esquema Visual (Lógica del Proyecto)**

Diagrama de arquitectura (ASCII):

```
               +-----------------+         Reads           +----------------+
               |  Server PH      |  -------------------->  |                |
               |  (opc.tcp:4840) |                         |                |
               +-----------------+                         |                |
                                                    +----->|                |
               +-----------------+         Reads     |      |  Middleware    |
               |  Server TEMP    |  -------------------->  |  (opc.tcp:4844) |  Exposes:
               |  (opc.tcp:4841) |                         |  - Estado_Alerta|
               +-----------------+                         |  - Dosis_Recom. |
                                                    |      |  - PH_Procesado |
               +-----------------+         Reads     |      |                |
               |  Server NIVEL   |  -------------------->  |                |
               |  (opc.tcp:4845) |                         |                |
               +-----------------+                         +----------------+
                                                    |
               +-----------------+         Reads     |
               |  Server BOMBA   |  -------------------->
               |  (opc.tcp:4843) |
               +-----------------+

                              |
                              |  Client connects to middleware
                              v
                       +----------------+
                       | Panel de       |
                       | Control (GUI)  |
                       | (lee PH, Dosis,|
                       | Estado)        |
                       +----------------+

```

Flujo lógico y reglas principales:
- Los cuatro servidores fuente publican variables en `ns=2` con BrowseNames:
  - `PH_Actual` (float), `Temperatura_Agua` (float), `Nivel_Agua_Porcentaje` (int), `Bomba_Status` (bool).
- El `middleware_integracion.py` actúa como cliente de cada servidor y agrupa/expone los datos en su propio servidor.
- Reglas de alerta (implementadas en el middleware):
  - PH Bajo: `PH_Actual < 7.2` → añadir alerta `PH Bajo` y calcular `Dosis_Recomendada = 100 * (7.2 - PH_Actual)`.
  - PH Alto: `PH_Actual > 7.8` → añadir alerta `PH Alto` (no se calcula dosis para bajar el pH en esta versión).
  - Nivel Bajo: `Nivel_Agua_Porcentaje < 90` → añadir alerta `Nivel Bajo`.
  - Las alertas se concatenan si hay múltiples condiciones: ejemplo `ALERTA: PH Alto | Nivel Bajo`.
- El Panel de Control se conecta al endpoint del middleware y muestra en tiempo real `PH_Procesado`, `Dosis_Recomendada` y `Estado_Alerta_Global`. Las alertas se resaltan en rojo.

Representación Mermaid (opcional):

```mermaid
graph TD
  PH[Server PH\n(opc.tcp:4840)] --> M[Middleware\n(opc.tcp:4844)]
  TEMP[Server TEMP\n(opc.tcp:4841)] --> M
  NIVEL[Server NIVEL\n(opc.tcp:4845)] --> M
  BOMBA[Server BOMBA\n(opc.tcp:4843)] --> M
  M --> Panel[Panel de Control\n(Tkinter GUI)]

  subgraph Rules[Reglas en Middleware]
    direction TB
    PHLow[PH < 7.2 -> Dosis = 100*(7.2 - PH)]
    PHHigh[PH > 7.8 -> Alerta PH Alto]
    NivelLow[Nivel < 90 -> Alerta Nivel Bajo]
  end

  M --- Rules
```

Nota: GitHub renderiza Mermaid en algunos entornos; si no se visualiza, usa el diagrama ASCII anterior.

# 🏭 Sistema de Control de Tanque Industrial - Digital Twin

## 📋 Descripción

**Sistema de Control Digital Twin** con arquitectura de **"Middleware Maestro"** que implementa un motor de física centralizado para garantizar coherencia total de datos y realismo físico.

### ✨ Características Principales

- 🎯 **Motor de Física Centralizado**: Todos los cálculos están centralizados en el middleware
- 🔄 **Arquitectura Maestro-Esclavo**: El middleware escribe los valores calculados en los servidores
- 📊 **Panel SCADA Web**: Interfaz dark industrial con visualización en tiempo real
- 🔧 **Modo Ingeniero**: Toggle para mostrar/ocultar datos técnicos detallados
- ⚠️ **Detección de Fugas**: Algoritmo inteligente que detecta anomalías en el balance de masas
- 📈 **Gráficos en Tiempo Real**: Visualización de caudales y nivel con Chart.js

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    MIDDLEWARE MAESTRO                        │
│              (Motor de Física - Puerto 4845)                 │
│                                                              │
│  • Lee inputs (RPM, Válvula, SetPoint)                      │
│  • Calcula física (caudales, nivel, temp)                   │
│  • Escribe resultados en servidores esclavos                │
│  • Detecta fugas y anomalías                                │
└──────────────┬──────────────┬──────────────┬────────────────┘
               │              │              │
       ┌───────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────────┐
       │  Servidor   │ │ Servidor  │ │ Servidor  │ │Servidor │
       │   Nivel     │ │   Temp    │ │  Entrada  │ │ Salida  │
       │ (P: 4840)   │ │ (P: 4841) │ │ (P: 4842) │ │(P: 4843)│
       └─────────────┘ └───────────┘ └───────────┘ └─────────┘
                                │
                        ┌───────▼────────┐
                        │   Web SCADA    │
                        │  (P: 5000)     │
                        │  Flask + JS    │
                        └────────────────┘
```

---

## 📂 Estructura de Archivos

```
PROYECTO_TANQUE_OPCUA/
│
├── modelos_xml/                    # Definiciones estáticas
│   ├── modelo_nivel.xml            # Nivel, Volumen, Estado
│   ├── modelo_temp.xml             # Temperatura, SetPoint, Calentador
│   ├── modelo_entrada.xml          # Caudal_In, RPM, Amperios
│   ├── modelo_salida.xml           # Caudal_Out, Posición, Totalizador
│   └── modelo_middleware.xml       # Estado, Alerta, Tiempo
│
├── src/                            # Código Python
│   ├── server_nivel.py             # Servidor Nivel (Puerto 4840)
│   ├── server_temp.py              # Servidor Temperatura (4841)
│   ├── server_entrada.py           # Servidor Entrada (4842)
│   ├── server_salida.py            # Servidor Salida (4843)
│   ├── middleware.py               # MAESTRO - Motor Física (4845)
│   ├── web_app.py                  # Flask SCADA (5000)
│   │
│   ├── static/                     # Frontend
│   │   ├── style.css               # Dark Industrial CSS
│   │   └── script.js               # Lógica UI + Gráficos
│   │
│   └── templates/
│       └── index.html              # Dashboard SCADA
│
├── requirements.txt                # Dependencias Python
├── run_all.bat                     # Script de inicio (Windows)
└── README.md                       # Este archivo
```

---

## 🔧 Instalación

### 1. **Requisitos Previos**
- Python 3.8 o superior
- pip (gestor de paquetes Python)

### 2. **Instalar Dependencias**

```bash
pip install -r requirements.txt
```

Las dependencias son:
- `flask==3.0.0` - Framework web
- `opcua==0.98.13` - Biblioteca OPC UA

---

## 🚀 Ejecución

### Opción 1: Script Automático (Windows)

```bash
run_all.bat
```

Este script iniciará automáticamente:
1. Servidor Nivel (4840)
2. Servidor Temperatura (4841)
3. Servidor Entrada (4842)
4. Servidor Salida (4843)
5. Middleware - Motor de Física (4845)
6. Web SCADA (5000)

### Opción 2: Manual

Abrir **6 terminales diferentes** y ejecutar en orden:

```bash
# Terminal 1
cd src
python server_nivel.py

# Terminal 2
python server_temp.py

# Terminal 3
python server_entrada.py

# Terminal 4
python server_salida.py

# Terminal 5 (esperar 3 segundos)
python middleware.py

# Terminal 6 (esperar 3 segundos más)
python web_app.py
```

### 3. **Acceder al Panel SCADA**

Abrir navegador en: **http://localhost:5000**

---

## 🧪 Física Implementada

### 1. **Bomba de Entrada**
```python
Caudal_In = RPM_Bomba * 0.05  # L/min
Amperios = 2.0 + (Caudal_In * 0.15)
```

### 2. **Válvula de Salida (Ley de Torricelli Simplificada)**
```python
Factor_Presion = sqrt(Nivel_mm / 3000)
Caudal_Out = (Posicion_Valvula / 100) * 50.0 * Factor_Presion
```

### 3. **Balance de Masas (Tanque)**
```python
Delta_Nivel = (Caudal_In - Caudal_Out) * 0.5
Nivel_Nuevo = Nivel_Actual + Delta_Nivel
# CLAMPING: 0 <= Nivel_Nuevo <= 3000
```

### 4. **Termodinámica con Histéresis**
```python
if temp < (setpoint - 2): calentador = ON
if temp > (setpoint + 2): calentador = OFF

if calentador_ON: temp += 0.08
else: temp -= 0.01
```

### 5. **Detección de Fugas**
```python
Alerta_Fuga = True SI:
  - (Caudal_In > Caudal_Out + 10) Y
  - (Nivel NO sube) Y
  - (Nivel < 2990)
```

### 6. **Tiempo de Llenado**
```python
if Nivel >= 3000: tiempo = 0  # Lleno
elif Caudal_In <= Caudal_Out: tiempo = 9999  # Vaciando
else: tiempo = (10000 - Volumen) / (Caudal_In - Caudal_Out)
```

---

## 🎮 Uso del Panel SCADA

### Controles Principales

1. **RPM Bomba** (0 - 3000 RPM)
   - Controla el caudal de entrada
   - RPM más alto = más caudal
   
2. **Apertura Válvula** (0 - 100%)
   - Controla el caudal de salida
   - Depende también del nivel (presión)
   
3. **Setpoint Temperatura** (15 - 100°C)
   - Temperatura objetivo
   - Calentador se activa/desactiva automáticamente

### Modo Ingeniero

Active el toggle **"MODO INGENIERO"** para ver:
- **Entrada**: Caudal calculado, Amperios consumidos
- **Salida**: Caudal calculado, Totalizador (m³ acumulados)

---

## 📊 KPIs y Alertas

### Indicadores Principales
- **Nivel**: 0 - 3000 mm
- **Volumen**: 0 - 10,000 L
- **Temperatura**: Con indicador de calentador ON/OFF
- **Tiempo de Llenado**: Estimación dinámica

### Estados del Sistema
- ✅ **OPERACIÓN NORMAL**: Todo funciona correctamente
- 🟠 **TANQUE LLENO**: Nivel = 3000 mm
- ⚪ **TANQUE VACÍO**: Nivel = 0 mm
- 🔴 **ALERTA: FUGA DETECTADA**: Anomalía en balance de masas

---

## 🎨 Diseño UI

**Tema**: Dark Industrial

**Paleta de Colores**:
- Fondo: `#0a0e1a` (Negro profundo)
- Cards: `#1a1f2e` (Gris oscuro)
- Acento primario: `#00d9ff` (Cyan brillante)
- Alertas: `#ff6b35` (Naranja), `#ff3366` (Rojo)
- Éxito: `#00ff88` (Verde neón)

**Fuentes**:
- Display: `Orbitron` (Títulos y números)
- Cuerpo: `Rajdhani` (Textos)

**Efectos**:
- Animaciones de ola en el tanque
- Glow effects en elementos activos
- Transiciones suaves
- Responsive design

---

## 🔍 Puertos Utilizados

| Componente | Puerto | Protocolo |
|-----------|--------|-----------|
| Servidor Nivel | 4840 | OPC UA |
| Servidor Temperatura | 4841 | OPC UA |
| Servidor Entrada | 4842 | OPC UA |
| Servidor Salida | 4843 | OPC UA |
| Middleware | 4845 | OPC UA |
| Web SCADA | 5000 | HTTP |

---

## 🛠️ Troubleshooting

### Error: "No se pudo conectar a los servidores"
**Solución**: Asegúrese de iniciar los 4 servidores antes del middleware

### Error: "Address already in use"
**Solución**: Cierre todas las instancias previas de los scripts

### La UI no actualiza
**Solución**: Verifique que el middleware esté ejecutándose y calculando física

### Datos inconsistentes
**Solución**: Reinicie todo el sistema con `run_all.bat`

---

## 📚 Conceptos Técnicos

### ¿Qué es un Digital Twin?
Un gemelo digital es una representación virtual de un sistema físico que se actualiza en tiempo real y permite simulación, monitoreo y control.

### Arquitectura Maestro-Esclavo
- **Maestro** (Middleware): Toma decisiones, calcula física
- **Esclavos** (Servidores): Solo exponen variables, no calculan

### Ventajas de esta Arquitectura
✅ **Coherencia garantizada**: Imposible tener contradicciones  
✅ **Física realista**: Todas las variables están vinculadas  
✅ **Mantenimiento simple**: Lógica centralizada  
✅ **Escalable**: Fácil agregar nuevos sensores  

---

## 👨‍💻 Desarrollo

### Agregar un Nuevo Sensor

1. Crear `modelo_nuevo.xml` en `modelos_xml/`
2. Crear `server_nuevo.py` con nodos `writable`
3. Modificar `middleware.py`:
   - Conectar al nuevo servidor
   - Agregar cálculos de física
   - Escribir resultados
4. Actualizar `web_app.py` para mostrar datos

### Modificar Ecuaciones de Física

Editar la clase `PhysicsEngine` en `middleware.py`

---

## 📄 Licencia

Este proyecto es de código abierto para fines educativos.

---

## 🙏 Créditos

**Arquitectura**: Estrategia del Middleware Maestro  
**Framework OPC UA**: FreeOpcUa (Python)  
**UI Framework**: Flask + Chart.js  
**Diseño**: Dark Industrial Theme  

---

## 📞 Soporte

Para problemas o preguntas:
1. Revise la sección de Troubleshooting
2. Verifique los logs en las consolas de cada servidor
3. Asegúrese de que todos los puertos estén disponibles

---

**¡Disfrute de su Digital Twin con física realista! 🚀**

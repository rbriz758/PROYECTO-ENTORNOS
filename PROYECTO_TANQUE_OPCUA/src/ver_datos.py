import os
import sqlite3
import time

def leer_datos():
    # Ruta de la base de datos (un nivel arriba de src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "tank_data.db")
    
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos en: {db_path}")
        print("Asegúrate de haber ejecutado el middleware al menos una vez.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener los últimos 20 registros
        cursor.execute('''
            SELECT id, timestamp, nivel, temperatura, caudal_entrada, caudal_salida, estado, calentador, estado_temp
            FROM measurements
            ORDER BY id DESC
            LIMIT 20
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("📭 La base de datos está vacía.")
            return

        print("\n📊 ÚLTIMOS 20 REGISTROS DEL TANQUE")
        print("=" * 145)
        # Encabezados con ancho fijo
        print(f"{'ID':<5} | {'Hora':<20} | {'Nivel (mm)':<12} | {'Temp (°C)':<10} | {'In (L/min)':<12} | {'Out (L/min)':<12} | {'Estado':<20} | {'Calentador':<10} | {'Estado Temp':<15}")
        print("-" * 145)
        
        for row in rows:
            id_val = str(row[0])
            hora = row[1].split('.')[0]
            nivel = f"{row[2]:.1f}"
            temp = f"{row[3]:.1f}"
            in_flow = f"{row[4]:.1f}"
            out_flow = f"{row[5]:.1f}"
            estado = row[6]
            # Manejar valores nulos por si acaso (aunque no debería haber)
            calentador = "ON" if row[7] else "OFF"
            estado_temp = row[8] if row[8] else "N/A"
            
            print(f"{id_val:<5} | {hora:<20} | {nivel:<12} | {temp:<10} | {in_flow:<12} | {out_flow:<12} | {estado:<20} | {calentador:<10} | {estado_temp:<15}")
            
        print("=" * 145)
        print(f"Total registros mostrados: {len(rows)}")

    except Exception as e:
        print(f"❌ Error leyendo la base de datos: {e}")

if __name__ == "__main__":
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        leer_datos()
        print("\n🔄 Actualizando en 5 segundos... (Ctrl+C para salir)")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            break

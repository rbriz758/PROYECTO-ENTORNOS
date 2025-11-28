import sqlite3
import os
from datetime import datetime
import logging

# Configurar logging
logger = logging.getLogger("DATABASE")

class DatabaseManager:
    def __init__(self, db_name="tank_data.db"):
        # La base de datos se creará en la carpeta raíz del proyecto (un nivel arriba de src)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_name)
        self.init_db()

    def init_db(self):
        """Inicializa la base de datos y crea la tabla si no existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Para simplificar en desarrollo, borramos la tabla si existe para recrearla con nuevas columnas
            # En producción esto sería una migración
            cursor.execute('DROP TABLE IF EXISTS measurements')
            
            cursor.execute('''
                CREATE TABLE measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    nivel REAL,
                    temperatura REAL,
                    caudal_entrada REAL,
                    caudal_salida REAL,
                    estado TEXT,
                    calentador BOOLEAN,
                    estado_temp TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Base de datos inicializada en: {self.db_path}")
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")

    def insert_data(self, nivel, temperatura, caudal_in, caudal_out, estado, calentador, estado_temp):
        """Inserta una nueva medición"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO measurements (nivel, temperatura, caudal_entrada, caudal_salida, estado, calentador, estado_temp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nivel, temperatura, caudal_in, caudal_out, estado, calentador, estado_temp))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error insertando datos: {e}")

    def get_recent_data(self, limit=50):
        """Obtiene los últimos registros"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, nivel, temperatura, caudal_entrada, caudal_salida, estado, calentador, estado_temp
                FROM measurements
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"Error leyendo datos: {e}")
            return []

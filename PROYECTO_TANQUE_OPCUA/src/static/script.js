// ===== CONFIGURACIÓN GLOBAL =====
let datosHistorico = {
    timestamps: [],
    caudal_in: [],
    caudal_out: [],
    nivel: []
};

const MAX_HISTORY = 50;  // Últimos 50 puntos de datos

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function () {
    inicializarControles();
    inicializarGraficos();
    inicializarModoIngeniero();
    actualizarDatos();

    // Actualizar timestamp
    setInterval(actualizarTimestamp, 1000);
});

// ===== MODO INGENIERO =====
function inicializarModoIngeniero() {
    const toggle = document.getElementById('modoIngeniero');
    const elementosIngenieria = document.querySelectorAll('.ingenieria');

    toggle.addEventListener('change', function () {
        elementosIngenieria.forEach(el => {
            if (this.checked) {
                el.style.display = 'flex';
            } else {
                el.style.display = 'none';
            }
        });
    });
}

// ===== CONTROLES =====
function inicializarControles() {
    // Slider RPM
    const rpmSlider = document.getElementById('rpmSlider');
    const rpmDisplay = document.getElementById('rpmDisplay');

    rpmSlider.addEventListener('input', function () {
        rpmDisplay.textContent = this.value;
    });

    rpmSlider.addEventListener('change', function () {
        enviarControl('/api/control/rpm', { rpm: parseFloat(this.value) });
    });

    // Slider Válvula
    const valvulaSlider = document.getElementById('valvulaSlider');
    const valvulaDisplay = document.getElementById('valvulaDisplay');

    valvulaSlider.addEventListener('input', function () {
        valvulaDisplay.textContent = this.value;
    });

    valvulaSlider.addEventListener('change', function () {
        enviarControl('/api/control/valvula', { posicion: parseFloat(this.value) });
    });

    // Slider Setpoint
    const setpointSlider = document.getElementById('setpointSlider');
    const setpointDisplay = document.getElementById('setpointDisplay');

    setpointSlider.addEventListener('input', function () {
        setpointDisplay.textContent = this.value;
    });

    setpointSlider.addEventListener('change', function () {
        enviarControl('/api/control/setpoint', { setpoint: parseFloat(this.value) });
    });
}

async function enviarControl(endpoint, data) {
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            console.error('Error en control:', await response.text());
        }
    } catch (error) {
        console.error('Error enviando control:', error);
    }
}

// ===== ACTUALIZACIÓN DE DATOS =====
async function actualizarDatos() {
    try {
        const response = await fetch('/api/datos');
        const datos = await response.json();

        // Actualizar UI
        actualizarTanque(datos);
        actualizarTemperatura(datos);
        actualizarCaudales(datos);
        actualizarEstado(datos);
        actualizarHistorico(datos);

    } catch (error) {
        console.error('Error obteniendo datos:', error);
    }

    // Actualizar cada segundo
    setTimeout(actualizarDatos, 1000);
}

function actualizarTanque(datos) {
    const nivel_mm = datos.nivel_mm || 0;
    const volumen_l = datos.volumen_l || 0;
    const capacidad = (nivel_mm / 3000) * 100;

    // Actualizar visualización del tanque 3D
    document.getElementById('water-level-3d').style.height = capacidad + '%';

    // Actualizar displays
    document.getElementById('nivelDisplay').textContent = nivel_mm.toFixed(1) + ' mm';
    document.getElementById('volumenDisplay').textContent = volumen_l.toFixed(1) + ' L';
    document.getElementById('capacidadDisplay').textContent = capacidad.toFixed(1) + '%';
}

function actualizarTemperatura(datos) {
    const temp = datos.temperatura || 0;
    const calentador = datos.calentador_on || false;

    document.getElementById('tempActualDisplay').textContent = temp.toFixed(1) + ' °C';

    const statusEl = document.getElementById('calentadorStatus');
    if (calentador) {
        statusEl.textContent = 'ON';
        statusEl.classList.remove('off');
        statusEl.classList.add('on');
    } else {
        statusEl.textContent = 'OFF';
        statusEl.classList.remove('on');
        statusEl.classList.add('off');
    }
}

function actualizarCaudales(datos) {
    // Datos de ingeniería
    document.getElementById('caudalInDisplay').textContent = (datos.caudal_in || 0).toFixed(1) + ' L/min';
    document.getElementById('caudalOutDisplay').textContent = (datos.caudal_out || 0).toFixed(1) + ' L/min';
    document.getElementById('amperiosDisplay').textContent = (datos.amperios || 0).toFixed(2) + ' A';
    document.getElementById('totalizadorDisplay').textContent = (datos.totalizador || 0).toFixed(3) + ' m³';

    // Sensor status
    const sensorStatusEl = document.getElementById('val-sensor-status');
    const estado_sensor = datos.estado_sensor !== undefined ? datos.estado_sensor : true;

    if (estado_sensor === true || estado_sensor === 'true' || estado_sensor === 1) {
        sensorStatusEl.textContent = 'ONLINE';
        sensorStatusEl.classList.remove('fault');
        sensorStatusEl.classList.add('online');
    } else {
        sensorStatusEl.textContent = 'FAULT';
        sensorStatusEl.classList.remove('online');
        sensorStatusEl.classList.add('fault');
    }
}

function actualizarEstado(datos) {
    const estado = datos.estado_sistema || 'DESCONOCIDO';
    const alerta_fuga = datos.alerta_fuga || false;
    const tiempo_llenado = datos.tiempo_llenado || 0;

    // Estado del sistema
    const estadoEl = document.getElementById('estadoSistema');
    estadoEl.textContent = estado;

    // Cambiar color según estado
    estadoEl.style.borderColor = alerta_fuga ? 'var(--red-danger)' :
        estado.includes('LLENO') ? 'var(--orange-alert)' :
            estado.includes('VACÍO') ? 'var(--text-dim)' :
                'var(--green-success)';

    estadoEl.style.color = alerta_fuga ? 'var(--red-danger)' :
        estado.includes('LLENO') ? 'var(--orange-alert)' :
            estado.includes('VACÍO') ? 'var(--text-dim)' :
                'var(--green-success)';

    // Alerta de fuga
    const alertaEl = document.getElementById('alertaFuga');
    alertaEl.style.display = alerta_fuga ? 'block' : 'none';

    // Tiempo de llenado
    const tiempoEl = document.getElementById('tiempoLlenado');
    if (tiempo_llenado >= 9999) {
        tiempoEl.textContent = '∞ (vaciando)';
        tiempoEl.style.color = 'var(--orange-alert)';
    } else if (tiempo_llenado === 0) {
        tiempoEl.textContent = 'LLENO';
        tiempoEl.style.color = 'var(--green-success)';
    } else {
        tiempoEl.textContent = tiempo_llenado.toFixed(1) + ' min';
        tiempoEl.style.color = 'var(--cyan-glow)';
    }
}

function actualizarHistorico(datos) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();

    // Agregar nuevos datos
    datosHistorico.timestamps.push(timeStr);
    datosHistorico.caudal_in.push(datos.caudal_in || 0);
    datosHistorico.caudal_out.push(datos.caudal_out || 0);
    datosHistorico.nivel.push(datos.nivel_mm || 0);

    // Mantener solo los últimos MAX_HISTORY puntos
    if (datosHistorico.timestamps.length > MAX_HISTORY) {
        datosHistorico.timestamps.shift();
        datosHistorico.caudal_in.shift();
        datosHistorico.caudal_out.shift();
        datosHistorico.nivel.shift();
    }

    // Actualizar gráficos
    if (window.chartCaudales) {
        window.chartCaudales.data.labels = datosHistorico.timestamps;
        window.chartCaudales.data.datasets[0].data = datosHistorico.caudal_in;
        window.chartCaudales.data.datasets[1].data = datosHistorico.caudal_out;
        window.chartCaudales.update('none');
    }

    if (window.chartNivel) {
        window.chartNivel.data.labels = datosHistorico.timestamps;
        window.chartNivel.data.datasets[0].data = datosHistorico.nivel;
        window.chartNivel.update('none');
    }
}

function actualizarTimestamp() {
    const now = new Date();
    document.getElementById('timestamp').textContent =
        now.toLocaleDateString() + ' ' + now.toLocaleTimeString();
}

// ===== GRÁFICOS CON CHART.JS =====
function inicializarGraficos() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
            legend: {
                labels: {
                    color: '#8b95a5',
                    font: {
                        family: 'Rajdhani'
                    }
                }
            }
        },
        scales: {
            x: {
                ticks: {
                    color: '#5a6270',
                    maxTicksLimit: 10
                },
                grid: {
                    color: '#2a3444'
                }
            },
            y: {
                ticks: {
                    color: '#5a6270'
                },
                grid: {
                    color: '#2a3444'
                }
            }
        }
    };

    // Gráfico de Caudales
    const ctxCaudales = document.getElementById('chartCaudales').getContext('2d');
    window.chartCaudales = new Chart(ctxCaudales, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Caudal Entrada (L/min)',
                    data: [],
                    borderColor: '#00d9ff',
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.3
                },
                {
                    label: 'Caudal Salida (L/min)',
                    data: [],
                    borderColor: '#ff6b35',
                    backgroundColor: 'rgba(255, 107, 53, 0.1)',
                    borderWidth: 2,
                    tension: 0.3
                }
            ]
        },
        options: chartOptions
    });

    // Gráfico de Nivel
    const ctxNivel = document.getElementById('chartNivel').getContext('2d');
    window.chartNivel = new Chart(ctxNivel, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Nivel (mm)',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                y: {
                    ...chartOptions.scales.y,
                    min: 0,
                    max: 3000
                }
            }
        }
    });
}

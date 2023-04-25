# ------------------------------------------------------------------------------
## Carga de módulos M. Padron y J. Fornet
# ------------------------------------------------------------------------------
import json
from machine import Pin, PWM, ADC, SPI, Timer
import math
import cmath
import time
import sys
import uselect
# ------------------------------------------------------------------------------
SOURCE = 'Procesamiento de Señales'
# ------------------------------------------------------------------------------
# Configuración de entrada/salida 
# ------------------------------------------------------------------------------
led = PWM(Pin(14))
signal_in = ADC(26)
signal_out = PWM(Pin(14))
signal_out.freq(10_000)
buffer=[0,0,0,0,0,0,0,0,0,0]

# ------------------------------------------------------------------------------
# ADC
# ------------------------------------------------------------------------------
def readInput():
    return signal_in.read_u16()
# ------------------------------------------------------------------------------
# DAC
# ------------------------------------------------------------------------------
def writeOutput(value: int):
    '''Write output to DAC '''
    signal_out.duty_u16(value)
# ------------------------------------------------------------------------------
# Comunicación serie
# ------------------------------------------------------------------------------
def parse_command(cmd):
    global params
    try:
        command = json.loads(cmd)
        # Escribe aquí el código para interpretar las órdenes recibidas
    except Exception as e:
        print('{"result":"unknown or malformed command"}')
        
def FastFT(buffer):
# Creamos Wk*n con N/2 (matriz 5x5 con exp(-j*2*pi*k*n/5) variando k en las filas y n en las columnas o viceversa) k y n varia de
# 0  a 4 (0-((N/2)-1)).
    Wkn = [[0 for n in range(5)] for k in range(5)] # Matriz de ceros (5x5)
    for n in range (5):
        for k in range (5):
            Wkn[n][k]=cmath.exp(-1j*2*cmath.pi*k*n/5)
# Necesitamos una matriz Wk con N (matriz 1x5 ó 5x1 con exp(-j*2*pi*k/10) variando k de 0-4, para ello podemos usar la matriz anterios
# fijando n a 1, y sumando a cada elemento de esa fila o columna por exp(1/2). 
    Wk = [0 for n in range(5)]  # Matriz de ceros (5x1)
    for k in range (5):
        Wk[k]=Wkn[1][k]*cmath.exp(0.5)
# Generamos las funciones f(n)=x(2*n) y g(n)=x(2*n+1).
    
    fn=[0 for n in range(5)]
    gn=[0 for n in range(5)]
    for i in range (10):
        if i % 2 == 0:
            n=int(i/2)
            fn[n]=buffer[i]         
        else:
            n=int((i-1)/2)
            gn[n]=buffer[i]

# Calculamos la DFT de de f(n) (F(k)) usando Wk*n con N/2 haciendo el sumatorio desde 0 hasta 4 de f(n)*Wk*n, siendo K
#k la variable independiente de la DFT.

    Fk=[0 for n in range(5)]
    for k in range (5):
        for n in range (5):
            Fk[k]=fn[k]*Wkn[n][k]+Fk[k]

# Repetimos el proceso anterior para calcular G(k) a partir de g(n).

    Gk=[0 for n in range(5)]
    for k in range (5):
        for n in range (5):
            Gk[k]=gn[k]*Wkn[n][k]+Gk[k]

# Obtenmos la DFT X[k] a partir de de las F(k) y G(k) sabiendo que para k menor a 5 la formula es
#X(k)=F(k) + Wk*G(k) y para k mayor a 5 X(k)=F(k-5)-W(k-5)*G(k-5).

    Xk=[0 for n in range(10)]
    for k in range (5):
        Xk[k]=Fk[k]+Wk[k]*Gk[k]
    for k in range (5):
        Xk[k+5]=Fk[k]-Wk[k]*Gk[k]
        
    return(Xk) 
# ------------------------------------------------------------------------------
# Bucle principal
# ------------------------------------------------------------------------------
#   1. Espera hasta el siguiente periodo de muestreo (PERIOD_US).
#   2. Genera la siguiente muestra de la señal y la envía a la salida (PWM).
#   3. Lee el valor de la entrada analógica (ADC).
# ------------------------------------------------------------------------------
def waitNextPeriod(previous):
    lapsed = time.ticks_us() - previous
    offset = -60
    remaining = PERIOD_US - lapsed + offset
    if 0 < lapsed <= PERIOD_US:
        time.sleep_us(remaining)
    return time.ticks_us()

def loop():
    state = []
    tLast = time.ticks_us()
    t0 = tLast
    spoll = uselect.poll()
    spoll.register(sys.stdin, uselect.POLLIN)
    while True:
        data = []
        for i in range(BUFFER_SIZE):
            try:
              t = waitNextPeriod(tLast)
              u = signal((t-t0)*1e-6)
              y = readInput()
              led.duty_u16(u);
              buffer[i]=y
              Yw = FastFT(buffer)
              for j in range (10):
                  yywn = abs(Yw[j])
                  print(f'{u} {y} {yywn}')
              writeOutput(int(u))
            except ValueError:
              pass
        data.append([(t-t0)*1e-6, u, y])
        tLast = t
        if spoll.poll(0):
            cmd = str(sys.stdin.readline())
            parse_command(cmd)
       
        
        
# ------------------------------------------------------------------------------
# INSTRUCCIONES
# ------------------------------------------------------------------------------
PERIOD_US = 1000 # Periodo de muestreo en microsegundos
BUFFER_SIZE = 10 # Muestras en el buffer



def signal(t):
  # Pon aquí el código necesario para generar tu señal.
  freq = 0.01
  signal_out = math.sin( 2*math.pi*freq * t) * 65_025
  return int(math.fabs(signal_out))

# ------------------------------------------------------------------------------
# Comienza la ejecución
# ------------------------------------------------------------------------------
loop()


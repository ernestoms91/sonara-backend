#!/bin/bash

# Busca el entorno virtual en diferentes ubicaciones comunes
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Entorno virtual activado: venv"
elif [ -f "env/bin/activate" ]; then
    source env/bin/activate
    echo "Entorno virtual activado: env"
else
    echo " No se encontró el entorno virtual (venv o env)"
    echo " Para crear uno nuevo: python3 -m venv venv"
fi
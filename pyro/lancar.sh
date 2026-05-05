#!/bin/bash
# lancar.sh — Lança o NameServer + 4 nós Raft em janelas do Terminator
#
# Como usar:
#   chmod +x lancar.sh
#   ./lancar.sh

DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$DIR/processo.py"
VENV="$DIR/venv/bin/activate"  # <-- ajuste aqui se necessário

# Verifica se a venv existe
if [ ! -f "$VENV" ]; then
    echo "ERRO: venv não encontrada em $VENV"
    echo "Ajuste a variável VENV no topo do script."
    exit 1
fi

# Mata processos anteriores
echo "Encerrando processos anteriores (se houver)..."
pkill -f "Pyro5.nameserver" 2>/dev/null
pkill -f "processo.py" 2>/dev/null
sleep 1

# Lança o NameServer
terminator -T "NameServer" -e "bash -c 'source $VENV && echo === NAMESERVER === && python3 -m Pyro5.nameserver; bash'" &

sleep 3  # espera o NameServer subir

# Lança os 4 nós
terminator -T "no1" -e "bash -c 'source $VENV && echo === NÓ 1 === && python3 $SCRIPT no1 5001; bash'" &
sleep 0.3
terminator -T "no2" -e "bash -c 'source $VENV && echo === NÓ 2 === && python3 $SCRIPT no2 5002; bash'" &
sleep 0.3
terminator -T "no3" -e "bash -c 'source $VENV && echo === NÓ 3 === && python3 $SCRIPT no3 5003; bash'" &
sleep 0.3
terminator -T "no4" -e "bash -c 'source $VENV && echo === NÓ 4 === && python3 $SCRIPT no4 5004; bash'" &

echo "Tudo lançado! Organize as janelas como preferir no Terminator."
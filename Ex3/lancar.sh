#!/bin/bash

SESSION="raft"
DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$DIR/processo.py"
CLIENTE="$DIR/cliente.py"
VENV="$DIR/venv/bin/activate"

# Mata a sessão anterior se ela existir
tmux kill-session -t $SESSION 2>/dev/null

# 1. Cria a sessão e lança o NameServer no primeiro painel (topo esquerda)
tmux new-session -d -s $SESSION "source $VENV && python3 -m Pyro5.nameserver; bash"

# 2. Divide horizontalmente para o Nó 1
tmux split-window -h "source $VENV && python3 $SCRIPT no1 5001; bash"

# 3. Divide o painel do NameServer verticalmente para o Nó 2
tmux select-pane -t 0
tmux split-window -v "source $VENV && python3 $SCRIPT no2 5002; bash"

# 4. Divide o painel do Nó 1 verticalmente para o Nó 3
tmux select-pane -t 2
tmux split-window -v "source $VENV && python3 $SCRIPT no3 5003; bash"

# 5. Adiciona o Nó 4 dividindo o espaço do Nó 2
tmux select-pane -t 1
tmux split-window -v "source $VENV && python3 $SCRIPT no4 5004; bash"

tmux select-pane -t 1
tmux split-window -v "sleep 5 && source $VENV && python3 $CLIENTE;bash"

# Organiza tudo em grade e entra na janela
tmux select-layout tiled
tmux attach-session -t $SESSION
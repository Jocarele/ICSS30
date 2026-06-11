import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pathlib import Path 
from terminal import opcoes
from threading import Thread
# FLASK
from flask import Flask, jsonify, request
from flask_cors import CORS
import queue
from flask import Response
import requests

'''
Responsavel por:
    -Export a API REST consumida pelo frontend
    -transformar ações dos usuários em eventos publicados no RabbitMQ
    -consumir eventos dos demais microserviços
    -mantes conexões SSE com os clientes
    -encaminhar notificações SSE apenas para os clientes interessados

Precisa disponibilizar endpoint REST para(ROTAS):
    -cadastrar promoções na loja
    -listar promoções publicadas
    -votar em promoção
    -registrar interesse em categoria
    -cancelar interesse em categoria

SSE Notificiações em tempo real
    -Hot deals
    -categorias seguidas pelo usuario

RabbitMQ
    Publica evento:
        -promocao.recebida
        -promocao.voto
    Consome evento:
        -promocao.publicada
        -promocao.destaque
        -promocao.categoria
        -promocao.hotdeal
'''



URL_BASE = "http://127.0.0.1:5000"


class Loja:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""

        
        self.caminho = Path(__file__).parent

        
        self.promos = []
        #chaves publicas
        self.privete_key = None
        with open(self.caminho / "loja_privatekey.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = serialization.load_pem_private_key(private_key_data,password=None)
        with open(self.caminho / "loja_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = serialization.load_pem_public_key(public_key_data)



        self.acoes = {
            "1": self.cadastrar_promocao,
            "4": self.sair,
        }

        self.categorias_seguidas = set() 
        self.notificacoes_sse = queue.Queue()




    def cadastrar_promocao(self):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        
        item = input("Digite o nome do item: ")
        descricao = input("Digite a descrição da promoção: ")
        categoria  = input("Digite a categoria: ")

        message = {"item": item, "descricao": descricao, "categoria" : categoria}
        message_bytes = json.dumps(message).encode()
        signature = self.private_key.sign(message_bytes)
        payload = {
            "message":message,
            "assinatura": base64.b64encode(signature).decode()
        }
        resposta = requests.post(f"{URL_BASE}/cadastrar",json=payload)
        if resposta.status_code == 200:
            print("Sucesso")
        else:
            print("Falha")
        
  


        


    def sair(self):
        """Encerra o sistema."""
        print("Saindo do sistema. Até mais!")
        return False  
    
    def processar_opcao(self, escolha):
        """
        Processa a opção escolhida pelo usuário.
        
        Args:
            escolha (str): A opção selecionada
            
        Returns:
            bool: True para continuar, False para sair
        """
        acao = self.acoes.get(escolha)
        if acao:
            resultado = acao()
            return resultado if resultado is not None else True
        else:
            print("Opção inválida. Por favor, tente novamente.")
            return True
    
    def executar(self   ):
        """Loop principal do sistema."""
        while True:
            escolha = opcoes()
            if not self.processar_opcao(escolha):
                break
    


        
loja = Loja( )
 
    


def main():
    # t = Thread(target=loja.executar)
    # t.daemon = True
    # t.start()
    loja.executar()
    
    print("Iniciando API Flask na porta 5000...")
    


if __name__ == '__main__':
    main()
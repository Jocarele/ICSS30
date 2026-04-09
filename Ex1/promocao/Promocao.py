import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from threading import Thread
from pathlib import Path


class Promocao:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name,routing_key="recebida")
        self.channel.basic_consume(queue=self.queue_name, 
                                on_message_callback=self.validar_promocoes, auto_ack=True)
        
        self.caminho = Path(__file__).parent
        caminho2= self.caminho.parent
        #Carrega as chaves de privada e publica
        self.privete_key = None
        with open(f"{self.caminho}/promocao_privatekey.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = serialization.load_pem_private_key(private_key_data,password=None)
        with open(f"{self.caminho}/promocao_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = serialization.load_pem_public_key(public_key_data)
        with open(f"{caminho2}/gateway/public_key_gateway.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key_gateway = serialization.load_pem_public_key(public_key_data)

        self.channel.start_consuming()


        
        
    def cadastrar_promocao(self,message):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        message_bytes = json.dumps(message).encode()
        signature = self.private_key.sign(message_bytes)
        payload = {
            "mensagem": message,
            "assinatura": base64.b64encode(signature).decode()
        }
        self.channel.basic_publish(
        exchange='promocao', routing_key="publicada", body=json.dumps(payload))
    

    def validar_promocoes(self,ch, method, properties, body):
        payload = json.loads(body)
        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])
        try:
            self.public_key_gateway.verify(signature, json.dumps(message).encode())
            self.cadastrar_promocao(message)

        except Exception as e:
            print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")
    

def main():
    """Ponto de entrada do programa."""
    gateway = Promocao() 


if __name__ == '__main__':
    main()
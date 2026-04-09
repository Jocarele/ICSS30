import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from pathlib import Path
class Ranking:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name,routing_key="voto")
        self.channel.basic_consume(queue=self.queue_name, 
                                   on_message_callback=self.processar_mensagem, auto_ack=True)
        
        self.itens = []
        self.threshold = 3
        self.caminho = Path(__file__).parent

        self.privete_key = None
        with open(f"{self.caminho}/Ranking_privatekey.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = serialization.load_pem_private_key(private_key_data,password=None)
        with open(f"{self.caminho}/Ranking_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = serialization.load_pem_public_key(public_key_data)

        self.channel.start_consuming()
        


    def processar_mensagem(self,ch, method, properties, body):
        payload = json.loads(body)
        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])

        try:
            found = False
            votos = 0
            for key in self.itens:
                if key["item"] == message["item"]:
                    key["votos"] += 1
                    votos = key["votos"]
                    found = True
                    break
            if not found:
                votos = 1
                self.itens.append({"item": message["item"], "votos": votos})
                
            print(f"Item {message['item']} adicionado ao ranking com {votos} votos.")
            if votos >= self.threshold:
                self.cadastrar_promocao(message)
                

        except Exception as e:
            print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")

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
        exchange='promocao', routing_key="destaque", body=json.dumps(payload))
    


def main():
    """Ponto de entrada do programa."""
    gateway = Ranking() 


if __name__ == '__main__':
    main()
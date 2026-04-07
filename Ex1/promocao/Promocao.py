import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

class Promocao:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        #Cria exchange e fila. A fila tem nome aleatório e esta bindada à exchange com routing key "publicada"
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name,routing_key="recebida")
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.validar_promocoes, auto_ack=True)
        self.channel.start_consuming()
        

        #Carrega as chaves de privada e publica
        self.privete_key = None
        with open("./promocao/promocao_publickey.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_data)
        with open("./promocao_privatekey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_data)
        
        with open("./gateway/public_key_gateway.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key_gateway = ed25519.Ed25519PublicKey.from_public_bytes(public_key_data)

    def cadastrar_promocao(self,message):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        signature = self.private_key.sign(message.encode())
        payload = {
            "mensagem": message,
            "assinatura": base64.b64encode(signature).decode()
        }
        self.channel.basic_publish(
        exchange='promocao', routing_key="publicada", body=json.dumps(payload))
    
    def validar_promocoes(self,ch, method, properties, body):
        for bod in body:
            payload = json.loads(bod)
            message = payload["mensagem"]
            signature = base64.b64decode(payload["assinatura"])
            try:
                
                if self.public_key_gateway.verify(signature, message.encode()):
                    self.cadastrar_promocao(message)

            except Exception as e:
                print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")
    

def main():
    """Ponto de entrada do programa."""
    gateway = Promocao() 


if __name__ == '__main__':
    main()
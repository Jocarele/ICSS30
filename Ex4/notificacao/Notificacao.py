import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from pathlib import Path
import resend
import os
from dotenv import load_dotenv
load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

class Notificacao:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        
        queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue
        #---------email
        self.emailfrom = "Notificação <onboarding@resend.dev>" #email ??
        self.emailto = ["celularmini3@gmail.com"]  #email loja

        # consome evento de publicadas e destaques
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name, routing_key="publicada")
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name, routing_key="destaque")
                
        self.caminho = Path(__file__).parent
        self.caminho2= self.caminho.parent
        with open(f"{self.caminho}/notificacao_privatekey.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = serialization.load_pem_private_key(private_key_data,password=None)
        with open(f"{self.caminho}/notificacao_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = serialization.load_pem_public_key(public_key_data)

        # Bombinha das chaves
        with open(self.caminho2 / "promocao/promocao_publickey.pem", "rb") as f:
            self.public_key_promocao = serialization.load_pem_public_key(f.read())
            
        with open(self.caminho2 / "Ranking/Ranking_publickey.pem", "rb") as f:
            self.public_key_ranking = serialization.load_pem_public_key(f.read())

    def processar_mensagem(self, ch, method, properties, body):
        payload = json.loads(body)

        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])

        try:
            categoria = message.get("categoria", "geral")
            message_bytes = json.dumps(message).encode()
            signature_send = self.private_key.sign(message_bytes)
            payload_send = {
                "mensagem": message,
                "assinatura": base64.b64encode(signature_send).decode()
            }
            if method.routing_key == "publicada":
                self.public_key_promocao.verify(signature, json.dumps(message).encode())
                print(f"[Notificação] Promoção validada. Distribuindo para categoria: {categoria}")
                self.channel.basic_publish(exchange='promocao', routing_key=categoria, body=json.dumps(payload_send))

            elif method.routing_key == "destaque":
                self.public_key_ranking.verify(signature, json.dumps(message).encode())
                print(f"[Notificação] HOT DEAL validado. Distribuindo para destaque.")
                self.channel.basic_publish(exchange='promocao', routing_key=categoria, body=json.dumps(payload_send))
                self.channel.basic_publish(exchange='promocao', routing_key="hotdeal", body=json.dumps(payload_send))
                self.send_email(message)
            
            
        except Exception as e:
            print(f"Assinatura inválida no MS Notificação: {message}. Erro: {e}")

    def send_email(self,message):
        subject = f"{message['item']} da categoria {message['categoria']} virou HOTDEAL "
        html = "<strong> it works!</strong>"
        params: resend.Emails.SendParams ={
            "from": self.emailfrom,
            "to": self.emailto,
            "subject":subject,
            "html": html
        }
        email = resend.Emails.send(params)
    def iniciar(self):
        print("MS Notificação iniciado. Aguardando eventos...")
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.processar_mensagem, auto_ack=True)
        self.channel.start_consuming()

def main():
    notificacao = Notificacao() 
    notificacao.iniciar()

if __name__ == '__main__':
    main()
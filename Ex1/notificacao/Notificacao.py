import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from pathlib import Path

class Notificacao:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        
        queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue
        
        # consome evento de publicadas e destaques
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name, routing_key="publicada")
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name, routing_key="destaque")

        self.caminho = Path(__file__).resolve().parent.parent

        # Bombinha das chaves
        with open(self.caminho / "promocao/promocao_publickey.pem", "rb") as f:
            self.public_key_promocao = serialization.load_pem_public_key(f.read())
            
        with open(self.caminho / "Ranking/Ranking_publickey.pem", "rb") as f:
            self.public_key_ranking = serialization.load_pem_public_key(f.read())

    def processar_mensagem(self, ch, method, properties, body):
        payload = json.loads(body)
        
        # gambiarra pq estava crashando com as proprias msgs
        if "mensagem" not in payload:
            return

        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])

        try:
            categoria = message.get("categoria", "geral")
            
            if method.routing_key == "publicada":
                self.public_key_promocao.verify(signature, json.dumps(message).encode())
                print(f"[Notificação] Promoção validada. Distribuindo para categoria: {categoria}")
                self.channel.basic_publish(exchange='promocao', routing_key=categoria, body=json.dumps(message))

            elif method.routing_key == "destaque":
                self.public_key_ranking.verify(signature, json.dumps(message).encode())
                print(f"[Notificação] HOT DEAL validado. Distribuindo para destaque.")
                
                msg_destaque = message.copy()
                msg_destaque["alerta"] = "HOT DEAL"
                
                # Publica na routing_key "destaque" (para clientes inscritos diretamente em destaques)
                self.channel.basic_publish(exchange='promocao', routing_key="destaque", body=json.dumps(msg_destaque))
                
                # Opcional: Publica também na categoria específica com a flag de hot deal 
                self.channel.basic_publish(exchange='promocao', routing_key=categoria, body=json.dumps(msg_destaque))
                
        except Exception as e:
            print(f"Assinatura inválida no MS Notificação: {message}. Erro: {e}")

    def iniciar(self):
        print("MS Notificação iniciado. Aguardando eventos...")
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.processar_mensagem, auto_ack=True)
        self.channel.start_consuming()

def main():
    notificacao = Notificacao() 
    notificacao.iniciar()

if __name__ == '__main__':
    main()
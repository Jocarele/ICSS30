import pika
import json

class Cliente:
    def __init__(self, categorias_interesse):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        
        queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue

        self.categorias_interesse = categorias_interesse

        # Vincula a fila às categorias  que o cliente quer seguir
        for categoria in self.categorias_interesse:
            self.channel.queue_bind(exchange='promocao', queue=self.queue_name, routing_key=categoria)
            print(f"[*] Inscrito na categoria: {categoria}")

        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.receber_notificacao, auto_ack=True)

    def receber_notificacao(self, ch, method, properties, body):
        mensagem = json.loads(body)
        print(f"\n Capitão fumaça em ação ({method.routing_key.upper()}) ")
        if "alerta" in mensagem:
            print(f"  {mensagem['alerta']} ")
        for chave, valor in mensagem.items():
            if chave != "alerta":
                print(f" -> {chave.capitalize()}: {valor}")
        print("-----------------------------------")

    def iniciar(self):
        print("[*] Aguardando mensagens. Para sair pressione CTRL+C")
        self.channel.start_consuming()

if __name__ == '__main__':
    interesses = ["jogos", "livros", "destaque"]
    cliente = Cliente(interesses)
    cliente.iniciar()
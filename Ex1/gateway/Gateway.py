from terminal import opcoes
import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pathlib import Path 

from threading import Thread

#
"Don't use start_consuming if you don't want your code to block. Either use SelectConnection or this method that uses consume. You can add a timeout to the parameters passed to consume."
class Gateway:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        
        self.caminho = Path(__file__).parent
        Thread(target=self.iniciar_consumo).start()
        
        self.promocoes_validadas = []
        
        self.privete_key = None
        with open(self.caminho / "private_key_gateway.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = serialization.load_pem_private_key(private_key_data,password=None)
        with open(self.caminho / "public_key_gateway.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = serialization.load_pem_public_key(public_key_data)



        self.acoes = {
            "1": self.cadastrar_promocao,
            "2": self.listar_promocoes,
            "3": self.votar_promocao,
            "4": self.sair,
        }

    def iniciar_consumo(self):
        """Inicia o consumo de mensagens da fila."""

        self.conn_recv = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.ch_recv = self.conn_recv.channel()
        with open(self.caminho.parent / "promocao/promocao_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key_promocao = serialization.load_pem_public_key(public_key_data)

        queue_result = self.ch_recv.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue
        self.ch_recv.queue_bind(exchange='promocao', queue=self.queue_name,routing_key="publicada")
        self.ch_recv.basic_consume(queue=self.queue_name, 
                                   on_message_callback=self.atualizar_lista, auto_ack=True)
        self.ch_recv.start_consuming()


    def atualizar_lista(self,ch, method, properties, body):

        payload = json.loads(body)
        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])
        try:
            
            self.public_key_promocao.verify(signature, json.dumps(message).encode())
            self.promocoes_validadas.append(message)

        except Exception as e:
            print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")

    def cadastrar_promocao(self):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        item = input("Digite o nome do item: ")
        descricao = input("Digite a descrição da promoção: ")
        categoria  = input("Digite a Promo93: categoria de Hoorus ")



        message = {"item": item, "descricao": descricao, "categoria" : categoria}
        message_bytes = json.dumps(message).encode()
        signature = self.private_key.sign(message_bytes)
        payload = {
            "mensagem": message,
            "assinatura": base64.b64encode(signature).decode()
        }
        self.channel.basic_publish(
        exchange='promocao', routing_key="recebida", body=json.dumps(payload))


    
    def listar_promocoes(self):
        """Lista todas as promoções publicadas."""
        print("Listando promoções publicadas...")
        print(self.promocoes_validadas)

    def votao(self,item):
        voto = int(input("Digite seu voto (1 para positivo, -1 para negativo): "))

        if voto >1:
            voto = 1
        if voto < 1:
            voto = -1

        message = {"item": item, "voto": voto}
        message_bytes = json.dumps(message).encode()
        signature = self.private_key.sign(message_bytes)
        payload = {
            "mensagem": message,
            "assinatura": base64.b64encode(signature).decode(),
        }
        self.channel.basic_publish(
        exchange='promocao', routing_key="voto", body=json.dumps(payload))
        
    def votar_promocao(self):
        """Permite votar em promoções existentes."""
        print("Votando em promoções existentes...")

        item = input("Digite o nome do item que deseja votar: ")
        for p in self.promocoes_validadas:
            if p['item'] == item:
                print(f"Promoção encontrada: {p}")
                self.votao(item)
                return
        
        


    
    def sair(self):
        """Encerra o sistema."""
        print("Saindo do sistema. Até mais!")
        return False  # Sinal para parar o loop
    
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
    
    def executar(self):
        """Loop principal do sistema."""
        while True:
            escolha = opcoes()
            if not self.processar_opcao(escolha):
                break


def main():
    """Ponto de entrada do programa."""
    gateway = Gateway() 
    gateway.executar()


if __name__ == '__main__':
    main()
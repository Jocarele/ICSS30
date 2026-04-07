from terminal import opcoes
import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

class Gateway:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        queue_result = self.channel.queue_declare(queue='', exclusive=True)
        self.queue_name = queue_result.method.queue
        self.channel.queue_bind(exchange='promocao', queue=self.queue_name,routing_key="publicada")
        
        self.channel.basic_consume(queue=self.queue_name, 
                                   on_message_callback=self.atualizar_lista, auto_ack=True)
        self.channel.start_consuming()
        

        self.promocoes_validadas = []

        self.privete_key = None
        with open("./private_key_gateway.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_data)
        with open("./public_key_gateway.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_data)
        with open("./public_key_promocao.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key_promocao = ed25519.Ed25519PublicKey.from_public_bytes(public_key_data)


        self.acoes = {
            "1": self.cadastrar_promocao,
            "2": self.listar_promocoes,
            "3": self.votar_promocao,
            "4": self.sair,
        }

    def atualizar_lista(self,ch, method, properties, body):

        for bod in body:
            payload = json.loads(bod)
            message = payload["mensagem"]
            signature = base64.b64decode(payload["assinatura"])
            try:
                
                self.public_key_promocao.verify(signature, message.encode())
                self.promocoes_validadas.append(message)

            except Exception as e:
                print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")

    
    def cadastrar_promocao(self,item,descricao):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        
        message = {"item": item, "descricao": descricao}
        signature = self.private_key.sign(message.encode())
        payload = {
            "mensagem": message,
            "assinatura": base64.b64encode(signature).decode()
        }
        self.channel.basic_publish(
        exchange='promocao', routing_key="recebida", body=json.dumps(payload))


    
    def listar_promocoes(self,payload):
        """Lista todas as promoções publicadas."""
        print("Listando promoções publicadas...")

        print(self.promocoes_validadas)


        
    def votar_promocao(self,item,descricao,voto):
        """Permite votar em promoções existentes."""
        print("Votando em promoções existentes...")

        if voto >1:
            voto = 1
        if voto < 1:
            voto = -1
        #TODO: validar se a promocao existe
        message = {"item": item,"descricao": descricao, "voto": voto}
        signature = self.private_key.sign(message.encode())
        payload = {
            "mensagem": message,
            "assinatura": base64.b64encode(signature).decode(),
        }
        self.channel.basic_publish(
        exchange='promocao', routing_key="voto", body=json.dumps(payload))

    
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
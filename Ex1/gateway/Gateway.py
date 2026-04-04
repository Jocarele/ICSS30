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
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        self.channel.queue_bind(exchange='promocao', queue='',routing_key="publicada")

        self.privete_key = None
        with open("./private_key_gateway.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_data)
        with open("./public_key_gateway.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_data)


        self.acoes = {
            "1": self.cadastrar_promocao,
            "2": self.listar_promocoes,
            "3": self.votar_promocao,
            "4": self.sair,
        }
    
    def cadastrar_promocao(self,message,signature):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        # Lógica para cadastrar promoção
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
        def processar_mensagem(ch, method, properties, body):
            payload = json.loads(body)
            message = payload["mensagem"]
            signature = base64.b64decode(payload["assinatura"])
            try:
                self.public_key.verify(signature, message.encode())
                print(f"Promoção: {message}")
            except Exception as e:
                print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")

        self.channel.basic_consume(queue='fila_gateway', on_message_callback=self.processar_mensagem, auto_ack=True)


        
    def votar_promocao(self):
        """Permite votar em promoções existentes."""
        print("Votando em promoções existentes...")
        # Lógica para votar em promoções
    
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
            # Se a ação retorna False (caso do 'sair'), encerra
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
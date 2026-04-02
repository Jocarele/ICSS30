from terminal import opcoes
import pika

class Gateway:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='unico', exchange_type='direct')

        self.acoes = {
            "1": self.cadastrar_promocao,
            "2": self.listar_promocoes,
            "3": self.votar_promocao,
            "4": self.sair,
        }
    
    def cadastrar_promocao(self):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        # Lógica para cadastrar promoção
        self.channel.basic_publish(
        exchange='unico', routing_key="publicada", body=message)
    
    def listar_promocoes(self):
        """Lista todas as promoções publicadas."""
        print("Listando promoções publicadas...")
        # Lógica para listar promoções
    
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
import pika
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pathlib import Path 
from terminal import opcoes
from threading import Thread
# FLASK
from flask import Flask, jsonify, request
from flask_cors import CORS
import queue
from flask import Response

'''
Responsavel por:
    -Export a API REST consumida pelo frontend
    -transformar ações dos usuários em eventos publicados no RabbitMQ
    -consumir eventos dos demais microserviços
    -mantes conexões SSE com os clientes
    -encaminhar notificações SSE apenas para os clientes interessados

Precisa disponibilizar endpoint REST para(ROTAS):
    -cadastrar promoções na loja
    -listar promoções publicadas
    -votar em promoção
    -registrar interesse em categoria
    -cancelar interesse em categoria

SSE Notificiações em tempo real
    -Hot deals
    -categorias seguidas pelo usuario

RabbitMQ
    Publica evento:
        -promocao.recebida
        -promocao.voto
    Consome evento:
        -promocao.publicada
        -promocao.destaque
        -promocao.categoria
        -promocao.hotdeal
'''


app = Flask(__name__)
CORS(app)


class Gateway:
    """Gateway centraliza o menu principal e o roteamento de ações do sistema."""
    
    def __init__(self):
        """Inicializa o Gateway com o dicionário de ações."""
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='promocao', exchange_type='direct')
        
        self.caminho = Path(__file__).parent
        Thread(target=self.iniciar_consumo_publicado).start()
        Thread(target=self.iniciar_consumo_hotdeal).start()
        Thread(target=self.iniciar_consumo_categoria).start()
        
        self.promos = []
        #chaves publicas
        self.privete_key = None
        with open(self.caminho / "private_key_gateway.pem", "rb") as f:
            private_key_data = f.read()
            self.private_key = serialization.load_pem_private_key(private_key_data,password=None)
        with open(self.caminho / "public_key_gateway.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key = serialization.load_pem_public_key(public_key_data)
        with open(self.caminho.parent / "notificacao/notificacao_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key_notificacao = serialization.load_pem_public_key(public_key_data)
        with open(self.caminho.parent / "promocao/promocao_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key_promocao = serialization.load_pem_public_key(public_key_data)
        #with open(self.caminho / "public_key_loja.pem", "rb") as f:
        #    public_key_data = f.read()
        #    self.public_key_loja = serialization.load_pem_public_key(public_key_data)



        self.acoes = {
            "1": self.cadastrar_promocao,
            "2": self.listar_promocoes,
            "3": self.votar_promocao,
            "4": self.sair,
        }

        self.categorias_seguidas = set() #### categorias que o amigão está seguindo
        self.notificacoes_sse = queue.Queue()


    def iniciar_consumo_publicado(self):
        """Inicia o consumo de mensagens da fila."""

        self.conn_recv1 = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.ch_recv1 = self.conn_recv1.channel()


        queue_result = self.ch_recv1.queue_declare(queue='', exclusive=True)
        self.queue_name1 = queue_result.method.queue
        self.ch_recv1.queue_bind(exchange='promocao', queue=self.queue_name1,routing_key="publicada")
        self.ch_recv1.basic_consume(queue=self.queue_name1, 
                                   on_message_callback=self.atualizar_lista_publicado, auto_ack=True)
        self.ch_recv1.start_consuming()

    def atualizar_lista_publicado(self,ch, method, properties, body):

        payload = json.loads(body)
        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])
        try:
            
            self.public_key_promocao.verify(signature, json.dumps(message).encode())
            self.promos.append(message)

        except Exception as e:
            print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")
    
    def iniciar_consumo_hotdeal(self):
        """Inicia o consumo de mensagens da fila."""

        self.conn_recv2 = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.ch_recv2 = self.conn_recv2.channel()
        with open(self.caminho.parent / "notificacao/notificacao_publickey.pem", "rb") as f:
            public_key_data = f.read()
            self.public_key_notificacao = serialization.load_pem_public_key(public_key_data)

        queue_result = self.ch_recv2.queue_declare(queue='', exclusive=True)
        self.queue_name2 = queue_result.method.queue
        self.ch_recv2.queue_bind(exchange='promocao', queue=self.queue_name2,routing_key="hotdeal")
        self.ch_recv2.basic_consume(queue=self.queue_name2, 
                                   on_message_callback=self.atualizar_lista_hotdeal, auto_ack=True)
        self.ch_recv2.start_consuming()

    def atualizar_lista_hotdeal(self,ch, method, properties, body):
        payload = json.loads(body)
        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])
        try:
            self.public_key_promocao.verify(signature, json.dumps(message).encode())
            
            #TODO
            alerta = f" HOT DEAL: A promoção '{message.get('item')}' está em destaque!"
            self.notificacoes_sse.put(alerta)
            

        except Exception as e:
            print(f"Assinatura inválida para a hotdeal: {message}. Erro: {e}")
    
    def iniciar_consumo_categoria(self):
        """Inicia o consumo de mensagens da fila."""

        self.conn_recv3 = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.ch_recv3 = self.conn_recv3.channel()

        queue_result = self.ch_recv3.queue_declare(queue='', exclusive=True)
        self.queue_name3 = queue_result.method.queue
        self.ch_recv3.queue_bind(exchange='promocao', queue=self.queue_name3,routing_key="categoria")
        self.ch_recv3.basic_consume(queue=self.queue_name3, 
                                   on_message_callback=self.atualizar_lista_categoria, auto_ack=True)
        self.ch_recv3.start_consuming()

    def atualizar_lista_categoria(self,ch, method, properties, body):
        payload = json.loads(body)
        message = payload["mensagem"]
        signature = base64.b64decode(payload["assinatura"])
        try:
            self.public_key_promocao.verify(signature, json.dumps(message).encode())
            
            categoria = message.get('categoria', '').strip().lower()
            if categoria in self.categorias_seguidas:
                alerta = f"🔔 Novidade na sua categoria favorita ({categoria.upper()}): {message.get('item')}!"
                self.notificacoes_sse.put(alerta)

        except Exception as e:
            print(f"Assinatura inválida para a promoção: {message}. Erro: {e}")
        
        


    def cadastrar_promocao(self):
        """Cadastra uma nova promoção no sistema."""
        print("Cadastrando nova promoção...")
        item = input("Digite o nome do item: ")
        descricao = input("Digite a descrição da promoção: ")
        categoria  = input("Digite a categoria: ")

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
        print(self.promos)

    def votao(self,promo, voto_recebido):
        if voto_recebido >1:
            voto_recebido = 1
        elif voto_recebido < 1:
            voto_recebido = -1


        message = {"item" : promo["item"],"categoria": promo["categoria"], "votos": voto_recebido }

        message_bytes = json.dumps(message).encode()
        signature = self.private_key.sign(message_bytes)
        payload = {
            "mensagem": message,
            "assinatura": base64.b64encode(signature).decode(),
        }
        self.channel.basic_publish(
        exchange='promocao', routing_key="voto", body=json.dumps(payload))
        
    def votar_promocao(self,item, voto_recebido=1):
        """Permite votar em promoções existentes."""
        print("Votando em promoções existentes...")

        for p in self.promos:
            if p['item'] == item:
                print(f"Promoção encontrada: {p}")
                self.votao(p, voto_recebido)
                return 1
        print(f"Promoção não encontrada")
        return None
    

    def sair(self):
        """Encerra o sistema."""
        print("Saindo do sistema. Até mais!")
        return False  
    
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
    
    def executar(self   ):
        """Loop principal do sistema."""
        while True:
            escolha = opcoes()
            if not self.processar_opcao(escolha):
                break
        
gateway = Gateway( )

@app.route('/promocoes', methods=['GET'])
def get_items():
    return jsonify(gateway.promos), 200
    
@app.route('/promocoes', methods=['POST'])
def add_item():
    try:
        new_promo = request.get_json()
        signature = new_promo.pop("signature")
        gateway.public_key_loja.verify(signature, json.dumps(new_promo).encode())
        #new_promo["id"] = len(gateway.promos) + 1  # Assign an ID
        gateway.promos.append(new_promo)
        return jsonify(new_promo), 201

    except Exception as e:
        print(f"Assinatura inválida para a promoção: {new_promo}. Erro: {e}")
        return jsonify(new_promo), 404 #ERRO
    
@app.route('/promocoes/votar', methods=['POST'])
def votar_promo():
    try:
        dados_voto = request.get_json()
        item_nome = dados_voto.get('item')
        valor = dados_voto.get('voto')

        if gateway.votar_promocao(item_nome, valor):
            return jsonify({"mensagem" : "Voto registrado"}), 201
        else:
            return jsonify({"erro" : "não acho essa promo"}), 404

    except Exception as e:
        print(f"Erro ao votar. Erro: {e}")
        return jsonify({"erro" : "erro interno"}), 500 #ERRO
        
@app.route('/promocoes/interesse', methods=['POST'])
def interesse_categoria():
    try:
        dados = request.get_json()
        categoria = dados.get('categoria', '').strip().lower()
        if categoria:
            gateway.categorias_seguidas.add(categoria)
            print(f"[*] Usuário registou interesse na categoria: {categoria}")
            print(f"Interesses ativos: {list(gateway.categorias_seguidas)}")
            return jsonify({"status": "sucesso", "categoria": categoria}), 200
        return jsonify({"erro": "Categoria invalida"}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
        
@app.route('/promocoes/desinteresse', methods=['POST'])
def desinteresse_categoria():
    try:
        dados = request.get_json()
        categoria = dados.get('categoria', '').strip().lower()
        if categoria in gateway.categorias_seguidas:
            gateway.categorias_seguidas.remove(categoria)
            print(f"[-] Usuário removeu interesse da categoria: {categoria}")
            print(f"Interesses ativos: {list(gateway.categorias_seguidas)}")
            return jsonify({"status": "sucesso", "categoria": categoria}), 200
        return jsonify({"erro": "Categoria nao encontrada nos interesses"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
        

@app.route('/stream', methods=['GET'])
def stream():
    def event_stream():
        while True:
            mensagem = gateway.notificacoes_sse.get()
            yield f"data: {mensagem}\n\n"
            
    return Response(event_stream(), mimetype="text/event-stream")


    
    


def main():
    t = Thread(target=gateway.executar)
    t.daemon = True
    t.start()
    
    print("Iniciando API Flask na porta 5000...")
    app.run(port=5000, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
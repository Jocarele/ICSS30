import raft_pb2_grpc
import raft_pb2
import threading
import grpc


def get_stub(lider):
    channel = grpc.insecure_channel(lider)
    return raft_pb2_grpc.ReplicateStub(channel)

# Tem que ter essa listinha, pq como foi removido o servidor de nomes, se o lider morrer, preciso chutar outro no, para que 
# o outro no avise quem é o lider
todos_nos = {
    "no1": "localhost:5001",
    "no2": "localhost:5002",
    "no3": "localhost:5003",
    "no4": "localhost:5004"
}
nos = ["no1","no2","no3","no4"]
indice = 0
lider = todos_nos[nos[indice]]


while True:
    texto  = input("Digite uma raça de hipopótamo: ")
    try:
        stub = get_stub(lider)
        resposta = stub.receber_comando(
            raft_pb2.comando_cliente(command=texto),
            timeout=0.5
        )
        print(resposta)
        if not resposta.success:
            lider = resposta.lider
            stub = get_stub(lider)
            resposta = stub.receber_comando(
                raft_pb2.comando_cliente(command=texto),
                timeout=0.5
            )
    except:
        print("INsano, como que deu errado?")
        indice = (indice + 1) % len(nos)
        lider = todos_nos[nos[indice]]

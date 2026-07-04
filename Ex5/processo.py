import sys
import time
import random
import sqlite3
import raft_pb2_grpc
import raft_pb2
import threading
import grpc
from concurrent import futures


CORES = {
    "seguidor": "\033[94m",  # Azul: pacífico, apenas escutando
    "candidato": "\033[93m", # Amarelo: em transição, chamando atenção
    "lider": "\033[92m",     # Verde: sucesso, estabilidade
    "erro": "\033[91m",      # Vermelho: falhas de conexão
    "reset": "\033[0m"       # Retorna para a cor padrão do terminal
}

class ReplicateService(raft_pb2_grpc.ReplicateServicer):
    def __init__(self, processo):
        self.processo = processo

    def pedir_voto(self, request, context):
        resultado = self.processo.pedir_voto(
            request.id_candidato,
            request.termo_candidato
        )

        return raft_pb2.success(
            success=resultado
        )

    def anexar_entradas(self, request, context):
        

        resultado = self.processo.anexar_entradas(
            request.id_lider,
            request.termo_lider,
            request.commit,
            request.commit_id,
            request.commit_command,
            request.uncommit,
            request.uncommit_id,
            request.uncommit_command,
        )

        return raft_pb2.success(
            success=resultado
        )

    def receber_comando(self, request, context):
        resposta = self.processo.receber_comando(
            request.command
        )
        #print(resposta)
        if resposta:
            ok, command, lider = resposta

            return raft_pb2.resposta_cliente(
                success=ok,
                mensagem=command,
                lider = lider
            )
        return raft_pb2.resposta_cliente(
                success=False,
                mensagem="command recusado",
                lider=self.processo.lider
                )
        
    def set_lider(self,request,context):
        resultado = self.processo.set_lider(
            request.lider,
            request.termo
        )

        return raft_pb2.success(
            success=resultado
        )

class Processo(object):
    def __init__(self, id, porta):
        self.id = id
        self.porta = porta
        
        self.estado = "seguidor"
        self.termo_atual = 0
        self.log = [] # MSG commitadas
        self.uncommit = [] #MSG não comitadas

        self.votou_em = 0
        db_path = "./nodes.db"
        self.conn = sqlite3.connect(db_path,check_same_thread=False)
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {id}_uncommited(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL
        );
        """)
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {id}_commited(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL
            );

        """)

        self.lock = threading.Lock()
        self.ultimo_heartbeat = time.time()
        tempo_aleatorio = random.randint(150,300)/ 1000
        self.limite = tempo_aleatorio


        self.outros_nos = {"no1": "localhost:5001",
                           "no2": "localhost:5002", 
                           "no3": "localhost:5003",
                           "no4": "localhost:5004"}
        self.eu = self.outros_nos[id]

        if self.id in self.outros_nos:
            self.outros_nos.pop(self.id) 
        self.threshold = len (self.outros_nos)
        self.lider = ""
    
    def get_stub(self,no):
        channel = grpc.insecure_channel(self.outros_nos[no])
        stub = raft_pb2_grpc.ReplicateStub(channel)
        return stub
    

    def set_lider(self,lider,termo):
         with self.lock:
            if termo >= self.termo_atual:
                self.termo_atual = termo
                self.lider = lider
                self.estado = "seguidor"
                self.ultimo_heartbeat = time.time()
                return True

            print("EU SOU MAIOR")
            return False

    def monitorar_time(self):
        while(True):
            time.sleep(0.01)
            controle = False

            with self.lock:
                if(self.estado == "seguidor" or self.estado == "candidato"):
                    if(time.time() - self.ultimo_heartbeat > self.limite):
                        self.estado = "candidato"
                        self.termo_atual  = self.termo_atual + 1
                        self.limite = random.randint(150,300)/1000
                        self.ultimo_heartbeat = time.time()
                        self.imprimir_log(f"timeout! virei candidato e começando eleição (limite novo: {self.limite}s)")
                        controle = True
            if controle:
                self.comecar_eleicao()

    


    def comecar_eleicao(self):
        venceu = False
        
        with self.lock:
            self.votou_em = self.id
            termo_da_eleicao = self.termo_atual
        votos = 1
        self.imprimir_log(f"pedindo votos para o termo {termo_da_eleicao}...")

        for a in list(self.outros_nos):
            try:
                stub=self.get_stub(a)
                resposta = stub.pedir_voto(
                    raft_pb2.voto(
                        id_candidato=self.id,
                        termo_candidato=termo_da_eleicao
                    ),
                    timeout=0.5
                )
     
                if resposta.success:
                    votos += 1
                    self.imprimir_log(f"recebi voto de {a} (total: {votos})")
                else:
                    self.imprimir_log(f"{a} negou voto")
            except:
                self.imprimir_log(f"{a} não respondeu", erro=True)
                #with self.lock:
                    #self.outros_nos.pop(a)
                    #self.threshold -= 1
                
        with self.lock:
            if votos >= self.threshold  and self.estado == "candidato":
                self.estado = "lider"
                venceu = True
        #TODO: DEFINIR LIDER

        if venceu:
            self.imprimir_log(f">>> ELEITO LÍDER do termo {termo_da_eleicao} com {votos} votos <<<")
            self.lider = self.eu
            for a in list(self.outros_nos):
                try:
                    stub=self.get_stub(a)
                    resposta = stub.set_lider(
                        raft_pb2.lider(
                            lider=self.eu,
                            termo=self.termo_atual
                        ),
                        timeout=0.5
                    )
                except:
                    print("deu erro no set lider")
                    continue
            thread_heartbeat = threading.Thread(target=self.enviar_heartbeats, daemon=True)
            thread_heartbeat.start()
        else:
            self.imprimir_log(f"não venci a eleição (consegui {votos} votos)")

                
    def enviar_heartbeats(self):
        while True:
            time.sleep(0.01)

            with self.lock:
                if self.estado != "lider":
                    self.imprimir_log("parando de enviar heartbeats (não sou mais líder)")
                    break
            for a in list(self.outros_nos):
                try:
                    stub = self.get_stub(a)
                    
                    resposta = stub.anexar_entradas(
                                    raft_pb2.entrada(
                                        id_lider=self.id,
                                        termo_lider=self.termo_atual,
                                        uncommit=False,
                                        uncommit_id = 0,
                                        uncommit_command = "",
                                        commit=False,
                                        commit_id = 0,
                                        commit_command = ""
                                    ),
                                    timeout=0.5
                                )
                    if resposta.success:
                        pass
                    # else:
                    #     self.imprimir_log(f"falha no heartbeat para {a}", erro=True)
                except Exception as e:
                    #self.imprimir_log(f"falha no heartbeat para {a}: {e}", erro=True)
                    pass
                    # with self.lock:
                    #     self.outros_nos.pop(a)
                    #     self.threshold -= 1
    #EXPOSE                   
    def anexar_entradas(self, id_lider, termo_lider, commit,commit_id,commit_command, uncommit,uncommit_id,uncommit_command):
        with self.lock:
            if termo_lider < self.termo_atual:
                self.imprimir_log(f"rejeitei heartbeat de {id_lider} (termo {termo_lider} < meu termo {self.termo_atual})")
                return False
            if termo_lider >= self.termo_atual:
                era_lider = (self.estado == "lider")
                era_candidato = (self.estado == "candidato")

                self.termo_atual = max(termo_lider, self.termo_atual)
                self.estado = "seguidor"
                self.ultimo_heartbeat = time.time()
                if era_lider or era_candidato:
                    self.imprimir_log(f"reconheci {id_lider} como líder do termo {termo_lider}, voltei a ser seguidor")
                
                if uncommit:
                    cursor = self.conn.cursor()
                    cursor.execute(f"SELECT * FROM {self.id}_uncommited ORDER BY id DESC LIMIT 1; ")

                    ultima_msg = cursor.fetchone()
                    if ultima_msg is not None:
                        if ultima_msg[0] + 1 != uncommit_id:
                            print(f"{self.id} DESATUALIZADO, PF ME ATUALIZE")
                    
                    cursor.execute(f"INSERT INTO {self.id}_uncommited (id, command) VALUES (?, ?)", (uncommit_id,uncommit_command))
                    self.conn.commit()
                    mensagem = f"uncommit:{uncommit}"
                    self.imprimir_log(mensagem=f"{uncommit}")
                
                if commit:
                    cursor = self.conn.cursor()
                    cursor.execute(f"SELECT * FROM {self.id}_uncommited ORDER BY id DESC LIMIT 1; ")
                    ultima_msg = cursor.fetchone()
                    if ultima_msg[0] != commit_id:
                            print(f"{self.id} DESATUALIZADO, PF ME ATUALIZE")
                    cursor.execute(f"INSERT INTO {self.id}_commited (id, command) VALUES (?, ?)", ultima_msg)
                    self.conn.commit()
                    self.imprimir_log(mensagem=f"ultima_msg")

                if era_lider or era_candidato:
                    self.imprimir_log(f"reconheci {id_lider} como líder do termo {termo_lider}, voltei a ser seguidor")
                return True
    




    #EXPOSE
    def pedir_voto(self, id_candidato, termo_candidato):
        with self.lock:

            if termo_candidato > self.termo_atual:
                self.termo_atual = termo_candidato
                self.estado = "seguidor"
                self.votou_em = 0 

            if termo_candidato < self.termo_atual:
                self.imprimir_log(f"neguei voto a {id_candidato} (termo {termo_candidato} < meu {self.termo_atual})")
                return False
            if self.votou_em != 0 and self.votou_em != id_candidato:
                self.imprimir_log(f"neguei voto a {id_candidato} (já votei em {self.votou_em} neste termo)")
                return False
            

            self.votou_em = id_candidato
            self.ultimo_heartbeat = time.time() 
            self.imprimir_log(f"votei em {id_candidato} para o termo {termo_candidato}")
            return True
                        
    #EXPOSE (CLIENTE?)
    def receber_comando(self, name):
        with self.lock:
            if self.estado != "lider":
                print("num sou lider")
                if self.lider == "":
                    for no in self.outros_nos:
                        return False,name,self.outros_nos[no]
                else:
                    return False,name,self.lider

            cursor = self.conn.cursor()
            cursor.execute(f"INSERT INTO {self.id}_uncommited (command) VALUES (?);",(name,))
            self.conn.commit()

        confirmacoes = 1
        #==================== UNCOMMITED ==============

        for a in list(self.outros_nos):
            stub = self.get_stub(a)

            try:
                with self.lock:
                    cursor.execute(f"SELECT * FROM {self.id}_uncommited ORDER BY id DESC LIMIT 1; ") #pega o id da msg
                    ultima_msg = cursor.fetchone()
                    print(ultima_msg)
                
                
                resposta = stub.anexar_entradas(
                                    raft_pb2.entrada(
                                        id_lider=self.id,
                                        termo_lider=self.termo_atual,
                                        uncommit=True,
                                        uncommit_id = ultima_msg[0],
                                        uncommit_command = ultima_msg[1],
                                        commit=False,
                                        commit_id = 0,
                                        commit_command = ""
                                    ),
                                    timeout=0.5
                                )
                if resposta.success:
                    
                    #self.imprimir_log(mensagem=f"{ultima_msg})
                    confirmacoes +=1
            except:
                print("deu ruim uncommit")
                # self.outros_nos.pop(a)
                # self.threshold -= 1
                
        #====================      COMMITED     ==============

        if confirmacoes >= self.threshold:
            with self.lock:
                cursor.execute(f"INSERT INTO {self.id}_commited (id, command) VALUES (?, ?)", ultima_msg)
                self.conn.commit()
            self.imprimir_log(mensagem=f"{ultima_msg}")
            cliente = "Erro"
            for a in list(self.outros_nos):
                try:
                    stub = self.get_stub(a)
                
                    resposta = stub.anexar_entradas(
                                    raft_pb2.entrada(
                                        id_lider=self.id,
                                        termo_lider=self.termo_atual,
                                        uncommit=False,
                                        uncommit_id = 0,
                                        uncommit_command = "",
                                        commit=True,
                                        commit_id =  ultima_msg[0],
                                        commit_command = ultima_msg[1]
                                    ),
                                    timeout=0.5
                                )
                    print(resposta)
                    if resposta.success:
                        cliente =  f'Receba meu {ultima_msg}'
                    else:
                        print(resposta)
                        return False,name,self.lider
                except:
                    #NÃO PODE RETURN AQUI QUANDO UM NO MORRE FERRA TUDO
                    print("deu ruim commit")
                    
                    # self.outros_nos.pop(a)
                    # self.threshold -= 1
            return True,name,self.lider
        else:
            return False,name,self.lider
            

                
        
    
    def imprimir_log(self, mensagem, erro=False):
        if erro:
            cor = CORES["erro"]
        else:
            cor = CORES[self.estado] 
            
        print(f"{cor}[Nó: {self.id} | Termo: {self.termo_atual} | {self.estado.upper()}] {mensagem}{CORES['reset']}", flush=True)

if __name__ == "__main__":
    
    id = sys.argv[1]
    porta = int(sys.argv[2]) 

    meu_processo = Processo(id, porta)
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )
    raft_pb2_grpc.add_ReplicateServicer_to_server(
        ReplicateService(meu_processo),
        server
    )

    server.add_insecure_port(f"[::]:{porta}")

    thread_timer = threading.Thread(
        target=meu_processo.monitorar_time,
        daemon=True
    )
    thread_timer.start()


    print(f"Nó Estado: {meu_processo.estado}", flush=True)
    
    server.start()
    server.wait_for_termination()




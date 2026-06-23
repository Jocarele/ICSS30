import sys
import Pyro5.api
import threading
import time
import random
import sqlite3



CORES = {
    "seguidor": "\033[94m",  # Azul: pacífico, apenas escutando
    "candidato": "\033[93m", # Amarelo: em transição, chamando atenção
    "lider": "\033[92m",     # Verde: sucesso, estabilidade
    "erro": "\033[91m",      # Vermelho: falhas de conexão
    "reset": "\033[0m"       # Retorna para a cor padrão do terminal
}


@Pyro5.api.expose
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


        self.outros_nos = {"no1": "5001","no2": "5002", "no3": "5003","no4": "5004"}
        if self.id in self.outros_nos:
            self.outros_nos.pop(self.id) 
        self.threshold = len (self.outros_nos)

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
            string_conxexao = "PYRO:" + a + "@localhost:" + self.outros_nos[a]

            proxy = Pyro5.api.Proxy(string_conxexao)
            proxy._pyroTimeout = 0.5   ###### gambiarra

            try:
                if proxy.pedir_voto(self.id, termo_da_eleicao):
                    votos = votos + 1
                    self.imprimir_log(f"recebi voto de {a} (total: {votos})")
                else:
                    self.imprimir_log(f"{a} negou voto")
            except:
                self.imprimir_log(f"{a} não respondeu", erro=True)
                with self.lock:
                    self.outros_nos.pop(a)
                    self.threshold -= 1
                
        with self.lock:
            if votos >= self.threshold  and self.estado == "candidato":
                self.estado = "lider"
                venceu = True

        if venceu:
            self.imprimir_log(f">>> ELEITO LÍDER do termo {termo_da_eleicao} com {votos} votos <<<")
            ns = Pyro5.api.locate_ns()
            minha_string = "PYRO:" + self.id + "@localhost:" + str(self.porta)
            ns.register("Líder", minha_string)
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
                string_conxexao = "PYRO:" + a + "@localhost:" + self.outros_nos[a]

                proxy = Pyro5.api.Proxy(string_conxexao)

                proxy._pyroTimeout = 0.2
                try:
                    if proxy.anexar_entradas(self.id, self.termo_atual, False,False):
                        pass
                except:
                    self.imprimir_log(f"falha no heartbeat para {a}", erro=True)
                    with self.lock:
                        self.outros_nos.pop(a)
                        self.threshold -= 1
    #EXPOSE                   
    def anexar_entradas(self, id_lider, termo_lider, commit,uncommit):
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
                        if ultima_msg[0] + 1 != uncommit[0]:
                            print(f"{self.id} DESATUALIZADO, PF ME ATUALIZE")
                    
                    cursor.execute(f"INSERT INTO {self.id}_uncommited (id, command) VALUES (?, ?)", uncommit)
                    self.conn.commit()
                    mensagem = f"uncommit:{uncommit}"
                    self.imprimir_log(mensagem=f"{uncommit}")
                
                if commit:
                    cursor = self.conn.cursor()
                    cursor.execute(f"SELECT * FROM {self.id}_uncommited ORDER BY id DESC LIMIT 1; ")
                    ultima_msg = cursor.fetchone()
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
                print("deu ruim")
                return False

            cursor = self.conn.cursor()
            cursor.execute(f"INSERT INTO {self.id}_uncommited (command) VALUES (?);",(name,))
            self.conn.commit()

        confirmacoes = 1
        #==================== UNCOMMITED ==============

        for a in list(self.outros_nos):
            string_conxexao = "PYRO:" + a + "@localhost:" + self.outros_nos[a]
            proxy = Pyro5.api.Proxy(string_conxexao)

            proxy._pyroTimeout = 0.5

            try:
                with self.lock:
                    cursor.execute(f"SELECT * FROM {self.id}_uncommited ORDER BY id DESC LIMIT 1; ") #pega o id da msg
                    ultima_msg = cursor.fetchone()
                    print(ultima_msg)
                if proxy.anexar_entradas(self.id, self.termo_atual, False,ultima_msg):
                    
                    #self.imprimir_log(mensagem=f"{ultima_msg})
                    confirmacoes +=1
            except:
                print("deu ruim")
                self.outros_nos.pop(a)
                self.threshold -= 1
                
        #====================      COMMITED     ==============

        if confirmacoes >= self.threshold:
            with self.lock:
                cursor.execute(f"INSERT INTO {self.id}_commited (id, command) VALUES (?, ?)", ultima_msg)
                self.conn.commit()
            self.imprimir_log(mensagem=f"{ultima_msg}")
            cliente = "Erro"
            for a in list(self.outros_nos):
                try:
                    string_conxexao = "PYRO:" + a + "@localhost:" + self.outros_nos[a]
                    proxy = Pyro5.api.Proxy(string_conxexao)
                    if proxy.anexar_entradas(self.id, self.termo_atual, True,False):
                        cliente =  f'Receba meu {ultima_msg}'
                except:
                    print("deu ruim")
                    self.outros_nos.pop(a)
                    self.threshold -= 1
            return cliente
            

                
        
    
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

    daemon = Pyro5.server.Daemon(port=porta)

    uri = daemon.register(meu_processo, objectId=id)

    print(f"Nó Estado: {meu_processo.estado}", flush=True)
    print(f"URI :{uri}", flush=True)
    
    thread_timer = threading.Thread(target=meu_processo.monitorar_time, daemon=True)
    thread_timer.start()



    daemon.requestLoop() # bloquenate
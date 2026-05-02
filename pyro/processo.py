import sys
import Pyro5.api
import threading
import time
import random


@Pyro5.api.expose
class Processo(object):
    def __init__(self, id, porta):
        self.id = id
        self.porta = porta
        
        self.estado = "seguidor"
        self.termo_atual = 0
        self.log = []

        self.votou_em = 0


        self.lock = threading.Lock()
        self.ultimo_heartbeat = time.time()
        tempo_aleatorio = random.randint(2,4)
        self.limite = tempo_aleatorio


        

        self.outros_nos = {"no1": "5001","no2": "5002", "no3": "5003","no4": "5004 "}
        if self.id in self.outros_nos:
            self.outros_nos.pop(self.id) 


    def monitorar_time(self):
        while(True):
            time.sleep(0.1)
            controle = False

            with self.lock:
                if(self.estado == "seguidor" or self.estado == "candidato"):
                    if(time.time() - self.ultimo_heartbeat > self.limite):
                        self.estado = "candidato"
                        self.termo_atual  = self.termo_atual + 1
                        self.limite = random.randint(2,4)
                        self.ultimo_heartbeat = time.time()
                        print("tempo rodou, eleição começando")
                        controle = True
            if controle:
                self.comecar_eleicao()

    


    def comecar_eleicao(self):
        venceu = False
        with self.lock:
            self.votou_em = self.id
        votos = 1

        for a in self.outros_nos:
            string_conxexao = "PYRO:" + a + "@localhost:" + self.outros_nos[a]
            print(string_conxexao)

            proxy = Pyro5.api.Proxy(string_conxexao)

            try:
                if proxy.pedir_voto(self.id, self.termo_atual):
                    votos = votos + 1

            except:
                print("não exite essa bomba")
        
        with self.lock:
            if votos >= 3  and self.estado == "candidato":
                self.estado = "lider"
                venceu = True

        if venceu:
            ns = Pyro5.api.locate_ns()
            minha_string = "PYRO:" + self.id + "@localhost:" + str(self.porta)
            ns.register("Líder", minha_string)
            thread_heartbeat = threading.Thread(target=self.enviar_heartbeats, daemon=True)
            thread_heartbeat.start()

                
    def enviar_heartbeats():
        pass
        #  próximo passo
                        
    def pedir_voto(self, id_candidato, termo_candidato):
        with self.lock:

            if termo_candidato > self.termo_atual:
                self.termo_atual = termo_candidato
                self.estado = "seguidor"
                self.votou_em = 0 

            if termo_candidato < self.termo_atual:
                return False
            if self.votou_em != 0 and self.votou_em != id_candidato:
                return False
            

            self.votou_em = id_candidato
            self.ultimo_heartbeat = time.time() 
            return True
                        
    def processo_name(self, name):
        return f"Processo {self.id} na porta {self.porta}  {name}"

if __name__ == "__main__":
    
    id = sys.argv[1]
    porta = int(sys.argv[2]) 

    meu_processo = Processo(id, porta)

    daemon = Pyro5.server.Daemon(port=porta)

    uri = daemon.register(meu_processo, objectId=id)

    print(f"Nó Estado: {meu_processo.estado}")
    print(f"URI :{uri}")
    
    thread_timer = threading.Thread(target=meu_processo.monitorar_time, daemon=True)
    thread_timer.start()



    daemon.requestLoop() # bloquenate
# URI: <referncia-objeto>@localhost:port

import Pyro5.api


@Pyro5.api.expose
class Processo(object):
    def __init__(self):
        self.termo =0
        self.uriList = ["",
                        "",
                        "",
                        "",
                        ]
        pass
    def Processo_name(self,name):
        return " hello, {0}".format(name)
    
    def raft_1():
        pass
    def heartbeat():
        pass


    


daemon =Pyro5.server.Daemon()
ns = Pyro5.api.locate_ns()
uri = daemon.register(Processo)
ns.register("example.receba", uri)

print("Capitão fumça pronto para ação")
daemon.requestLoop()







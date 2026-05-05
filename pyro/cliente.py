import Pyro5.api

ns = Pyro5.api.locate_ns()
uri = ns.lookup("Líder")

proxy = Pyro5.api.Proxy(uri)


while True:
    texto  = input("Digite uma raça de hipopótamo")
    try:

        resposta = proxy.receber_comando(texto)
        print(resposta)
    except:
        print("Lider caiu")
        uri = ns.lookup("Líder")
        proxy = Pyro5.api.Proxy(uri)
        resposta = proxy.receber_comando(texto) 
        print(resposta)
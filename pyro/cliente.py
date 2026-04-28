import Pyro5.api

name = input("nome?").strip()

tera = Pyro5.api.Proxy("PYRONAME:example.receba")
print(tera.horus_name(name))

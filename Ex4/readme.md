# Extrutura mesagem:

## ENTRE REST
Feito para ler o json e dar pop na assinatura.
```json
    mensagem = {
        item:item,
        categoria:categoria,
        voto:    voto,
        assinatura : assinatura,
        }
```

## ENTRE RABBITMQ:
```json
    mensagem = {
        mensagem: mensagem,
        assinatura: assinatura
    }
```
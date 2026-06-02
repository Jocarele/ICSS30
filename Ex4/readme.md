# Trabalho Prático: Promoções 2026 - Sistemas Distribuídos

**Instituição:** Universidade Tecnológica Federal do Paraná (UTFPR) - Campus Curitiba
**Disciplina:** Sistemas Distribuídos
**Professora:** Ana Cristina Barreiras Kochem Vendramin

## Autores
* **João Lucas Marques Camilo** 
* **João Pedro dos Reis** 

---

## 1. Objetivo do Sistema
Desenvolver um sistema distribuído baseado em microsserviços para o gerenciamento e a divulgação de promoções de produtos.

## 2. Arquitetura e Comunicação
* **Arquitetura Orientada a Eventos (EDA):** A comunicação ocorre exclusivamente através de eventos publicados e consumidos em um broker **RabbitMQ**.
* **Desacoplamento Total:** Cada microsserviço atua de forma independente. É estritamente proibido realizar chamadas diretas entre os microsserviços.
* **Segurança e Validação:** Utilização de **Criptografia de Chave Assimétrica**. Todo evento publicado deve conter um hash do seu conteúdo e uma assinatura digital gerada com a chave privada do produtor. Os consumidores devem validar essa assinatura usando a chave pública correspondente antes de processar qualquer mensagem.

## 3. Estrutura dos Microsserviços

### 3.1. Microsserviço Gateway
* **Responsabilidade:** Ponto de entrada do sistema. Interage com os usuários via terminal, convertendo ações em eventos.
* **Ações Permitidas:** Cadastrar promoções, listar promoções validadas e votar.
* **Eventos:** Publica `promocao.recebida` e `promocao.voto`. Consome `promocao.publicada` para manter a lista local atualizada.

### 3.2. Microsserviço Promoção
* **Responsabilidade:** Gerenciamento central das promoções.
* **Fluxo:** Recebe novas promoções, valida a assinatura digital para garantir integridade e registra no sistema.
* **Eventos:** Consome `promocao.recebida` e publica `promocao.publicada`.

### 3.3. Microsserviço Ranking
* **Responsabilidade:** Processamento dos votos positivos e negativos associados às promoções.
* **Fluxo:** Calcula o *score* de popularidade. Se o score ultrapassar um limite pré-definido, a promoção é classificada como destaque (*hot deal*).
* **Eventos:** Consome `promocao.voto` e publica `promocao.destaque`.

### 3.4. Microsserviço Notificação
* **Responsabilidade:** Distribuir notificações sobre promoções para os clientes inscritos.
* **Fluxo:** Identifica a categoria da promoção validada ou destacada e envia o alerta correspondente. Para destaques, inclui a flag "hot deal".
* **Eventos:** Consome `promocao.publicada` e `promocao.destaque`. Publica `promocao.categoriaX`.

## 4. Processos Cliente
* O usuário define as categorias de interesse (podendo ser configurado via *hard code*) e passa a consumir as notificações do RabbitMQ correspondentes às suas escolhas (ex: `promocao.livro`, `promocao.jogo`, `promocao.destaque`).
* Utiliza *routing keys* hierárquicas e *bindings* em uma exchange do tipo `direct` ou `topic`.
* As notificações recebidas devem ser exibidas de forma legível no terminal.

# SGB — Sistema de Gestão Bancária

Trabalho Prático Final (TPF) — Universidade do Mindelo
Curso: Engenharia Informática e Sistemas Computacionais
Disciplina: Bases de Dados

Aplicação web (Flask) para gestão de clientes, colaboradores, departamentos
e contas bancárias, com persistência híbrida:

- **MySQL** (relacional) — entidades estruturadas: `clientes`,
  `colaboradores`, `departamentos`, `contas`.
- **MongoDB** (NoSQL) — dados de natureza variável e orientados a eventos:
  - `transacoes` / `auditoria` — histórico de operações (logs)
  - `notificacoes` — alertas automáticos gerados pelo sistema (saldo
    baixo, movimentos elevados, novas contas, levantamentos recusados)

## Funcionalidade NoSQL desta fase: Notificações do Sistema

Sempre que ocorre uma operação bancária relevante, a aplicação avalia
regras de negócio simples e, se aplicável, cria automaticamente um
documento na coleção `notificacoes` do MongoDB:

| Evento | Condição | Nível |
|---|---|---|
| Conta criada | sempre | info |
| Movimento elevado | depósito/levantamento ≥ 50.000 CVE | aviso |
| Saldo baixo | saldo após operação < 1.000 CVE | crítico |
| Levantamento recusado | valor pedido > saldo disponível | aviso |

Cada documento tem um campo `contexto` de estrutura livre, que varia de
acordo com o tipo de notificação — exatamente o tipo de cenário em que o
MongoDB tem vantagem sobre uma tabela relacional rígida, pois não exige
um esquema fixo de colunas para guardar dados heterogéneos.

As notificações são visíveis:
- num sino na barra superior, com contador de não lidas (em todas as páginas);
- numa página dedicada `/notificacoes`, com filtro "Todas" / "Não lidas";
- num resumo das mais recentes na página inicial (Dashboard).

## Estrutura do projeto

```
SGB_interface/
├── interface/
│   ├── app.py              # Rotas Flask (lógica de aplicação)
│   ├── db.py                # Acesso a MySQL e MongoDB
│   ├── .env                 # Credenciais (NÃO versionar)
│   ├── .env.example          # Modelo de configuração
│   ├── static/css/style.css
│   └── templates/            # HTML (Jinja2)
├── requirements.txt
└── .gitignore
```

## Configuração e execução

1. Criar e preencher o ficheiro `.env` (copiar a partir de `.env.example`):
   ```
   MYSQL_HOST=...
   MYSQL_PORT=3306
   MYSQL_USER=...
   MYSQL_PASSWORD=...
   MYSQL_DATABASE=mydb

   MONGO_URI=mongodb://localhost:27017/
   MONGO_DATABASE=sgb_logs
   ```

2. Instalar dependências:
   ```
   pip install -r requirements.txt
   ```

3. Garantir que o MySQL (com as tabelas das fases anteriores) e o MongoDB
   estão acessíveis com os parâmetros definidos no `.env`.

4. Executar a aplicação:
   ```
   cd interface
   python app.py
   ```

5. Abrir `http://localhost:5000` no browser.

## Autores

Éder Évora · Élvin Pires

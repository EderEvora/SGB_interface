"""
db.py — Camada de acesso aos dados do SGB (Sistema de Gestão Bancária)

Este módulo centraliza:
  - a ligação à base de dados relacional MySQL (entidades principais:
    clientes, colaboradores, departamentos, contas);
  - a ligação à base de dados NoSQL MongoDB, usada para dois fins
    complementares:
      1) "logs"          -> registo de auditoria e histórico de transações
                             (coleções: transacoes, auditoria)
      2) "notificacoes"   -> alertas automáticos do sistema gerados a
                             partir das operações bancárias (saldo baixo,
                             movimentos elevados, novas contas, etc.)

As credenciais de ligação NÃO estão escritas no código: são lidas de
variáveis de ambiente (ficheiro .env), o que evita expor dados sensíveis
no repositório e facilita a configuração em diferentes máquinas/ambientes.
"""

import os
from datetime import datetime

import mysql.connector
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis definidas no ficheiro .env para o ambiente do processo
load_dotenv()


# ─────────────────────────────────────────────
# Conexão MySQL
# ─────────────────────────────────────────────
def conectar_mysql():
    """Abre e devolve uma nova ligação à base de dados relacional MySQL."""
    conexao = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE", "mydb"),
    )
    return conexao


# ─────────────────────────────────────────────
# Conexão MongoDB
# ─────────────────────────────────────────────
def conectar_mongo():
    """Abre e devolve a base de dados MongoDB usada pelo sistema (sgb_logs)."""
    cliente = MongoClient(os.getenv("MONGO_URI"))
    return cliente[os.getenv("MONGO_DATABASE")]


# ─────────────────────────────────────────────
# Registo de logs (auditoria / transações) — MongoDB
# ─────────────────────────────────────────────
def registar_log(colecao: str, operacao: str, dados: dict):
    """
    Regista um documento de log numa coleção MongoDB (ex.: 'transacoes',
    'auditoria'). Cada documento guarda a operação realizada, os dados
    associados e o momento em que ocorreu.
    """
    try:
        db = conectar_mongo()
        documento = {
            "operacao": operacao,
            "dados": dados,
            "timestamp": datetime.now(),
        }
        db[colecao].insert_one(documento)
    except Exception as e:
        print(f"  [Aviso] Não foi possível registar log MongoDB: {e}")


# ─────────────────────────────────────────────
# Notificações do sistema — MongoDB (coleção: notificacoes)
# ─────────────────────────────────────────────
#
# Modelo conceptual do documento "notificacoes":
#
# {
#   "_id": ObjectId,
#   "tipo": "saldo_baixo" | "movimento_elevado" | "conta_criada" |
#           "deposito" | "levantamento" | "sistema",
#   "nivel": "info" | "aviso" | "critico",
#   "titulo": str,
#   "mensagem": str,
#   "cliente_id": int | None,     # referência ao MySQL (não é FK rígida)
#   "conta_id": int | None,       # referência ao MySQL (não é FK rígida)
#   "contexto": { ... },          # dados adicionais livres (schema flexível)
#   "lida": bool,
#   "timestamp": datetime
# }
#
# Esta coleção é o exemplo central de uso do MongoDB nesta fase do projeto:
# cada tipo de notificação pode ter um "contexto" com campos diferentes
# (ex.: saldo atual, valor do movimento, tipo de conta), o que seria pouco
# natural de modelar numa tabela relacional rígida, mas é trivial num
# documento JSON sem esquema fixo.

def criar_notificacao(tipo: str, nivel: str, titulo: str, mensagem: str,
                       cliente_id=None, conta_id=None, contexto=None):
    """Insere uma nova notificação na coleção 'notificacoes' do MongoDB."""
    try:
        db = conectar_mongo()
        documento = {
            "tipo": tipo,
            "nivel": nivel,
            "titulo": titulo,
            "mensagem": mensagem,
            "cliente_id": cliente_id,
            "conta_id": conta_id,
            "contexto": contexto or {},
            "lida": False,
            "timestamp": datetime.now(),
        }
        db["notificacoes"].insert_one(documento)
    except Exception as e:
        print(f"  [Aviso] Não foi possível criar notificação MongoDB: {e}")


def listar_notificacoes(apenas_nao_lidas=False, limite=50):
    """Devolve a lista de notificações, mais recentes primeiro."""
    try:
        db = conectar_mongo()
        filtro = {"lida": False} if apenas_nao_lidas else {}
        documentos = list(
            db["notificacoes"].find(filtro).sort("timestamp", -1).limit(limite)
        )
        for d in documentos:
            d["_id"] = str(d["_id"])
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp_fmt"] = d["timestamp"].strftime("%d/%m/%Y %H:%M")
        return documentos
    except Exception as e:
        print(f"  [Aviso] Não foi possível listar notificações: {e}")
        return []


def contar_notificacoes_nao_lidas():
    """Devolve o número de notificações ainda não lidas."""
    try:
        db = conectar_mongo()
        return db["notificacoes"].count_documents({"lida": False})
    except Exception:
        return 0


def marcar_notificacao_lida(notificacao_id: str):
    """Marca uma notificação específica como lida."""
    try:
        from bson import ObjectId
        db = conectar_mongo()
        db["notificacoes"].update_one(
            {"_id": ObjectId(notificacao_id)},
            {"$set": {"lida": True}},
        )
    except Exception as e:
        print(f"  [Aviso] Não foi possível atualizar notificação: {e}")


def marcar_todas_lidas():
    """Marca todas as notificações pendentes como lidas."""
    try:
        db = conectar_mongo()
        db["notificacoes"].update_many({"lida": False}, {"$set": {"lida": True}})
    except Exception as e:
        print(f"  [Aviso] Não foi possível atualizar notificações: {e}")


def eliminar_notificacao(notificacao_id: str):
    """Elimina uma notificação da coleção."""
    try:
        from bson import ObjectId
        db = conectar_mongo()
        db["notificacoes"].delete_one({"_id": ObjectId(notificacao_id)})
    except Exception as e:
        print(f"  [Aviso] Não foi possível eliminar notificação: {e}")

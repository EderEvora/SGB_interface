
import mysql.connector
from pymongo import MongoClient
from datetime import datetime
 
 
# Conexão MySQL
 
def conectar_mysql():
    conexao = mysql.connector.connect(
        host="172.234.174.181",
        port=3306,
        user="um_cbd_eder",
        password="123UM@cbd#test",
        database="mydb"
    )
    return conexao
 
 
# Conexão MongoDB
 
def conectar_mongo():
    cliente = MongoClient("mongodb://localhost:27017/")
    return cliente["sgb_logs"]
 
 
# Registar log no MongoDB
 
def registar_log(colecao: str, operacao: str, dados: dict):
    try:
        db = conectar_mongo()
        documento = {
            "operacao": operacao,
            "dados": dados,
            "timestamp": datetime.now()
        }
        db[colecao].insert_one(documento)
    except Exception as e:
        print(f"  [Aviso] Não foi possível registar log MongoDB: {e}")
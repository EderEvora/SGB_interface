from flask import Flask, render_template, request, redirect, url_for, flash
from db import (
    conectar_mysql, conectar_mongo, registar_log,
    criar_notificacao, listar_notificacoes, contar_notificacoes_nao_lidas,
    marcar_notificacao_lida, marcar_todas_lidas, eliminar_notificacao,
)
from datetime import datetime

app = Flask(__name__)
app.secret_key = "sgb_secret_key"

# Limiares de negócio usados para gerar notificações automáticas
LIMIAR_SALDO_BAIXO = 1000       # CVE — saldo abaixo disto gera alerta
LIMIAR_MOVIMENTO_ELEVADO = 50000  # CVE — depósito/levantamento acima disto gera alerta


# ─────────────────────────────────────────────
# Disponibiliza o contador de notificações não lidas a TODOS os templates
# (usado no sino de notificações da topbar)
# ─────────────────────────────────────────────
@app.context_processor
def injetar_notificacoes():
    return {"notificacoes_nao_lidas": contar_notificacoes_nao_lidas()}


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@app.route("/")
def dashboard():
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clientes")
    total_clientes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM colaboradores")
    total_colaboradores = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM departamentos")
    total_departamentos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM contas")
    total_contas = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(saldo), 0) FROM contas")
    total_saldo = float(cur.fetchone()[0])
    cur.close()
    conn.close()

    # Últimas transações do MongoDB
    try:
        db = conectar_mongo()
        logs = list(db["transacoes"].find().sort("timestamp", -1).limit(5))
        for l in logs:
            l["_id"] = str(l["_id"])
            if isinstance(l.get("timestamp"), datetime):
                l["timestamp"] = l["timestamp"].strftime("%d/%m/%Y %H:%M")
    except Exception:
        logs = []

    # Últimas notificações do sistema (MongoDB)
    ultimas_notificacoes = listar_notificacoes(limite=5)

    return render_template("dashboard.html",
        total_clientes=total_clientes,
        total_colaboradores=total_colaboradores,
        total_departamentos=total_departamentos,
        total_contas=total_contas,
        total_saldo=total_saldo,
        logs=logs,
        ultimas_notificacoes=ultimas_notificacoes,
    )

# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────
@app.route("/clientes")
def clientes():
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, email FROM clientes ORDER BY id")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("clientes.html", clientes=dados)

@app.route("/clientes/novo", methods=["GET", "POST"])
def cliente_novo():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip()
        if nome and email:
            conn = conectar_mysql()
            cur = conn.cursor()
            cur.execute("INSERT INTO clientes (nome, email) VALUES (%s, %s)", (nome, email))
            conn.commit()
            novo_id = cur.lastrowid
            cur.close()
            conn.close()
            registar_log("auditoria", "criar_cliente", {"id": novo_id, "nome": nome, "email": email})
            flash("Cliente criado com sucesso.", "success")
        else:
            flash("Nome e email são obrigatórios.", "error")
        return redirect(url_for("clientes"))
    return render_template("form_cliente.html", acao="Novo", cliente=None)

@app.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
def cliente_editar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip()
        cur.execute("UPDATE clientes SET nome=%s, email=%s WHERE id=%s", (nome, email, id))
        conn.commit()
        cur.close()
        conn.close()
        registar_log("auditoria", "atualizar_cliente", {"id": id, "nome": nome, "email": email})
        flash("Cliente atualizado.", "success")
        return redirect(url_for("clientes"))
    cur.execute("SELECT id, nome, email FROM clientes WHERE id=%s", (id,))
    cliente = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("form_cliente.html", acao="Editar", cliente=cliente)

@app.route("/clientes/eliminar/<int:id>")
def cliente_eliminar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("DELETE FROM clientes WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    registar_log("auditoria", "eliminar_cliente", {"id": id})
    flash("Cliente eliminado.", "success")
    return redirect(url_for("clientes"))

# ─────────────────────────────────────────────
# COLABORADORES
# ─────────────────────────────────────────────
@app.route("/colaboradores")
def colaboradores():
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, email FROM colaboradores ORDER BY id")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("colaboradores.html", colaboradores=dados)

@app.route("/colaboradores/novo", methods=["GET", "POST"])
def colaborador_novo():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip()
        if nome and email:
            conn = conectar_mysql()
            cur = conn.cursor()
            cur.execute("INSERT INTO colaboradores (nome, email) VALUES (%s, %s)", (nome, email))
            conn.commit()
            novo_id = cur.lastrowid
            cur.close()
            conn.close()
            registar_log("auditoria", "criar_colaborador", {"id": novo_id, "nome": nome, "email": email})
            flash("Colaborador criado com sucesso.", "success")
        else:
            flash("Nome e email são obrigatórios.", "error")
        return redirect(url_for("colaboradores"))
    return render_template("form_colaborador.html", acao="Novo", colaborador=None)

@app.route("/colaboradores/editar/<int:id>", methods=["GET", "POST"])
def colaborador_editar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip()
        cur.execute("UPDATE colaboradores SET nome=%s, email=%s WHERE id=%s", (nome, email, id))
        conn.commit()
        cur.close()
        conn.close()
        registar_log("auditoria", "atualizar_colaborador", {"id": id, "nome": nome, "email": email})
        flash("Colaborador atualizado.", "success")
        return redirect(url_for("colaboradores"))
    cur.execute("SELECT id, nome, email FROM colaboradores WHERE id=%s", (id,))
    colaborador = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("form_colaborador.html", acao="Editar", colaborador=colaborador)

@app.route("/colaboradores/eliminar/<int:id>")
def colaborador_eliminar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("DELETE FROM colaboradores WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    registar_log("auditoria", "eliminar_colaborador", {"id": id})
    flash("Colaborador eliminado.", "success")
    return redirect(url_for("colaboradores"))

# ─────────────────────────────────────────────
# DEPARTAMENTOS
# ─────────────────────────────────────────────
@app.route("/departamentos")
def departamentos():
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("SELECT id, nome FROM departamentos ORDER BY id")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("departamentos.html", departamentos=dados)

@app.route("/departamentos/novo", methods=["GET", "POST"])
def departamento_novo():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        if nome:
            conn = conectar_mysql()
            cur = conn.cursor()
            cur.execute("INSERT INTO departamentos (nome) VALUES (%s)", (nome,))
            conn.commit()
            novo_id = cur.lastrowid
            cur.close()
            conn.close()
            registar_log("auditoria", "criar_departamento", {"id": novo_id, "nome": nome})
            flash("Departamento criado.", "success")
        else:
            flash("O nome é obrigatório.", "error")
        return redirect(url_for("departamentos"))
    return render_template("form_departamento.html", acao="Novo", departamento=None)

@app.route("/departamentos/editar/<int:id>", methods=["GET", "POST"])
def departamento_editar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        cur.execute("UPDATE departamentos SET nome=%s WHERE id=%s", (nome, id))
        conn.commit()
        cur.close()
        conn.close()
        registar_log("auditoria", "atualizar_departamento", {"id": id, "nome": nome})
        flash("Departamento atualizado.", "success")
        return redirect(url_for("departamentos"))
    cur.execute("SELECT id, nome FROM departamentos WHERE id=%s", (id,))
    dep = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("form_departamento.html", acao="Editar", departamento=dep)

@app.route("/departamentos/eliminar/<int:id>")
def departamento_eliminar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("DELETE FROM departamentos WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    registar_log("auditoria", "eliminar_departamento", {"id": id})
    flash("Departamento eliminado.", "success")
    return redirect(url_for("departamentos"))

# ─────────────────────────────────────────────
# CONTAS
# ─────────────────────────────────────────────
@app.route("/contas")
def contas():
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, cl.nome, c.tipo, c.saldo
        FROM contas c
        JOIN clientes cl ON c.cliente_id = cl.id
        ORDER BY c.id
    """)
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("contas.html", contas=dados)

@app.route("/contas/nova", methods=["GET", "POST"])
def conta_nova():
    conn = conectar_mysql()
    cur = conn.cursor()
    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        tipo = request.form["tipo"]
        saldo = float(request.form.get("saldo", 0))
        cur.execute("INSERT INTO contas (cliente_id, tipo, saldo) VALUES (%s, %s, %s)", (cliente_id, tipo, saldo))
        conn.commit()
        novo_id = cur.lastrowid

        # Nome do cliente para personalizar a notificação
        cur.execute("SELECT nome FROM clientes WHERE id=%s", (cliente_id,))
        linha_cliente = cur.fetchone()
        nome_cliente = linha_cliente[0] if linha_cliente else "Cliente"

        cur.close()
        conn.close()

        registar_log("transacoes", "criar_conta", {"conta_id": novo_id, "cliente_id": int(cliente_id), "tipo": tipo, "saldo_inicial": saldo})

        # Notificação automática (MongoDB) — nova conta criada
        criar_notificacao(
            tipo="conta_criada",
            nivel="info",
            titulo="Nova conta aberta",
            mensagem=f"Conta {tipo} criada para {nome_cliente} com saldo inicial de {saldo:,.2f} CVE.",
            cliente_id=int(cliente_id),
            conta_id=novo_id,
            contexto={"tipo_conta": tipo, "saldo_inicial": saldo},
        )

        flash("Conta criada com sucesso.", "success")
        return redirect(url_for("contas"))
    cur.execute("SELECT id, nome FROM clientes ORDER BY nome")
    clientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("form_conta.html", acao="Nova", conta=None, clientes=clientes)


def _gerar_notificacoes_movimento(operacao, conta_id, cliente_nome, cliente_id, valor, saldo_novo):
    """
    Função auxiliar que aplica as regras de negócio do sistema e cria, se
    necessário, notificações automáticas no MongoDB após um depósito ou
    levantamento. Centraliza a lógica para evitar duplicação de código
    entre as rotas de depósito e levantamento.
    """
    # Regra 1: movimento de valor elevado
    if valor >= LIMIAR_MOVIMENTO_ELEVADO:
        criar_notificacao(
            tipo="movimento_elevado",
            nivel="aviso",
            titulo=f"{operacao} de valor elevado",
            mensagem=f"{operacao} de {valor:,.2f} CVE na conta de {cliente_nome} (conta #{conta_id}).",
            cliente_id=cliente_id,
            conta_id=conta_id,
            contexto={"operacao": operacao.lower(), "valor": valor, "saldo_apos": saldo_novo},
        )

    # Regra 2: saldo resultante baixo
    if saldo_novo < LIMIAR_SALDO_BAIXO:
        criar_notificacao(
            tipo="saldo_baixo",
            nivel="critico",
            titulo="Saldo baixo",
            mensagem=f"A conta #{conta_id} de {cliente_nome} ficou com saldo de {saldo_novo:,.2f} CVE.",
            cliente_id=cliente_id,
            conta_id=conta_id,
            contexto={"saldo_atual": saldo_novo},
        )


@app.route("/contas/depositar/<int:id>", methods=["GET", "POST"])
def conta_depositar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    if request.method == "POST":
        valor = float(request.form["valor"])
        if valor > 0:
            cur.execute("UPDATE contas SET saldo = saldo + %s WHERE id = %s", (valor, id))
            conn.commit()
            registar_log("transacoes", "deposito", {"conta_id": id, "valor": valor})

            # Recuperar saldo atualizado + dados do cliente para a notificação
            cur.execute("""
                SELECT c.saldo, cl.id, cl.nome
                FROM contas c JOIN clientes cl ON c.cliente_id = cl.id
                WHERE c.id = %s
            """, (id,))
            saldo_novo, cliente_id, cliente_nome = cur.fetchone()
            saldo_novo = float(saldo_novo)
            _gerar_notificacoes_movimento("Depósito", id, cliente_nome, cliente_id, valor, saldo_novo)

            flash(f"Depósito de {valor:,.2f} CVE realizado.", "success")
        else:
            flash("O valor deve ser positivo.", "error")
        cur.close()
        conn.close()
        return redirect(url_for("contas"))
    cur.execute("SELECT c.id, cl.nome, c.tipo, c.saldo FROM contas c JOIN clientes cl ON c.cliente_id=cl.id WHERE c.id=%s", (id,))
    conta = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("form_transacao.html", operacao="Depositar", conta=conta)

@app.route("/contas/levantar/<int:id>", methods=["GET", "POST"])
def conta_levantar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    if request.method == "POST":
        valor = float(request.form["valor"])
        cur.execute("""
            SELECT c.saldo, cl.id, cl.nome
            FROM contas c JOIN clientes cl ON c.cliente_id = cl.id
            WHERE c.id = %s
        """, (id,))
        saldo_atual, cliente_id, cliente_nome = cur.fetchone()
        saldo_atual = float(saldo_atual)

        if valor <= 0:
            flash("O valor deve ser positivo.", "error")
        elif valor > saldo_atual:
            flash(f"Saldo insuficiente. Saldo atual: {saldo_atual:,.2f} CVE.", "error")
            # Notificação automática — tentativa de levantamento recusada
            criar_notificacao(
                tipo="levantamento_recusado",
                nivel="aviso",
                titulo="Levantamento recusado por saldo insuficiente",
                mensagem=f"Tentativa de levantar {valor:,.2f} CVE da conta #{id} ({cliente_nome}), saldo disponível: {saldo_atual:,.2f} CVE.",
                cliente_id=cliente_id,
                conta_id=id,
                contexto={"valor_pedido": valor, "saldo_disponivel": saldo_atual},
            )
        else:
            cur.execute("UPDATE contas SET saldo = saldo - %s WHERE id = %s", (valor, id))
            conn.commit()
            registar_log("transacoes", "levantamento", {"conta_id": id, "valor": valor})
            saldo_novo = saldo_atual - valor
            _gerar_notificacoes_movimento("Levantamento", id, cliente_nome, cliente_id, valor, saldo_novo)
            flash(f"Levantamento de {valor:,.2f} CVE realizado.", "success")
        cur.close()
        conn.close()
        return redirect(url_for("contas"))
    cur.execute("SELECT c.id, cl.nome, c.tipo, c.saldo FROM contas c JOIN clientes cl ON c.cliente_id=cl.id WHERE c.id=%s", (id,))
    conta = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("form_transacao.html", operacao="Levantar", conta=conta)

@app.route("/contas/eliminar/<int:id>")
def conta_eliminar(id):
    conn = conectar_mysql()
    cur = conn.cursor()
    cur.execute("DELETE FROM contas WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    registar_log("auditoria", "eliminar_conta", {"conta_id": id})
    flash("Conta eliminada.", "success")
    return redirect(url_for("contas"))

# ─────────────────────────────────────────────
# LOGS MONGODB (transações / auditoria)
# ─────────────────────────────────────────────
@app.route("/logs")
def logs():
    colecao = request.args.get("colecao", "transacoes")
    try:
        db = conectar_mongo()
        documentos = list(db[colecao].find().sort("timestamp", -1).limit(50))
        for d in documentos:
            d["_id"] = str(d["_id"])
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].strftime("%d/%m/%Y %H:%M:%S")
        total_t = db["transacoes"].count_documents({})
        total_a = db["auditoria"].count_documents({})
    except Exception:
        documentos = []
        total_t = 0
        total_a = 0
    return render_template("logs.html", documentos=documentos, colecao=colecao,
                           total_transacoes=total_t, total_auditoria=total_a)

# ─────────────────────────────────────────────
# NOTIFICAÇÕES (MongoDB) — funcionalidade NoSQL desta fase
# ─────────────────────────────────────────────
@app.route("/notificacoes")
def notificacoes():
    apenas_nao_lidas = request.args.get("filtro") == "nao_lidas"
    documentos = listar_notificacoes(apenas_nao_lidas=apenas_nao_lidas, limite=100)
    total_nao_lidas = contar_notificacoes_nao_lidas()
    return render_template("notificacoes.html",
                           notificacoes=documentos,
                           total_nao_lidas=total_nao_lidas,
                           filtro="nao_lidas" if apenas_nao_lidas else "todas")

@app.route("/notificacoes/lida/<id>")
def notificacao_lida(id):
    marcar_notificacao_lida(id)
    return redirect(request.referrer or url_for("notificacoes"))

@app.route("/notificacoes/marcar-todas")
def notificacoes_marcar_todas():
    marcar_todas_lidas()
    flash("Todas as notificações foram marcadas como lidas.", "success")
    return redirect(url_for("notificacoes"))

@app.route("/notificacoes/eliminar/<id>")
def notificacao_eliminar(id):
    eliminar_notificacao(id)
    flash("Notificação eliminada.", "success")
    return redirect(url_for("notificacoes"))


if __name__ == "__main__":
    app.run(debug=True)

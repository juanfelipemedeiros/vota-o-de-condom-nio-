import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "votacao.db")


# ---------- Banco de dados ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------- Utilidades ----------
def agora():
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def estado(votacao):
    n = agora()
    if n < votacao["data_inicio"]:
        return "agendada"
    if n > votacao["data_fim"]:
        return "encerrada"
    return "aberta"


def formata(dt):
    return datetime.strptime(dt, "%Y-%m-%dT%H:%M").strftime("%d/%m/%Y %H:%M")


app.jinja_env.globals["estado"] = estado
app.jinja_env.filters["formata"] = formata


@app.before_request
def carrega_usuario():
    uid = session.get("uid")
    g.user = None
    if uid:
        g.user = get_db().execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if g.user is None:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if g.user["perfil"] != "admin":
            abort(403)
        return f(*a, **kw)
    return wrapper


# ---------- Autenticação ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        u = get_db().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if u and check_password_hash(u["senha_hash"], senha):
            session.clear()
            session["uid"] = u["id"]
            return redirect(url_for("index"))
        flash("E-mail ou senha incorretos.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Moradores ----------
@app.route("/")
@login_required
def index():
    votacoes = get_db().execute("SELECT * FROM votacoes ORDER BY data_inicio DESC").fetchall()
    return render_template("index.html", votacoes=votacoes)


@app.route("/votacao/<int:vid>")
@login_required
def votacao(vid):
    db = get_db()
    v = db.execute("SELECT * FROM votacoes WHERE id = ?", (vid,)).fetchone()
    if v is None:
        abort(404)
    opcoes = db.execute("SELECT * FROM opcoes WHERE votacao_id = ?", (vid,)).fetchall()

    # unidades pelas quais o usuário logado está autorizado a votar
    minhas = db.execute(
        """SELECT u.id, u.bloco, u.numero,
                  (SELECT opcao_id FROM votos WHERE votacao_id = ? AND unidade_id = u.id) AS opcao_votada
           FROM autorizacoes_voto a JOIN unidades u ON u.id = a.unidade_id
           WHERE a.usuario_id = ? AND a.ativo = 1 ORDER BY u.bloco, u.numero""",
        (vid, g.user["id"]),
    ).fetchall()

    mostrar_resultado = estado(v) == "encerrada" or g.user["perfil"] == "admin"
    resultado, nominal, participacao = [], [], None
    if mostrar_resultado:
        resultado = db.execute(
            """SELECT o.texto, COUNT(vt.id) AS total FROM opcoes o
               LEFT JOIN votos vt ON vt.opcao_id = o.id
               WHERE o.votacao_id = ? GROUP BY o.id ORDER BY o.id""", (vid,)).fetchall()
        total_un = db.execute("SELECT COUNT(*) FROM unidades").fetchone()[0]
        votaram = db.execute("SELECT COUNT(*) FROM votos WHERE votacao_id = ?", (vid,)).fetchone()[0]
        participacao = (votaram, total_un)
    if g.user["perfil"] == "admin":
        nominal = db.execute(
            """SELECT un.bloco, un.numero, us.nome, o.texto, vt.data_hora
               FROM votos vt JOIN unidades un ON un.id = vt.unidade_id
               JOIN usuarios us ON us.id = vt.usuario_id
               JOIN opcoes o ON o.id = vt.opcao_id
               WHERE vt.votacao_id = ? ORDER BY un.bloco, un.numero""", (vid,)).fetchall()

    return render_template("votacao.html", v=v, opcoes=opcoes, minhas=minhas,
                           resultado=resultado, nominal=nominal, participacao=participacao,
                           mostrar_resultado=mostrar_resultado)


@app.post("/votacao/<int:vid>/votar")
@login_required
def votar(vid):
    db = get_db()
    v = db.execute("SELECT * FROM votacoes WHERE id = ?", (vid,)).fetchone()
    if v is None:
        abort(404)
    destino = redirect(url_for("votacao", vid=vid))

    if estado(v) != "aberta":
        flash("Esta votação não está aberta.")
        return destino

    unidade_id = request.form.get("unidade_id", type=int)
    opcao_id = request.form.get("opcao_id", type=int)

    autorizado = db.execute(
        "SELECT 1 FROM autorizacoes_voto WHERE unidade_id = ? AND usuario_id = ? AND ativo = 1",
        (unidade_id, g.user["id"])).fetchone()
    if not autorizado:
        flash("Você não é o votante autorizado desta unidade.")
        return destino

    opcao_ok = db.execute("SELECT 1 FROM opcoes WHERE id = ? AND votacao_id = ?",
                          (opcao_id, vid)).fetchone()
    if not opcao_ok:
        flash("Escolha uma opção válida.")
        return destino

    try:
        db.execute("INSERT INTO votos (votacao_id, unidade_id, usuario_id, opcao_id) VALUES (?,?,?,?)",
                   (vid, unidade_id, g.user["id"], opcao_id))
        db.commit()
        flash("Voto registrado.")
    except sqlite3.IntegrityError:
        flash("Esta unidade já votou nesta votação.")
    return destino


# ---------- Administração (síndico) ----------
@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    return render_template(
        "admin.html",
        usuarios=db.execute("SELECT * FROM usuarios ORDER BY nome").fetchall(),
        unidades=db.execute("SELECT * FROM unidades ORDER BY bloco, numero").fetchall(),
        votantes=db.execute(
            """SELECT un.bloco, un.numero, us.nome, a.tipo,
                      (SELECT nome FROM usuarios WHERE id = a.indicado_por) AS indicado_por
               FROM autorizacoes_voto a
               JOIN unidades un ON un.id = a.unidade_id
               JOIN usuarios us ON us.id = a.usuario_id
               WHERE a.ativo = 1 ORDER BY un.bloco, un.numero""").fetchall(),
    )


def tenta(db, sql, params, ok_msg):
    try:
        db.execute(sql, params)
        db.commit()
        flash(ok_msg)
    except sqlite3.IntegrityError:
        db.rollback()
        flash("Não foi possível salvar: dado duplicado ou inválido.")


@app.post("/admin/usuario")
@admin_required
def admin_usuario():
    f = request.form
    tenta(get_db(),
          "INSERT INTO usuarios (nome, cpf, email, senha_hash, perfil) VALUES (?,?,?,?,?)",
          (f["nome"].strip(), f["cpf"].strip(), f["email"].strip().lower(),
           generate_password_hash(f["senha"]), f.get("perfil", "votante")),
          "Usuário cadastrado.")
    return redirect(url_for("admin"))


@app.post("/admin/unidade")
@admin_required
def admin_unidade():
    f = request.form
    tenta(get_db(), "INSERT INTO unidades (bloco, numero) VALUES (?,?)",
          (f["bloco"].strip().upper(), f["numero"].strip()), "Unidade cadastrada.")
    return redirect(url_for("admin"))


@app.post("/admin/proprietario")
@admin_required
def admin_proprietario():
    f = request.form
    tenta(get_db(), "INSERT INTO proprietarios (unidade_id, usuario_id) VALUES (?,?)",
          (f["unidade_id"], f["usuario_id"]), "Proprietário vinculado à unidade.")
    return redirect(url_for("admin"))


@app.post("/admin/votante")
@admin_required
def admin_votante():
    """Define o único votante da unidade (proprietário ou representante indicado)."""
    db = get_db()
    unidade_id = request.form.get("unidade_id", type=int)
    usuario_id = request.form.get("usuario_id", type=int)
    indicado_por = request.form.get("indicado_por", type=int)

    eh_dono = db.execute("SELECT 1 FROM proprietarios WHERE unidade_id = ? AND usuario_id = ?",
                         (unidade_id, usuario_id)).fetchone()
    if eh_dono:
        tipo, indicado_por = "proprietario", None
    else:
        dono_indicou = indicado_por and db.execute(
            "SELECT 1 FROM proprietarios WHERE unidade_id = ? AND usuario_id = ?",
            (unidade_id, indicado_por)).fetchone()
        if not dono_indicou:
            flash("Representante precisa ser indicado por um proprietário da unidade.")
            return redirect(url_for("admin"))
        tipo = "representante"

    try:
        db.execute("UPDATE autorizacoes_voto SET ativo = 0, data_fim = date('now') "
                   "WHERE unidade_id = ? AND ativo = 1", (unidade_id,))
        db.execute("INSERT INTO autorizacoes_voto (unidade_id, usuario_id, tipo, indicado_por) "
                   "VALUES (?,?,?,?)", (unidade_id, usuario_id, tipo, indicado_por))
        db.commit()
        flash("Votante da unidade atualizado.")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("Não foi possível atualizar o votante.")
    return redirect(url_for("admin"))


@app.route("/admin/votacao/nova", methods=["GET", "POST"])
@admin_required
def nova_votacao():
    if request.method == "POST":
        f = request.form
        opcoes = [o.strip() for o in f.get("opcoes", "").splitlines() if o.strip()]
        if len(opcoes) < 2:
            flash("Informe pelo menos duas opções, uma por linha.")
            return render_template("nova_votacao.html")
        if f["data_fim"] <= f["data_inicio"]:
            flash("A data de encerramento deve ser depois da data de início.")
            return render_template("nova_votacao.html")
        db = get_db()
        cur = db.execute("INSERT INTO votacoes (titulo, descricao, data_inicio, data_fim) VALUES (?,?,?,?)",
                         (f["titulo"].strip(), f.get("descricao", "").strip(),
                          f["data_inicio"], f["data_fim"]))
        db.executemany("INSERT INTO opcoes (votacao_id, texto) VALUES (?,?)",
                       [(cur.lastrowid, o) for o in opcoes])
        db.commit()
        flash("Votação criada.")
        return redirect(url_for("votacao", vid=cur.lastrowid))
    return render_template("nova_votacao.html")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("Banco não encontrado. Rode primeiro:  python init_db.py --demo")
    app.run(debug=True)

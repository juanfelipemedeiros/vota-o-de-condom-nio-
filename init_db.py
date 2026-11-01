"""Cria o banco de dados. Use:  python init_db.py [--demo]"""
import os
import sqlite3
import sys
from werkzeug.security import generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "votacao.db")


def main(demo=False):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())

    db.execute(
        "INSERT INTO usuarios (nome, cpf, email, senha_hash, perfil) VALUES (?,?,?,?,?)",
        ("Síndico", "00000000000", "admin@condominio.com",
         generate_password_hash("admin123"), "admin"),
    )

    if demo:
        for i, (nome, cpf) in enumerate(
            [("Ana Souza", "11111111111"), ("Bruno Lima", "22222222222"),
             ("Carla Dias", "33333333333")], start=1):
            db.execute(
                "INSERT INTO usuarios (nome, cpf, email, senha_hash) VALUES (?,?,?,?)",
                (nome, cpf, f"morador{i}@teste.com", generate_password_hash("123456")),
            )
        for numero in ("101", "102", "103"):
            db.execute("INSERT INTO unidades (bloco, numero) VALUES ('A', ?)", (numero,))
        # usuários 2,3,4 = Ana, Bruno, Carla (o 1 é o síndico)
        for unidade, usuario in ((1, 2), (2, 3), (3, 4)):
            db.execute("INSERT INTO proprietarios VALUES (?,?)", (unidade, usuario))
            db.execute(
                "INSERT INTO autorizacoes_voto (unidade_id, usuario_id, tipo) "
                "VALUES (?,?, 'proprietario')", (unidade, usuario))

    db.commit()
    db.close()
    print("Banco criado em", DB_PATH)
    print("Login do síndico: admin@condominio.com / admin123")
    if demo:
        print("Moradores de teste: morador1@teste.com ... morador3@teste.com / 123456")


if __name__ == "__main__":
    main(demo="--demo" in sys.argv)

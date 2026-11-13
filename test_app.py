"""Testes básicos: python -m unittest -v"""
import os, re, sqlite3, tempfile, threading, unittest
from datetime import datetime, timedelta

import app as A
import init_db


def fmt(d): return d.strftime("%Y-%m-%dT%H:%M")


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        A.DB_PATH = init_db.DB_PATH = os.path.join(self.tmp, "t.db")
        init_db.main(demo=True)
        db = sqlite3.connect(A.DB_PATH)
        agora = datetime.now()
        for ini, fim in ((-1, 1), (-3, -2)):  # votação 1 aberta, 2 encerrada
            c = db.execute("INSERT INTO votacoes (titulo,data_inicio,data_fim) VALUES ('t',?,?)",
                           (fmt(agora + timedelta(hours=ini)), fmt(agora + timedelta(hours=fim))))
            db.executemany("INSERT INTO opcoes (votacao_id,texto) VALUES (?,?)",
                           [(c.lastrowid, "Sim"), (c.lastrowid, "Não")])
        db.commit(); db.close()

    def cliente(self, email, senha="123456"):
        c = A.app.test_client()
        tok = lambda r: re.search(r'name="csrf" value="(\w+)"', r.get_data(as_text=True)).group(1)
        csrf = tok(c.get("/login"))
        c.post("/login", data={"email": email, "senha": senha, "csrf": csrf})
        c.csrf = tok(c.get("/votacao/1" if "admin" not in email else "/admin"))
        return c

    def votar(self, c, vid=1, unidade=1, opcao=1, csrf=None):
        return c.post(f"/votacao/{vid}/votar", follow_redirects=True,
                      data={"unidade_id": unidade, "opcao_id": opcao, "csrf": csrf or c.csrf})

    def total(self):
        db = sqlite3.connect(A.DB_PATH)
        n = db.execute("SELECT COUNT(*) FROM votos").fetchone()[0]; db.close(); return n

    def test_voto_ok_e_duplicado(self):
        c = self.cliente("morador1@teste.com")
        self.assertIn("Voto registrado", self.votar(c).get_data(as_text=True))
        self.assertIn("já votou", self.votar(c, opcao=2).get_data(as_text=True))
        self.assertEqual(self.total(), 1)

    def test_sem_csrf_rejeitado(self):
        c = self.cliente("morador1@teste.com")
        self.assertEqual(c.post("/votacao/1/votar", data={"unidade_id": 1, "opcao_id": 1}).status_code, 400)
        self.assertEqual(self.total(), 0)

    def test_nao_autorizado_e_encerrada(self):
        c = self.cliente("morador1@teste.com")
        self.assertIn("não é o votante", self.votar(c, unidade=2).get_data(as_text=True))
        self.assertIn("não está aberta", self.votar(c, vid=2, opcao=3).get_data(as_text=True))
        self.assertEqual(self.total(), 0)

    def test_morador_nao_acessa_admin(self):
        self.assertEqual(self.cliente("morador1@teste.com").get("/admin").status_code, 403)

    def test_sem_login_redireciona(self):
        c = A.app.test_client()
        self.assertEqual(c.get("/").status_code, 302)

    def test_concorrencia_mesma_unidade(self):
        c = self.cliente("morador1@teste.com")
        ths = [threading.Thread(target=lambda: self.votar(c)) for _ in range(20)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(self.total(), 1)  # 1 voto por apartamento mesmo com 20 cliques simultâneos

    def test_concorrencia_varios_moradores(self):
        cs = [(self.cliente(f"morador{i}@teste.com"), i) for i in (1, 2, 3)]
        ths = [threading.Thread(target=self.votar, args=(c,), kwargs={"unidade": u}) for c, u in cs for _ in range(5)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(self.total(), 3)

    def test_maximo_2_proprietarios(self):
        c = self.cliente("admin@condominio.com", "admin123")
        add = lambda u: c.post("/admin/proprietario", follow_redirects=True,
                               data={"unidade_id": 1, "usuario_id": u, "csrf": c.csrf}).get_data(as_text=True)
        self.assertIn("vinculado", add(3))           # unidade 1 já tinha a Ana -> 2
        self.assertIn("máximo permitido", add(4))    # terceiro é recusado

    def test_editar_votante(self):
        c = self.cliente("admin@condominio.com", "admin123")
        r = c.get("/admin?unidade=1&usuario=2")
        self.assertIn('value="1" selected', r.get_data(as_text=True))  # formulário pré-preenchido
        # troca o votante da unidade 1: Ana(2) -> representante Bruno(3) indicado pela Ana
        r = c.post("/admin/votante", follow_redirects=True,
                   data={"unidade_id": 1, "usuario_id": 3, "indicado_por": 2, "csrf": c.csrf})
        self.assertIn("atualizado", r.get_data(as_text=True))
        # e corrige de volta, sem erro
        r = c.post("/admin/votante", follow_redirects=True,
                   data={"unidade_id": 1, "usuario_id": 2, "csrf": c.csrf})
        self.assertIn("atualizado", r.get_data(as_text=True))

    def test_editar_data_fim(self):
        c = self.cliente("admin@condominio.com", "admin123")
        nova = fmt(datetime.now() + timedelta(days=2))
        r = c.post("/admin/votacao/2/fim", data={"data_fim": nova, "csrf": c.csrf}, follow_redirects=True)
        self.assertIn("atualizada", r.get_data(as_text=True))  # votação encerrada reabre
        r = c.post("/admin/votacao/2/fim", data={"data_fim": "2000-01-01T00:00", "csrf": c.csrf}, follow_redirects=True)
        self.assertIn("depois da data de início", r.get_data(as_text=True))

    def test_encerra_ao_completar(self):
        db = sqlite3.connect(A.DB_PATH)
        db.execute("UPDATE votacoes SET encerra_ao_completar = 1 WHERE id = 1"); db.commit(); db.close()
        for i in (1, 2, 3):
            r = self.votar(self.cliente(f"morador{i}@teste.com"), unidade=i)
        self.assertIn("votação encerrada", r.get_data(as_text=True))
        db = sqlite3.connect(A.DB_PATH)
        self.assertLessEqual(db.execute("SELECT data_fim FROM votacoes WHERE id=1").fetchone()[0], fmt(datetime.now()))


if __name__ == "__main__":
    unittest.main()

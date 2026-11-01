# Votações do condomínio

Sistema web simples de votação para condomínio, feito com Python, Flask e SQLite.

Regras:
- 1 voto por apartamento em cada votação.
- Só vota o proprietário ou um representante indicado por ele.
- Cada apartamento tem um único votante ativo.
- O voto é identificado (fica registrado quem votou).

## Como rodar

```bash
python -m venv venv
# Windows:  venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python init_db.py --demo     # cria o banco com dados de teste
python app.py                # abre em http://127.0.0.1:5000
```

Logins de teste:
- Síndico: admin@condominio.com / admin123
- Moradores: morador1@teste.com, morador2@teste.com, morador3@teste.com / 123456

Para começar sem dados de teste: `python init_db.py` (cria só o síndico).
Em uso real, troque a senha do síndico e defina a variável SECRET_KEY.

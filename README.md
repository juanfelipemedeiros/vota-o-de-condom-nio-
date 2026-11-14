# Votações do condomínio

Sistema web simples de votação para condomínio, feito com Python, Flask e SQLite.

Regras:
- 1 voto por apartamento em cada votação.
- Só vota o proprietário ou um representante indicado por ele.
- Cada apartamento tem um único votante ativo.
- O voto é identificado (fica registrado quem votou).

## Requisitos

- **Python 3.9 ou superior** (https://www.python.org/downloads/). No Windows, marque "Add Python to PATH" na instalação. Confira com `python --version`.
- **Flask 3** (única biblioteca; é instalada pelo `pip`, passo abaixo).
- O banco SQLite já vem com o Python, não precisa instalar nada.
- Um navegador (Chrome, Edge, Firefox...).

## Instalação

Na pasta do projeto, no terminal:

```bash
python -m venv venv
# Windows (PowerShell):  venv\Scripts\activate
# Linux/Mac:             source venv/bin/activate
pip install -r requirements.txt
python init_db.py --demo     # cria o banco com dados de teste
```

Se o PowerShell bloquear o `activate`, rode antes:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

Atenção: `init_db.py` **apaga e recria** o banco. Rode só na primeira vez.

## Como rodar

Com o ambiente virtual ativado (`(venv)` aparece no terminal):

```bash
python app.py
```

Abra http://127.0.0.1:5000 no navegador. Para parar, `Ctrl+C` no terminal.

Logins de teste:
- Síndico: admin@condominio.com / admin123
- Moradores: morador1@teste.com, morador2@teste.com, morador3@teste.com / 123456

Para começar sem dados de teste: `python init_db.py` (cria só o síndico).
Em uso real, troque a senha do síndico e defina a variável SECRET_KEY.

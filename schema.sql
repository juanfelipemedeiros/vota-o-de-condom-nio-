PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    cpf         TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    perfil      TEXT NOT NULL DEFAULT 'votante' CHECK (perfil IN ('admin', 'votante'))
);

CREATE TABLE IF NOT EXISTS unidades (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    bloco   TEXT NOT NULL,
    numero  TEXT NOT NULL,
    UNIQUE (bloco, numero)
);

CREATE TABLE IF NOT EXISTS proprietarios (
    unidade_id  INTEGER NOT NULL REFERENCES unidades(id),
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    PRIMARY KEY (unidade_id, usuario_id)
);

-- Quem está autorizado a votar por cada unidade (proprietário ou representante)
CREATE TABLE IF NOT EXISTS autorizacoes_voto (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    unidade_id    INTEGER NOT NULL REFERENCES unidades(id),
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    tipo          TEXT NOT NULL CHECK (tipo IN ('proprietario', 'representante')),
    indicado_por  INTEGER REFERENCES usuarios(id),
    data_inicio   TEXT NOT NULL DEFAULT CURRENT_DATE,
    data_fim      TEXT,
    ativo         INTEGER NOT NULL DEFAULT 1
);

-- no máximo 1 votante ativo por unidade
CREATE UNIQUE INDEX IF NOT EXISTS uq_votante_ativo
    ON autorizacoes_voto (unidade_id) WHERE ativo = 1;

CREATE TABLE IF NOT EXISTS votacoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo       TEXT NOT NULL,
    descricao    TEXT,
    data_inicio  TEXT NOT NULL,   -- formato YYYY-MM-DDTHH:MM
    data_fim     TEXT NOT NULL,
    CHECK (data_fim > data_inicio)
);

CREATE TABLE IF NOT EXISTS opcoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    votacao_id  INTEGER NOT NULL REFERENCES votacoes(id),
    texto       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS votos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    votacao_id  INTEGER NOT NULL REFERENCES votacoes(id),
    unidade_id  INTEGER NOT NULL REFERENCES unidades(id),
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    opcao_id    INTEGER NOT NULL REFERENCES opcoes(id),
    data_hora   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (votacao_id, unidade_id)   -- 1 voto por apartamento
);

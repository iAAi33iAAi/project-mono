-- Seed data — run against a fresh database to populate demo records.

CREATE TABLE IF NOT EXISTS items (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    quantity    INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO items (name, quantity) VALUES
    ('Widget A', 10),
    ('Widget B', 25),
    ('Widget C', 5);

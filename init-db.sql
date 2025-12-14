CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    assistant_type VARCHAR(50) NOT NULL,  -- e.g., 'LLM', 'NLU', 'ML'
    latency FLOAT NOT NULL,
    error_rate FLOAT DEFAULT 0.0,
    user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE queries (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255),
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users ADD COLUMN rol VARCHAR(50);
ALTER TABLE users ADD COLUMN nivel VARCHAR(50);
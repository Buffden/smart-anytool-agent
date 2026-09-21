CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    budget NUMERIC(12, 2) NOT NULL
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    title TEXT NOT NULL,
    salary NUMERIC(10, 2) NOT NULL,
    manager_id INTEGER REFERENCES employees(id),
    hire_date DATE NOT NULL
);

INSERT INTO departments (name, budget) VALUES
    ('Engineering', 2500000),
    ('Sales', 1200000),
    ('Support', 600000);

INSERT INTO employees (name, department_id, title, salary, manager_id, hire_date) VALUES
    ('Dana Reyes', 1, 'Engineering Manager', 165000, NULL, '2021-03-01'),
    ('Priya Nair', 1, 'Senior Engineer', 140000, 1, '2021-06-15'),
    ('Tom Alvarez', 1, 'Engineer', 110000, 1, '2022-01-10'),
    ('Wei Zhang', 2, 'Sales Manager', 150000, NULL, '2020-11-01'),
    ('Liam O''Connor', 2, 'Account Executive', 95000, 4, '2022-08-01'),
    ('Sara Kim', 3, 'Support Lead', 105000, NULL, '2021-09-01'),
    ('Noah Patel', 3, 'Support Engineer', 80000, 6, '2023-02-20');

-- Read-only role for the agent. In production the password would come from a
-- secret, not be committed -- fine for a local dev seed, change before reuse.
CREATE ROLE agent_readonly WITH LOGIN PASSWORD 'change_me';
GRANT CONNECT ON DATABASE ops_db TO agent_readonly;
GRANT USAGE ON SCHEMA public TO agent_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agent_readonly;

-- ============================================================
-- ChauchaApp QA Seed Data
-- ============================================================
-- Test users for authentication testing (login & register flows).
-- All passwords are hashed with bcrypt via pgcrypto extension.
--
-- Default test password for ALL users: TestPass123!
-- ============================================================

-- Ensure pgcrypto is available for password hashing
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TEST USERS
-- ============================================================
-- 11 test users with varied income types and financial profiles.
-- 2 specific users for login/register test cases:
--   - test_login@chauchaapp.cl  (for login tests)
--   - test_register@chauchaapp.cl (for register flow tests)
-- ============================================================

INSERT INTO "user" (
    first_name, last_name, email, password,
    birth_date, income_type_id, monthly_income, monthly_expenses
) VALUES
    -- User 1: Login test user
    (
        'Test', 'Login',
        'test_login@chauchaapp.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1990-05-15',
        (SELECT income_type_id FROM income_type WHERE name = 'Sueldo fijo'),
        850000.00, 620000.00
    ),
    -- User 2: Family copy of Login test user
    (
        'Test', 'Family',
        'test_family@chauchaapp.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1990-05-15',
        (SELECT income_type_id FROM income_type WHERE name = 'Sueldo fijo'),
        850000.00, 620000.00
    ),
    -- User 3: Register flow test user
    (
        'Test', 'Register',
        'test_register@chauchaapp.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1995-08-22',
        (SELECT income_type_id FROM income_type WHERE name = 'Independiente'),
        1200000.00, 780000.00
    ),
    -- User 4: María González - Salaried
    (
        'María', 'González',
        'maria.gonzalez@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1988-03-10',
        (SELECT income_type_id FROM income_type WHERE name = 'Sueldo fijo'),
        1500000.00, 980000.00
    ),
    -- User 4: Carlos Muñoz - Independent
    (
        'Carlos', 'Muñoz',
        'carlos.munoz@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1992-11-28',
        (SELECT income_type_id FROM income_type WHERE name = 'Independiente'),
        2000000.00, 1350000.00
    ),
    -- User 5: Valentina Rojas - Mixed
    (
        'Valentina', 'Rojas',
        'valentina.rojas@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1985-07-03',
        (SELECT income_type_id FROM income_type WHERE name = 'Mixto'),
        1800000.00, 1100000.00
    ),
    -- User 6: Andrés Silva - Salaried
    (
        'Andrés', 'Silva',
        'andres.silva@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1998-01-20',
        (SELECT income_type_id FROM income_type WHERE name = 'Sueldo fijo'),
        650000.00, 520000.00
    ),
    -- User 7: Camila Torres - Other
    (
        'Camila', 'Torres',
        'camila.torres@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1993-09-14',
        (SELECT income_type_id FROM income_type WHERE name = 'Otro'),
        900000.00, 670000.00
    ),
    -- User 8: Diego Fernández - Salaried
    (
        'Diego', 'Fernández',
        'diego.fernandez@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1987-12-05',
        (SELECT income_type_id FROM income_type WHERE name = 'Sueldo fijo'),
        2500000.00, 1800000.00
    ),
    -- User 9: Javiera López - Independent
    (
        'Javiera', 'López',
        'javiera.lopez@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1996-04-18',
        (SELECT income_type_id FROM income_type WHERE name = 'Independiente'),
        1100000.00, 850000.00
    ),
    -- User 10: Felipe Martínez - Mixed
    (
        'Felipe', 'Martínez',
        'felipe.martinez@test.cl',
        crypt('TestPass123!', gen_salt('bf')),
        '1991-06-30',
        (SELECT income_type_id FROM income_type WHERE name = 'Mixto'),
        3000000.00, 2100000.00
    )
ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- SAMPLE TRANSACTIONS
-- ============================================================
-- Comprehensive transaction data for all QA test users.
-- 27 transactions for test_login@chauchaapp.cl plus 3-5 per other user.
-- Includes monthly, weekly, and one-time frequencies to test frequency logic.
-- ============================================================

-- ============================================================
-- test_login@chauchaapp.cl: 27 transactions
-- ============================================================

-- Monthly Recurring (start January, project across months) — personal (is_group_transaction = FALSE)
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 850000.00, 'Sueldo mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 350000.00, 'Arriendo', '2026-01-05'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Servicios Básicos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 42000.00, 'Luz y Agua', '2026-01-10'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Otros Gastos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 10000.00, 'Seguro celular', '2026-01-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 8500.00, 'Netflix', '2026-01-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 30000.00, 'Seguro salud', '2026-01-25'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

-- Weekly Recurring (start May, active)
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Semanal'), FALSE, 15000.00, 'Supermercado semanal', '2026-05-01'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Semanal'), FALSE, 5000.00, 'Carga Bip semanal', '2026-05-03'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

-- One-time Expenses (cross multiple months)
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 45000.00, 'Súper Líder', '2026-04-05'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 15000.00, 'Carga Bip', '2026-04-06'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 32000.00, 'Farmacia Cruz Verde', '2026-04-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 150000.00, 'Curso Online', '2026-04-22'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 25000.00, 'Cine y cena', '2026-04-25'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Otros Gastos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 60000.00, 'Compra imprevista', '2026-04-28'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 45000.00, 'Mantención hogar', '2026-03-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 60000.00, 'Tag autopista', '2026-03-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 85000.00, 'Dentista', '2026-02-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 55000.00, 'Supermercado Mayo', '2026-05-03'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 15000.00, 'Carga Bip Mayo', '2026-05-07'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 150000.00, 'Consulta Médica', '2026-04-08'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 200000.00, 'Curso Desarrollo Web', '2026-04-12'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 95000.00, 'Cena Aniversario', '2026-04-18'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 70000.00, 'Supermercado Extra Abril', '2026-04-25'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 120000.00, 'Cumpleaños', '2026-05-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 35000.00, 'Mantención auto', '2026-05-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

-- One-time Income
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Freelance'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 200000.00, 'Proyecto freelance', '2026-04-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Inversiones'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 50000.00, 'Dividendos', '2026-03-01'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

-- ============================================================
-- FAMILY GROUP TEST DATA
-- ============================================================

INSERT INTO family_group (name, admin_id)
SELECT 'Grupo Familiar Test', u.user_id
FROM "user" u
WHERE u.email = 'test_login@chauchaapp.cl'
  AND NOT EXISTS (
      SELECT 1
      FROM family_group fg
      WHERE fg.name = 'Grupo Familiar Test'
        AND fg.admin_id = u.user_id
  );

INSERT INTO group_member (user_id, family_group_id)
SELECT u.user_id, fg.family_group_id
FROM "user" u
JOIN family_group fg ON fg.name = 'Grupo Familiar Test'
JOIN "user" admin ON admin.user_id = fg.admin_id
WHERE admin.email = 'test_login@chauchaapp.cl'
  AND u.email IN ('test_login@chauchaapp.cl', 'test_family@chauchaapp.cl', 'maria.gonzalez@test.cl', 'carlos.munoz@test.cl')
  AND NOT EXISTS (
      SELECT 1
      FROM group_member gm
      WHERE gm.user_id = u.user_id
        AND gm.family_group_id = fg.family_group_id
  );


-- Family group QA member personal transactions.
-- Salary transactions stay personal and must never appear in the family group ledger.
WITH family_member_personal_transactions (
    email,
    transaction_type_name,
    category_name,
    frequency_name,
    amount,
    description,
    transaction_date
) AS (
    VALUES
        ('test_family@chauchaapp.cl', 'Ingreso', 'Sueldo', 'Mensual', 850000.00, 'Sueldo mensual', TIMESTAMP WITH TIME ZONE '2026-01-01 09:00:00-03'),
        ('test_family@chauchaapp.cl', 'Ingreso', 'Freelance', 'Única', 135000.00, 'Proyecto personal QA', TIMESTAMP WITH TIME ZONE '2026-04-14 10:10:00-03'),
        ('test_family@chauchaapp.cl', 'Gasto', 'Vivienda', 'Mensual', 320000.00, 'Arriendo personal', TIMESTAMP WITH TIME ZONE '2026-01-05 11:20:00-03'),
        ('test_family@chauchaapp.cl', 'Gasto', 'Alimentación', 'Única', 72000.00, 'Supermercado personal', TIMESTAMP WITH TIME ZONE '2026-04-09 12:30:00-03'),
        ('maria.gonzalez@test.cl', 'Ingreso', 'Sueldo', 'Mensual', 1500000.00, 'Sueldo mensual', TIMESTAMP WITH TIME ZONE '2026-01-01 09:15:00-03'),
        ('maria.gonzalez@test.cl', 'Ingreso', 'Inversiones', 'Única', 85000.00, 'Dividendos personales Maria', TIMESTAMP WITH TIME ZONE '2026-04-17 10:25:00-03'),
        ('maria.gonzalez@test.cl', 'Gasto', 'Alimentación', 'Única', 85000.00, 'Supermercado mensual', TIMESTAMP WITH TIME ZONE '2026-04-03 11:35:00-03'),
        ('maria.gonzalez@test.cl', 'Gasto', 'Salud', 'Única', 45000.00, 'Farmacia', TIMESTAMP WITH TIME ZONE '2026-04-15 12:45:00-03'),
        ('carlos.munoz@test.cl', 'Ingreso', 'Sueldo', 'Mensual', 2000000.00, 'Ingreso mensual', TIMESTAMP WITH TIME ZONE '2026-01-01 09:30:00-03'),
        ('carlos.munoz@test.cl', 'Ingreso', 'Freelance', 'Única', 210000.00, 'Asesoria personal Carlos', TIMESTAMP WITH TIME ZONE '2026-04-19 10:40:00-03'),
        ('carlos.munoz@test.cl', 'Gasto', 'Transporte', 'Única', 120000.00, 'Mantencion vehiculo', TIMESTAMP WITH TIME ZONE '2026-04-08 11:50:00-03'),
        ('carlos.munoz@test.cl', 'Gasto', 'Educación', 'Única', 80000.00, 'Curso marketing', TIMESTAMP WITH TIME ZONE '2026-05-05 13:00:00-03')
)
INSERT INTO "transaction" (
    user_id,
    transaction_type_id,
    transaction_category_id,
    transaction_frequency_id,
    is_group_transaction,
    amount,
    description,
    transaction_date
)
SELECT
    u.user_id,
    tt.transaction_type_id,
    tc.transaction_category_id,
    tf.transaction_frequency_id,
    FALSE,
    fmt.amount,
    fmt.description,
    fmt.transaction_date
FROM family_member_personal_transactions fmt
JOIN "user" u
    ON u.email = fmt.email
JOIN transaction_type tt
    ON tt.name = fmt.transaction_type_name
JOIN transaction_category tc
    ON tc.name = fmt.category_name
JOIN transaction_frequency tf
    ON tf.name = fmt.frequency_name
WHERE NOT EXISTS (
    SELECT 1
    FROM "transaction" existing
    WHERE existing.user_id = u.user_id
      AND existing.description = fmt.description
      AND existing.transaction_date = fmt.transaction_date
);

-- Family group QA member contribution transactions.
WITH family_member_group_transactions (
    email,
    transaction_type_name,
    category_name,
    frequency_name,
    amount,
    description,
    transaction_date
) AS (
    VALUES
        ('test_login@chauchaapp.cl', 'Ingreso', 'Freelance', 'Única', 110000.00, 'Aporte familiar admin', TIMESTAMP WITH TIME ZONE '2026-05-03 09:10:00-03'),
        ('test_login@chauchaapp.cl', 'Ingreso', 'Inversiones', 'Única', 45000.00, 'Retorno fondo familiar admin', TIMESTAMP WITH TIME ZONE '2026-05-13 10:20:00-03'),
        ('test_login@chauchaapp.cl', 'Gasto', 'Servicios Básicos', 'Mensual', 52000.00, 'Internet familiar admin', TIMESTAMP WITH TIME ZONE '2026-01-10 11:30:00-03'),
        ('test_login@chauchaapp.cl', 'Gasto', 'Alimentación', 'Única', 76000.00, 'Compra familiar admin', TIMESTAMP WITH TIME ZONE '2026-05-21 12:40:00-03'),
        ('test_family@chauchaapp.cl', 'Ingreso', 'Freelance', 'Única', 90000.00, 'Aporte familiar test family', TIMESTAMP WITH TIME ZONE '2026-05-02 09:05:00-03'),
        ('test_family@chauchaapp.cl', 'Ingreso', 'Inversiones', 'Única', 35000.00, 'Retorno fondo familiar test', TIMESTAMP WITH TIME ZONE '2026-05-11 10:15:00-03'),
        ('test_family@chauchaapp.cl', 'Gasto', 'Vivienda', 'Mensual', 145000.00, 'Gastos comunes familiares test', TIMESTAMP WITH TIME ZONE '2026-01-12 11:25:00-03'),
        ('test_family@chauchaapp.cl', 'Gasto', 'Entretenimiento', 'Única', 48000.00, 'Actividad familiar test', TIMESTAMP WITH TIME ZONE '2026-05-18 12:35:00-03'),
        ('maria.gonzalez@test.cl', 'Ingreso', 'Freelance', 'Única', 120000.00, 'Aporte familiar Maria', TIMESTAMP WITH TIME ZONE '2026-05-04 09:20:00-03'),
        ('maria.gonzalez@test.cl', 'Ingreso', 'Inversiones', 'Única', 42000.00, 'Retorno fondo familiar Maria', TIMESTAMP WITH TIME ZONE '2026-05-16 10:30:00-03'),
        ('maria.gonzalez@test.cl', 'Gasto', 'Alimentación', 'Única', 92000.00, 'Compra familiar Lider', TIMESTAMP WITH TIME ZONE '2026-05-06 11:40:00-03'),
        ('maria.gonzalez@test.cl', 'Gasto', 'Salud', 'Única', 68000.00, 'Medicamentos familiares', TIMESTAMP WITH TIME ZONE '2026-05-14 12:50:00-03'),
        ('carlos.munoz@test.cl', 'Ingreso', 'Freelance', 'Única', 150000.00, 'Reembolso familiar Carlos', TIMESTAMP WITH TIME ZONE '2026-05-18 09:35:00-03'),
        ('carlos.munoz@test.cl', 'Ingreso', 'Inversiones', 'Única', 60000.00, 'Retorno fondo familiar Carlos', TIMESTAMP WITH TIME ZONE '2026-05-24 10:45:00-03'),
        ('carlos.munoz@test.cl', 'Gasto', 'Transporte', 'Única', 55000.00, 'Bencina viaje familiar', TIMESTAMP WITH TIME ZONE '2026-05-09 11:55:00-03'),
        ('carlos.munoz@test.cl', 'Gasto', 'Vivienda', 'Mensual', 180000.00, 'Aporte gastos comunes', TIMESTAMP WITH TIME ZONE '2026-01-12 13:05:00-03')
)
INSERT INTO "transaction" (
    user_id,
    family_group_id,
    transaction_type_id,
    transaction_category_id,
    transaction_frequency_id,
    is_group_transaction,
    amount,
    description,
    transaction_date
)
SELECT
    u.user_id,
    fg.family_group_id,
    tt.transaction_type_id,
    tc.transaction_category_id,
    tf.transaction_frequency_id,
    TRUE,
    fgt.amount,
    fgt.description,
    fgt.transaction_date
FROM family_member_group_transactions fgt
JOIN "user" u
    ON u.email = fgt.email
JOIN family_group fg
    ON fg.name = 'Grupo Familiar Test'
JOIN "user" admin
    ON admin.user_id = fg.admin_id
JOIN transaction_type tt
    ON tt.name = fgt.transaction_type_name
JOIN transaction_category tc
    ON tc.name = fgt.category_name
JOIN transaction_frequency tf
    ON tf.name = fgt.frequency_name
WHERE admin.email = 'test_login@chauchaapp.cl'
  AND NOT EXISTS (
      SELECT 1
      FROM "transaction" existing
      WHERE existing.user_id = u.user_id
        AND existing.family_group_id = fg.family_group_id
        AND existing.description = fgt.description
        AND existing.transaction_date = fgt.transaction_date
  );

-- valentina.rojas@test.cl - mixed, 1,800,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 1800000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 65000.00, 'Consulta médica', '2026-04-12'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 55000.00, 'Concierto', '2026-05-08'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 95000.00, 'Supermercado Quincena', '2026-04-20'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

-- andres.silva@test.cl - salaried, 650,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 650000.00, 'Sueldo mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'andres.silva@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 25000.00, 'Carga Bip', '2026-04-10'
FROM "user" u WHERE u.email = 'andres.silva@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 35000.00, 'Supermercado', '2026-05-15'
FROM "user" u WHERE u.email = 'andres.silva@test.cl' ON CONFLICT DO NOTHING;

-- camila.torres@test.cl - other, 900,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 900000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 40000.00, 'Streaming anual', '2026-04-05'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 50000.00, 'Supermercado', '2026-05-02'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Otros Gastos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 25000.00, 'Suscripción revista', '2026-03-10'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

-- diego.fernandez@test.cl - salaried, 2,500,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 2500000.00, 'Sueldo mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 350000.00, 'Diplomado', '2026-04-03'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 95000.00, 'Consulta especialista', '2026-05-10'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 180000.00, 'Mantención hogar', '2026-03-15'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 75000.00, 'Tag autopista', '2026-04-22'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

-- javiera.lopez@test.cl - independent, 1,100,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 1100000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'javiera.lopez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 65000.00, 'Supermercado', '2026-04-07'
FROM "user" u WHERE u.email = 'javiera.lopez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 30000.00, 'Salida cultural', '2026-05-12'
FROM "user" u WHERE u.email = 'javiera.lopez@test.cl' ON CONFLICT DO NOTHING;

-- felipe.martinez@test.cl - mixed, 3,000,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), FALSE, 3000000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 500000.00, 'MBA cuota', '2026-04-01'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 400000.00, 'Dividendo extra', '2026-05-05'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 120000.00, 'Seguro salud extra', '2026-03-10'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, is_group_transaction, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), FALSE, 150000.00, 'Supermercado familiar', '2026-04-20'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

-- Add deterministic times to QA transactions that were inserted as date-only values.
WITH ordered_transactions AS (
    SELECT
        transaction_id,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, transaction_date::date
            ORDER BY description, transaction_id
        ) AS row_number
    FROM "transaction"
    WHERE transaction_date::time = TIME '00:00:00'
)
UPDATE "transaction" AS tx
SET transaction_date = tx.transaction_date
    + (((ordered_transactions.row_number % 10) + 8) * INTERVAL '1 hour')
    + (((ordered_transactions.row_number * 7) % 60) * INTERVAL '1 minute')
FROM ordered_transactions
WHERE tx.transaction_id = ordered_transactions.transaction_id;

-- Seed reminder notifications for recurring expense transactions.
INSERT INTO notification (
    user_id,
    notification_type_id,
    notification_status_id,
    message,
    scheduled_date,
    reference_id,
    reference_type
)
SELECT
    tx.user_id,
    (SELECT notification_type_id FROM notification_type WHERE name = 'transaction_reminder'),
    (SELECT notification_status_id FROM notification_status WHERE name = 'pending'),
    'Recordatorio: tienes el gasto ''' || COALESCE(tx.description, 'gasto programado') ||
        ''' programado para el ' || (tx.transaction_date::date)::text || '.',
    (tx.transaction_date::date - INTERVAL '3 days')::date,
    tx.transaction_id,
    'transaction'
FROM "transaction" tx
JOIN transaction_type tt
    ON tt.transaction_type_id = tx.transaction_type_id
JOIN transaction_frequency tf
    ON tf.transaction_frequency_id = tx.transaction_frequency_id
WHERE tt.name = 'Gasto'
  AND tf.name IN ('Mensual', 'Semanal')
  AND NOT EXISTS (
      SELECT 1
      FROM notification existing
      WHERE existing.reference_type = 'transaction'
        AND existing.reference_id = tx.transaction_id
  );

-- ============================================================
-- QA SEED COMPLETE
-- ============================================================
-- Test credentials summary:
--
-- | Email                          | Password      | Income Type  |
-- |--------------------------------|---------------|-------------|
-- | test_login@chauchaapp.cl       | TestPass123!  | salaried    |
-- | test_register@chauchaapp.cl    | TestPass123!  | independent |
-- | maria.gonzalez@test.cl         | TestPass123!  | salaried    |
-- | carlos.munoz@test.cl           | TestPass123!  | independent |
-- | valentina.rojas@test.cl        | TestPass123!  | mixed       |
-- | andres.silva@test.cl           | TestPass123!  | salaried    |
-- | camila.torres@test.cl          | TestPass123!  | other       |
-- | diego.fernandez@test.cl        | TestPass123!  | salaried    |
-- | javiera.lopez@test.cl          | TestPass123!  | independent |
-- | felipe.martinez@test.cl        | TestPass123!  | mixed       |
-- ============================================================

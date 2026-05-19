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

-- Monthly Recurring (start January, project across months)
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 850000.00, 'Sueldo mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 350000.00, 'Arriendo', '2026-01-05'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Servicios Básicos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 42000.00, 'Luz y Agua', '2026-01-10'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Otros Gastos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 10000.00, 'Seguro celular', '2026-01-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 8500.00, 'Netflix', '2026-01-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 30000.00, 'Seguro salud', '2026-01-25'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

-- Weekly Recurring (start May, active)
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Semanal'), 15000.00, 'Supermercado semanal', '2026-05-01'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Semanal'), 5000.00, 'Carga Bip semanal', '2026-05-03'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

-- One-time Expenses (cross multiple months)
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 45000.00, 'Súper Líder', '2026-04-05'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 15000.00, 'Carga Bip', '2026-04-06'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 32000.00, 'Farmacia Cruz Verde', '2026-04-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 150000.00, 'Curso Online', '2026-04-22'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 25000.00, 'Cine y cena', '2026-04-25'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Otros Gastos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 60000.00, 'Compra imprevista', '2026-04-28'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 45000.00, 'Mantención hogar', '2026-03-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 60000.00, 'Tag autopista', '2026-03-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 85000.00, 'Dentista', '2026-02-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 55000.00, 'Supermercado Mayo', '2026-05-03'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 15000.00, 'Carga Bip Mayo', '2026-05-07'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 150000.00, 'Consulta Médica', '2026-04-08'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 200000.00, 'Curso Desarrollo Web', '2026-04-12'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 95000.00, 'Cena Aniversario', '2026-04-18'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 70000.00, 'Supermercado Extra Abril', '2026-04-25'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 120000.00, 'Cumpleaños', '2026-05-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 35000.00, 'Mantención auto', '2026-05-20'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

-- One-time Income
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Freelance'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 200000.00, 'Proyecto freelance', '2026-04-15'
FROM "user" u WHERE u.email = 'test_login@chauchaapp.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Inversiones'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 50000.00, 'Dividendos', '2026-03-01'
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
  AND u.email IN ('test_login@chauchaapp.cl', 'test_family@chauchaapp.cl')
  AND NOT EXISTS (
      SELECT 1
      FROM group_member gm
      WHERE gm.user_id = u.user_id
        AND gm.family_group_id = fg.family_group_id
  );

UPDATE "transaction" t
SET family_group_id = fg.family_group_id
FROM family_group fg
JOIN "user" admin ON admin.user_id = fg.admin_id
WHERE admin.email = 'test_login@chauchaapp.cl'
  AND fg.name = 'Grupo Familiar Test'
  AND t.user_id = admin.user_id
  AND t.family_group_id IS NULL;

INSERT INTO "transaction" (
    user_id,
    family_group_id,
    transaction_type_id,
    transaction_category_id,
    transaction_frequency_id,
    amount,
    description,
    transaction_date
)
SELECT
    family_user.user_id,
    fg.family_group_id,
    t.transaction_type_id,
    t.transaction_category_id,
    t.transaction_frequency_id,
    t.amount,
    t.description,
    CASE
        WHEN t.description = 'Sueldo mensual' THEN TIMESTAMP WITH TIME ZONE '2026-01-02 00:00:00-03'
        ELSE t.transaction_date
    END
FROM "transaction" t
JOIN "user" source_user ON source_user.user_id = t.user_id
JOIN "user" family_user ON family_user.email = 'test_family@chauchaapp.cl'
JOIN family_group fg ON fg.name = 'Grupo Familiar Test'
JOIN "user" admin ON admin.user_id = fg.admin_id
WHERE source_user.email = 'test_login@chauchaapp.cl'
  AND admin.email = 'test_login@chauchaapp.cl'
  AND NOT EXISTS (
      SELECT 1
      FROM "transaction" existing
      WHERE existing.user_id = family_user.user_id
        AND existing.description = t.description
        AND existing.transaction_date = CASE
            WHEN t.description = 'Sueldo mensual' THEN TIMESTAMP WITH TIME ZONE '2026-01-02 00:00:00-03'
            ELSE t.transaction_date
        END
  );

-- ============================================================
-- Other QA Users
-- ============================================================

-- maria.gonzalez@test.cl - salaried, 1,500,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 1500000.00, 'Sueldo mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'maria.gonzalez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 85000.00, 'Supermercado mensual', '2026-04-03'
FROM "user" u WHERE u.email = 'maria.gonzalez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 45000.00, 'Farmacia', '2026-04-15'
FROM "user" u WHERE u.email = 'maria.gonzalez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 35000.00, 'Salida familiar', '2026-05-10'
FROM "user" u WHERE u.email = 'maria.gonzalez@test.cl' ON CONFLICT DO NOTHING;

-- carlos.munoz@test.cl - independent, 2,000,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 2000000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'carlos.munoz@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 120000.00, 'Mantención vehículo', '2026-04-08'
FROM "user" u WHERE u.email = 'carlos.munoz@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 80000.00, 'Curso marketing', '2026-05-05'
FROM "user" u WHERE u.email = 'carlos.munoz@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 250000.00, 'Reparación hogar', '2026-03-20'
FROM "user" u WHERE u.email = 'carlos.munoz@test.cl' ON CONFLICT DO NOTHING;

-- valentina.rojas@test.cl - mixed, 1,800,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 1800000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 65000.00, 'Consulta médica', '2026-04-12'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 55000.00, 'Concierto', '2026-05-08'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 95000.00, 'Supermercado Quincena', '2026-04-20'
FROM "user" u WHERE u.email = 'valentina.rojas@test.cl' ON CONFLICT DO NOTHING;

-- andres.silva@test.cl - salaried, 650,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 650000.00, 'Sueldo mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'andres.silva@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 25000.00, 'Carga Bip', '2026-04-10'
FROM "user" u WHERE u.email = 'andres.silva@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 35000.00, 'Supermercado', '2026-05-15'
FROM "user" u WHERE u.email = 'andres.silva@test.cl' ON CONFLICT DO NOTHING;

-- camila.torres@test.cl - other, 900,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 900000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 40000.00, 'Streaming anual', '2026-04-05'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 50000.00, 'Supermercado', '2026-05-02'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Otros Gastos'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 25000.00, 'Suscripción revista', '2026-03-10'
FROM "user" u WHERE u.email = 'camila.torres@test.cl' ON CONFLICT DO NOTHING;

-- diego.fernandez@test.cl - salaried, 2,500,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 2500000.00, 'Sueldo mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 350000.00, 'Diplomado', '2026-04-03'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 95000.00, 'Consulta especialista', '2026-05-10'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 180000.00, 'Mantención hogar', '2026-03-15'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Transporte'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 75000.00, 'Tag autopista', '2026-04-22'
FROM "user" u WHERE u.email = 'diego.fernandez@test.cl' ON CONFLICT DO NOTHING;

-- javiera.lopez@test.cl - independent, 1,100,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 1100000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'javiera.lopez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 65000.00, 'Supermercado', '2026-04-07'
FROM "user" u WHERE u.email = 'javiera.lopez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Entretenimiento'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 30000.00, 'Salida cultural', '2026-05-12'
FROM "user" u WHERE u.email = 'javiera.lopez@test.cl' ON CONFLICT DO NOTHING;

-- felipe.martinez@test.cl - mixed, 3,000,000
INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Sueldo'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Mensual'), 3000000.00, 'Ingreso mensual', '2026-01-01'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Educación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 500000.00, 'MBA cuota', '2026-04-01'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Vivienda'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 400000.00, 'Dividendo extra', '2026-05-05'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Salud'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 120000.00, 'Seguro salud extra', '2026-03-10'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

INSERT INTO "transaction" (user_id, transaction_type_id, transaction_category_id, transaction_frequency_id, amount, description, transaction_date)
SELECT u.user_id, (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'), (SELECT transaction_category_id FROM transaction_category WHERE name = 'Alimentación'), (SELECT transaction_frequency_id FROM transaction_frequency WHERE name = 'Única'), 150000.00, 'Supermercado familiar', '2026-04-20'
FROM "user" u WHERE u.email = 'felipe.martinez@test.cl' ON CONFLICT DO NOTHING;

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

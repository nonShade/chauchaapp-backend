-- ============================================================
-- ChauchaApp Database Schema
-- Version: 1.0
-- Description: Full DDL for all tables, triggers, and seed data
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TRIGGER FUNCTION: auto-update updated_at on row changes
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- LOOKUP TABLES
-- ============================================================

-- Income Type (salaried, independent, mixed, other)
CREATE TABLE IF NOT EXISTS income_type (
    income_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- Transaction Type (income, expense)
CREATE TABLE IF NOT EXISTS transaction_type (
    transaction_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- Transaction Frequency (one_time, monthly, weekly)
CREATE TABLE IF NOT EXISTS transaction_frequency (
    transaction_frequency_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- Transaction Category (alimentacion, transporte, sueldo, etc.)
CREATE TABLE IF NOT EXISTS transaction_category (
    transaction_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    transaction_type_id UUID REFERENCES transaction_type(transaction_type_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- Notification Type (group_join_request, transaction_reminder, etc.)
CREATE TABLE IF NOT EXISTS notification_type (
    notification_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- Notification Status (pending, sent, read, dismissed)
CREATE TABLE IF NOT EXISTS notification_status (
    notification_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- Educational Topic (ahorro, inversion, presupuesto, etc.)
CREATE TABLE IF NOT EXISTS educational_topic (
    educational_topic_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);


-- ============================================================
-- USER MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS "user" (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    birth_date DATE NOT NULL,
    income_type_id UUID REFERENCES income_type(income_type_id),
    monthly_income DECIMAL(12, 2) NOT NULL,
    monthly_expenses DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);


-- ============================================================
-- GROUPS MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS family_group (
    family_group_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    admin_id UUID NOT NULL REFERENCES "user"(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS group_member (
    group_member_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    family_group_id UUID NOT NULL REFERENCES family_group(family_group_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    UNIQUE(user_id, family_group_id)
);

CREATE TABLE IF NOT EXISTS group_join_request (
    group_join_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_group_id UUID NOT NULL REFERENCES family_group(family_group_id),
    requester_user_id UUID NOT NULL REFERENCES "user"(user_id),
    status VARCHAR(45) NOT NULL DEFAULT 'pending',
    responded_by UUID REFERENCES "user"(user_id),
    responded_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_group_join_request_status
    ON group_join_request(status);


-- ============================================================
-- FINANCIAL DATA MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS bank (
    bank_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bank_name VARCHAR(100) NOT NULL,
    code VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS credit_product (
    credit_product_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bank_id UUID NOT NULL REFERENCES bank(bank_id),
    product_type VARCHAR(100),
    effective_rate DECIMAL(5, 2),
    min_amount DECIMAL(12, 2),
    max_amount DECIMAL(12, 2),
    min_term INT,
    max_term INT,
    min_months INT,
    max_months INT,
    requirements TEXT,
    cae VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);


-- ============================================================
-- TRANSACTIONS MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS "transaction" (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    family_group_id UUID REFERENCES family_group(family_group_id),
    transaction_type_id UUID NOT NULL REFERENCES transaction_type(transaction_type_id),
    transaction_category_id UUID REFERENCES transaction_category(transaction_category_id),
    transaction_frequency_id UUID REFERENCES transaction_frequency(transaction_frequency_id),
    is_group_transaction BOOLEAN NOT NULL DEFAULT FALSE,
    amount DECIMAL(12, 2) NOT NULL,
    description VARCHAR(255),
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_transaction_user ON "transaction"(user_id);
CREATE INDEX IF NOT EXISTS idx_transaction_date ON "transaction"(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transaction_type ON "transaction"(transaction_type_id);


-- ============================================================
-- NEWS MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS news (
    news_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    content_text TEXT NOT NULL,
    source_url VARCHAR(255),
    image_url VARCHAR(255),
    published_at TIMESTAMP,
    impact_level VARCHAR(45),
    affects VARCHAR(100),
    target_audience VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS news_tag (
    tag_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS news_tag_map (
    news_id UUID NOT NULL REFERENCES news(news_id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES news_tag(tag_id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    PRIMARY KEY (news_id, tag_id)
);

CREATE TABLE IF NOT EXISTS personalized_analysis_news (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    news_id UUID NOT NULL REFERENCES news(news_id),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    analysis_text TEXT,
    generated_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS user_interest (
    interest_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    tag_id UUID NOT NULL REFERENCES news_tag(tag_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);


-- ============================================================
-- EDUCATION MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS educational_module (
    educational_module_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT,
    duration INT,
    difficulty VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- M2M pivot: a module can have multiple topics
CREATE TABLE IF NOT EXISTS educational_module_topic (
    educational_module_id UUID NOT NULL REFERENCES educational_module(educational_module_id) ON DELETE CASCADE,
    educational_topic_id UUID NOT NULL REFERENCES educational_topic(educational_topic_id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    PRIMARY KEY (educational_module_id, educational_topic_id)
);

CREATE TABLE IF NOT EXISTS user_progress (
    progress_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    educational_module_id UUID NOT NULL REFERENCES educational_module(educational_module_id),
    status VARCHAR(45) NOT NULL DEFAULT 'not_started',
    progress_percentage INT NOT NULL DEFAULT 0,
    completed_sections JSON NOT NULL DEFAULT '[]'::json,
    quiz_attempts JSON NOT NULL DEFAULT '[]'::json,
    started_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    UNIQUE(user_id, educational_module_id)
);


-- ============================================================
-- QUIZZES MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS quiz (
    quiz_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    educational_module_id UUID NOT NULL REFERENCES educational_module(educational_module_id),
    title VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS question (
    question_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID NOT NULL REFERENCES quiz(quiz_id),
    question_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS answer_option (
    answer_option_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES question(question_id),
    answer_text VARCHAR(255),
    is_correct BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE IF NOT EXISTS quiz_result (
    quiz_result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    quiz_id UUID NOT NULL REFERENCES quiz(quiz_id),
    attempt_number INT,
    correct_answer INT,
    total_questions INT,
    score INT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);


-- ============================================================
-- NOTIFICATIONS MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS notification (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    notification_type_id UUID NOT NULL REFERENCES notification_type(notification_type_id),
    notification_status_id UUID NOT NULL REFERENCES notification_status(notification_status_id),
    message TEXT,
    scheduled_date DATE,
    reference_id UUID,
    reference_type VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_notification_user ON notification(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_status ON notification(notification_status_id);
CREATE INDEX IF NOT EXISTS idx_notification_scheduled ON notification(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_notification_reference
    ON notification(reference_type, reference_id);


-- ============================================================
-- DAILY TIPS MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS daily_tip (
    daily_tip_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    day_of_week INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS idx_daily_tip_active ON daily_tip(is_active);
CREATE INDEX IF NOT EXISTS idx_daily_tip_day_of_week ON daily_tip(day_of_week);
CREATE INDEX IF NOT EXISTS idx_daily_tip_generated_at ON daily_tip(generated_at);


-- ============================================================
-- APPLY updated_at TRIGGERS TO ALL TABLES
-- ============================================================

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'income_type',
            'transaction_type',
            'transaction_frequency',
            'transaction_category',
            'notification_type',
            'notification_status',
            'educational_topic',
            '"user"',
            'family_group',
            'group_member',
            'group_join_request',
            'bank',
            'credit_product',
            '"transaction"',
            'news',
            'news_tag',
            'news_tag_map',
            'personalized_analysis_news',
            'user_interest',
            'educational_module',
            'educational_module_topic',
            'user_progress',
            'quiz',
            'question',
            'answer_option',
            'quiz_result',
            'notification',
            'daily_tip'
        ])
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_updated_at ON %s; '
            'CREATE TRIGGER trg_updated_at BEFORE UPDATE ON %s '
            'FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            tbl, tbl
        );
    END LOOP;
END;
$$;


-- ============================================================
-- SEED LOOKUP TABLES WITH INITIAL VALUES
-- ============================================================

-- Income Types
INSERT INTO income_type (name, description) VALUES
    ('Sueldo fijo', 'Trabajador dependiente con sueldo fijo'),
    ('Independiente', 'Trabajador independiente o freelance'),
    ('Mixto', 'Combinación de ingresos dependientes e independientes'),
    ('Otro', 'Otro tipo de ingreso')
ON CONFLICT (name) DO NOTHING;

-- News Tags / Topics
INSERT INTO news_tag (name, description) VALUES
    ('Sueldo mínimo', 'Cambios en el salario mínimo'),
    ('Combustible', 'Precios bencina/diesel'),
    ('Alimentos', 'IPC y canasta básica'),
    ('Vivienda', 'Arriendos, dividendos, UF'),
    ('Transporte', 'Tarifas y movilidad'),
    ('Servicios básicos', 'Luz, agua, internet'),
    ('Impuestos', 'IVA, retenciones, SII'),
    ('Créditos', 'Tasas y condiciones'),
    ('Ahorro', 'APV, depósitos, fondos'),
    ('Inversiones', 'Bolsa, fondos mutuos')
ON CONFLICT (name) DO NOTHING;

-- Transaction Types
INSERT INTO transaction_type (name, description) VALUES
    ('Ingreso', 'Ingreso de dinero'),
    ('Gasto', 'Gasto de dinero')
ON CONFLICT (name) DO NOTHING;

-- Transaction Frequencies
INSERT INTO transaction_frequency (name, description) VALUES
    ('Única', 'Transacción única, no recurrente'),
    ('Mensual', 'Se repite mensualmente'),
    ('Semanal', 'Se repite semanalmente')
ON CONFLICT (name) DO NOTHING;

-- Transaction Categories (Expenses)
INSERT INTO transaction_category (name, description, transaction_type_id) VALUES
    ('Alimentación', 'Gastos en comida y supermercado',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto')),
    ('Transporte', 'Gastos en transporte público, combustible, etc.',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto')),
    ('Salud', 'Gastos médicos, farmacia, seguros de salud',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto')),
    ('Educación', 'Gastos en educación, cursos, materiales',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto')),
    ('Entretenimiento', 'Gastos en ocio, entretenimiento, suscripciones',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto')),
    ('Vivienda', 'Arriendo, dividendo, mantención del hogar',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto')),
    ('Servicios Básicos', 'Agua, luz, gas, internet, teléfono',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto')),
    ('Otros Gastos', 'Otros gastos no categorizados',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Gasto'))
ON CONFLICT (name) DO NOTHING;

-- Transaction Categories (Income)
INSERT INTO transaction_category (name, description, transaction_type_id) VALUES
    ('Sueldo', 'Sueldo mensual de trabajo dependiente',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso')),
    ('Freelance', 'Ingresos por trabajos independientes',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso')),
    ('Inversiones', 'Retornos de inversiones',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso')),
    ('Otros Ingresos', 'Otros ingresos no categorizados',
        (SELECT transaction_type_id FROM transaction_type WHERE name = 'Ingreso'))
ON CONFLICT (name) DO NOTHING;

-- Notification Types
INSERT INTO notification_type (name, description) VALUES
    ('group_join_request', 'Solicitud de un usuario para unirse a tu grupo familiar'),
    ('group_join_accepted', 'Tu solicitud para unirse a un grupo fue aceptada'),
    ('group_join_rejected', 'Tu solicitud para unirse a un grupo fue rechazada'),
    ('transaction_reminder', 'Recordatorio de una transacción programada'),
    ('system_info', 'Notificación informativa del sistema'),
    ('educational_reminder', 'Recordatorio de progreso en módulo educativo')
ON CONFLICT (name) DO NOTHING;

-- Notification Statuses
INSERT INTO notification_status (name, description) VALUES
    ('pending', 'Notificación pendiente de envío'),
    ('sent', 'Notificación enviada al usuario'),
    ('read', 'Notificación leída por el usuario'),
    ('dismissed', 'Notificación descartada por el usuario')
ON CONFLICT (name) DO NOTHING;

-- Educational Topics
INSERT INTO educational_topic (name, description) VALUES
    ('Ahorro', 'Estrategias y técnicas de ahorro personal'),
    ('Inversión', 'Conceptos de inversión y mercados financieros'),
    ('Presupuesto', 'Planificación y gestión de presupuesto personal'),
    ('Deudas', 'Manejo y estrategias para salir de deudas'),
    ('Impuestos', 'Educación tributaria y declaración de impuestos'),
    ('Seguros', 'Tipos de seguros y protección financiera'),
    ('Jubilación', 'Planificación para la jubilación y AFP'),
    ('Emprendimiento', 'Finanzas para emprendedores')
ON CONFLICT (name) DO NOTHING;


-- ============================================================
-- SCHEMA CREATION COMPLETE
-- ============================================================

-- Migration 002: Populate quiz, question, answer_option from JSON content
-- This script migrates existing educational modules from JSON blob to normalized tables

-- First, let's create a function to parse the JSON and populate tables
DO $$
DECLARE
    module_record RECORD;
    quiz_data JSONB;
    questions JSONB;
    question_record JSONB;
    options JSONB;
    q_id UUID;
    quiz_id UUID;
    option_text TEXT;
    correct_idx INT;
    i INT;
BEGIN
    -- Loop through all educational modules that have content
    FOR module_record IN
        SELECT educational_module_id, title, content
        FROM educational_module
        WHERE content IS NOT NULL
    LOOP
        -- Parse the content JSON
        quiz_data := (module_record.content::JSONB -> 'quiz');

        IF quiz_data IS NULL THEN
            RAISE NOTICE 'Module % has no quiz data, skipping', module_record.title;
            CONTINUE;
        END IF;

        -- Check if quiz already exists for this module
        IF EXISTS (SELECT 1 FROM quiz WHERE educational_module_id = module_record.educational_module_id) THEN
            RAISE NOTICE 'Quiz already exists for module %, skipping', module_record.title;
            CONTINUE;
        END IF;

        -- Create quiz record
        INSERT INTO quiz (quiz_id, educational_module_id, title)
        VALUES (uuid_generate_v4(), module_record.educational_module_id, quiz_data ->> 'title')
        RETURNING quiz_id INTO quiz_id;

        -- Get questions array
        questions := quiz_data -> 'questions';

        IF questions IS NULL THEN
            RAISE NOTICE 'Quiz for module % has no questions', module_record.title;
            CONTINUE;
        END IF;

        -- Loop through questions
        FOR i IN 0..jsonb_array_length(questions) - 1 LOOP
            question_record := questions -> i;

            -- Sanitize correctAnswer
            correct_idx := CASE
                WHEN jsonb_typeof(question_record -> 'correctAnswer') = 'array' THEN
                    (question_record -> 'correctAnswer' ->> 0)::INT
                WHEN jsonb_typeof(question_record -> 'correctAnswer') = 'string' THEN
                    0
                WHEN (question_record -> 'correctAnswer')::TEXT = 'null' THEN
                    0
                ELSE
                    (question_record -> 'correctAnswer')::INT
            END;

            -- Clamp to valid range
            options := question_record -> 'options';
            IF options IS NOT NULL AND jsonb_array_length(options) > 0 THEN
                correct_idx := GREATEST(0, LEAST(correct_idx, jsonb_array_length(options) - 1));
            ELSE
                correct_idx := 0;
            END IF;

            -- Create question record
            INSERT INTO question (question_id, quiz_id, question_text)
            VALUES (uuid_generate_v4(), quiz_id, question_record ->> 'question')
            RETURNING question_id INTO q_id;

            -- Create answer options
            IF options IS NOT NULL THEN
                FOR j IN 0..jsonb_array_length(options) - 1 LOOP
                    option_text := options ->> j;
                    INSERT INTO answer_option (answer_option_id, question_id, answer_text, is_correct)
                    VALUES (uuid_generate_v4(), q_id, option_text, j = correct_idx);
                END LOOP;
            END IF;
        END LOOP;

        RAISE NOTICE 'Migrated quiz for module: %', module_record.title;
    END LOOP;

    RAISE NOTICE 'Migration 002 complete: quiz tables populated';
END $$;

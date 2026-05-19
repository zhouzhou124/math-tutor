-- Run this ONCE in Supabase SQL Editor: https://app.supabase.com → your project → SQL Editor
-- This creates the tables for Math Tutor's persistent cloud storage.

-- 1. Error records (mistakes notebook + grading history)
CREATE TABLE IF NOT EXISTS error_records (
    id BIGSERIAL PRIMARY KEY,
    record_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    question TEXT DEFAULT '',
    student_answer TEXT DEFAULT '',
    standard_answer TEXT DEFAULT '',
    question_type TEXT DEFAULT '',
    knowledge_point TEXT DEFAULT '',
    difficulty TEXT DEFAULT '中等',
    score TEXT DEFAULT '0',
    max_score TEXT DEFAULT '10',
    error_type TEXT DEFAULT '',
    root_cause TEXT DEFAULT '',
    engine TEXT DEFAULT '',
    comment TEXT DEFAULT '',
    extra_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_er_user ON error_records(user_id);
CREATE INDEX IF NOT EXISTS idx_er_date ON error_records(date DESC);
CREATE INDEX IF NOT EXISTS idx_er_kp ON error_records(knowledge_point);
CREATE INDEX IF NOT EXISTS idx_er_record_id ON error_records(record_id);

-- 2. User profiles (learning progress)
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    profile_json TEXT DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Learning stats (dashboard data)
CREATE TABLE IF NOT EXISTS learning_stats (
    user_id TEXT PRIMARY KEY,
    total_questions INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    overall_accuracy REAL DEFAULT 0.0,
    current_level TEXT DEFAULT '强化阶段',
    streak_days INTEGER DEFAULT 0,
    last_study_date TEXT DEFAULT '',
    stats_json TEXT DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

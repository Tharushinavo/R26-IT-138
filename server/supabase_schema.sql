-- Supabase schema for the Cognitive Skill Profiling System
-- Run this once in the Supabase SQL editor.
-- Full schema per Implementation Plan Sections 8.2–8.7

-- ══════════════════════════════════════════════════════════
-- Table 1: user_profiles (linked to Supabase Auth)
-- ══════════════════════════════════════════════════════════
create table if not exists user_profiles (
    id          uuid primary key references auth.users(id),
    full_name   text,
    role        text check (role in ('student', 'teacher', 'parent', 'admin')),
    grade       text,
    created_at  timestamptz default now()
);

-- ══════════════════════════════════════════════════════════
-- Table 2: students
-- ══════════════════════════════════════════════════════════
create table if not exists students (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid references auth.users(id),
    student_code text unique,
    name         text,
    age          int,
    grade        text,
    teacher_id   uuid references auth.users(id),
    created_at   timestamptz default now()
);

create index if not exists idx_students_user     on students(user_id);
create index if not exists idx_students_teacher  on students(teacher_id);

-- ══════════════════════════════════════════════════════════
-- Table 3: questions
-- ══════════════════════════════════════════════════════════
create table if not exists questions (
    id             uuid primary key default gen_random_uuid(),
    question_code  text unique,
    topic          text not null,
    difficulty     text not null check (difficulty in ('Easy', 'Medium', 'Hard')),
    question_text  text not null,
    correct_answer text not null,
    options        jsonb,
    created_at     timestamptz default now()
);

create index if not exists idx_questions_topic      on questions(topic);
create index if not exists idx_questions_difficulty  on questions(difficulty);

-- ══════════════════════════════════════════════════════════
-- Table 4: interactions (raw interaction records)
-- ══════════════════════════════════════════════════════════
create table if not exists interactions (
    id                    uuid primary key default gen_random_uuid(),
    student_id            text not null,
    session_id            text not null,
    question_id           text not null,
    topic                 text not null default 'Addition',
    difficulty            text not null default 'Easy',
    response_time_sec     numeric not null,
    attempts              int not null default 1,
    is_correct            boolean not null,
    hint_used             boolean not null default false,
    click_count           int not null default 0,
    session_time_sec      numeric not null default 0,
    time_between_actions  numeric not null default 0,
    error_type            text not null default 'none',
    expected_answer       text,
    given_answer          text,
    created_at            timestamptz not null default now()
);

create index if not exists idx_interactions_student  on interactions(student_id);
create index if not exists idx_interactions_session  on interactions(session_id);
create index if not exists idx_interactions_created  on interactions(created_at);

-- ══════════════════════════════════════════════════════════
-- Table 5: extracted_features (optional, for research)
-- ══════════════════════════════════════════════════════════
create table if not exists extracted_features (
    id                    uuid primary key default gen_random_uuid(),
    student_id            text not null,
    interaction_id        uuid references interactions(id),
    accuracy_rate         numeric,
    average_response_time numeric,
    attempt_frequency     numeric,
    hint_usage_rate       numeric,
    error_frequency       numeric,
    engagement_score      numeric,
    created_at            timestamptz default now()
);

create index if not exists idx_features_student on extracted_features(student_id);

-- ══════════════════════════════════════════════════════════
-- Table 6: cognitive_profiles
-- ══════════════════════════════════════════════════════════
create table if not exists cognitive_profiles (
    id                       uuid primary key default gen_random_uuid(),
    student_id               text not null,
    session_id               text,
    memory_level             text not null check (memory_level in ('low','medium','high')),
    attention_level          text not null check (attention_level in ('low','medium','high')),
    number_sense_level       text not null check (number_sense_level in ('low','medium','high')),
    processing_speed_level   text not null check (processing_speed_level in ('Slow','Moderate','Fast')),
    confidence_score         numeric,
    recommendation           text,
    model_version            text,
    features                 jsonb not null,
    generated_at             timestamptz not null default now()
);

create index if not exists idx_profiles_student   on cognitive_profiles(student_id);
create index if not exists idx_profiles_generated on cognitive_profiles(generated_at desc);

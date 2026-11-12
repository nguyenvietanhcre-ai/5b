CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    account_code TEXT NOT NULL UNIQUE,
    login_identifier TEXT NOT NULL UNIQUE,
    auth_subject TEXT UNIQUE,
    birth_year INTEGER NOT NULL CHECK (birth_year BETWEEN 1900 AND 2100),
    invite_code TEXT NOT NULL UNIQUE,
    vip_expires_at TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended'))
);

CREATE TRIGGER accounts_birth_year_immutable
BEFORE UPDATE OF birth_year ON accounts
WHEN NEW.birth_year <> OLD.birth_year
BEGIN
    SELECT RAISE(ABORT, 'Birth year is immutable');
END;

CREATE TABLE grades (
    id INTEGER PRIMARY KEY CHECK (id BETWEEN 1 AND 5),
    name TEXT NOT NULL UNIQUE
);
INSERT INTO grades VALUES (1, 'Khối 1'), (2, 'Khối 2'), (3, 'Khối 3'), (4, 'Khối 4'), (5, 'Khối 5');

CREATE TABLE academic_years (
    id INTEGER PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    grade_effective_from TEXT NOT NULL,
    instruction_starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    CHECK (grade_effective_from < instruction_starts_on AND instruction_starts_on < ends_on)
);

ALTER TABLE students ADD COLUMN account_id INTEGER REFERENCES accounts(id);
CREATE UNIQUE INDEX students_account ON students(account_id);

CREATE TABLE student_grades (
    student_id INTEGER NOT NULL REFERENCES students(id),
    academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    PRIMARY KEY (student_id, academic_year_id)
);
CREATE INDEX student_grades_scope ON student_grades(academic_year_id, grade_id, student_id);

CREATE TABLE teachers (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    birth_year INTEGER,
    bio TEXT NOT NULL DEFAULT ''
);

CREATE TABLE online_classes (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
    name TEXT NOT NULL,
    meeting_ref TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed'))
);
CREATE INDEX online_classes_scope ON online_classes(academic_year_id, grade_id);
CREATE INDEX online_classes_teacher ON online_classes(teacher_id);

CREATE TABLE class_enrollments (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    class_id INTEGER NOT NULL REFERENCES online_classes(id),
    joined_at TEXT NOT NULL,
    left_at TEXT,
    CHECK (left_at IS NULL OR left_at >= joined_at)
);
CREATE UNIQUE INDEX class_enrollments_current_student ON class_enrollments(student_id) WHERE left_at IS NULL;
CREATE INDEX class_enrollments_roster ON class_enrollments(class_id, left_at, student_id);

CREATE TABLE access_entitlements (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    enrollment_id INTEGER REFERENCES class_enrollments(id),
    kind TEXT NOT NULL CHECK (kind = 'internal'),
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    CHECK (ends_at IS NULL OR ends_at > starts_at)
);
CREATE INDEX access_entitlements_account ON access_entitlements(account_id, kind, starts_at, ends_at);
CREATE INDEX access_entitlements_enrollment ON access_entitlements(enrollment_id);

CREATE TABLE vip_purchases (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    payment_ref TEXT NOT NULL UNIQUE,
    months INTEGER NOT NULL CHECK (months BETWEEN 1 AND 120),
    confirmed_at TEXT NOT NULL CHECK (
        strftime('%Y-%m-%dT%H:%M:%SZ', confirmed_at) IS NOT NULL
        AND strftime('%Y-%m-%dT%H:%M:%SZ', confirmed_at) = confirmed_at
    )
);
CREATE INDEX vip_purchases_account ON vip_purchases(account_id, id);

CREATE TABLE account_referrals (
    id INTEGER PRIMARY KEY,
    inviter_account_id INTEGER NOT NULL REFERENCES accounts(id),
    invitee_account_id INTEGER NOT NULL UNIQUE REFERENCES accounts(id),
    invite_code TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    first_vip_upgraded_at TEXT,
    qualifying_purchase_id INTEGER UNIQUE REFERENCES vip_purchases(id),
    reward_status TEXT NOT NULL DEFAULT 'pending' CHECK (reward_status IN ('pending', 'granted', 'customer_service')),
    reward_granted_at TEXT,
    reward_vip_expires_at TEXT,
    UNIQUE (inviter_account_id, invitee_account_id),
    CHECK (inviter_account_id <> invitee_account_id),
    CHECK (
        (reward_status = 'pending' AND qualifying_purchase_id IS NULL AND first_vip_upgraded_at IS NULL AND reward_granted_at IS NULL)
        OR (reward_status = 'granted' AND qualifying_purchase_id IS NOT NULL AND first_vip_upgraded_at IS NOT NULL AND reward_granted_at IS NOT NULL)
        OR (reward_status = 'customer_service' AND qualifying_purchase_id IS NOT NULL AND first_vip_upgraded_at IS NOT NULL AND reward_granted_at IS NULL)
    )
);
CREATE INDEX account_referrals_inviter ON account_referrals(inviter_account_id, registered_at, id);

CREATE TRIGGER account_referrals_registration
BEFORE INSERT ON account_referrals
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM accounts WHERE id = NEW.inviter_account_id AND invite_code = NEW.invite_code
    ) THEN RAISE(ABORT, 'Invite code does not match inviter') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM vip_purchases WHERE account_id = NEW.invitee_account_id
    ) THEN RAISE(ABORT, 'Referral must be attached before the first VIP purchase') END;
END;

CREATE TRIGGER account_referrals_attribution_immutable
BEFORE UPDATE OF inviter_account_id, invitee_account_id, invite_code, registered_at ON account_referrals
BEGIN
    SELECT RAISE(ABORT, 'Referral attribution is immutable');
END;

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    referral_id INTEGER UNIQUE REFERENCES account_referrals(id),
    kind TEXT NOT NULL CHECK (kind IN ('referral_vip_reward', 'referral_contact_support')),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT
);
CREATE INDEX notifications_inbox ON notifications(account_id, created_at DESC, id DESC);
CREATE INDEX notifications_unread ON notifications(account_id, id) WHERE read_at IS NULL;

CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    title TEXT NOT NULL,
    theory_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(theory_json)),
    UNIQUE (id, grade_id)
);
CREATE INDEX topics_grade ON topics(grade_id, id);

CREATE TABLE lessons (
    id INTEGER PRIMARY KEY,
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    topic_id INTEGER,
    kind TEXT NOT NULL CHECK (kind IN ('weekly', 'topic')),
    week_no INTEGER CHECK (week_no BETWEEN 1 AND 53),
    title TEXT NOT NULL,
    body_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(body_json)),
    video_ref TEXT,
    FOREIGN KEY (topic_id, grade_id) REFERENCES topics(id, grade_id),
    CHECK ((kind = 'weekly' AND week_no IS NOT NULL) OR (kind = 'topic' AND topic_id IS NOT NULL))
);
CREATE INDEX lessons_schedule ON lessons(grade_id, kind, week_no, id);
CREATE INDEX lessons_topic ON lessons(topic_id, id);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY,
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    topic_id INTEGER NOT NULL,
    question_code TEXT NOT NULL UNIQUE,
    FOREIGN KEY (topic_id, grade_id) REFERENCES topics(id, grade_id)
);
CREATE INDEX questions_pool ON questions(grade_id, topic_id, id);

CREATE TABLE question_versions (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 4),
    curriculum_week INTEGER CHECK (curriculum_week BETWEEN 1 AND 53),
    prompt_json TEXT NOT NULL CHECK (json_valid(prompt_json)),
    grading_rule_json TEXT NOT NULL CHECK (json_valid(grading_rule_json)),
    solution_steps_json TEXT NOT NULL CHECK (json_valid(solution_steps_json)),
    hints_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(hints_json)),
    status TEXT NOT NULL CHECK (status IN ('draft', 'published', 'retired')),
    UNIQUE (question_id, revision),
    UNIQUE (id, question_id)
);
CREATE INDEX question_versions_selection ON question_versions(question_id, status, difficulty, curriculum_week, id);

CREATE TABLE media_assets (
    id INTEGER PRIMARY KEY,
    storage_key TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    byte_size INTEGER NOT NULL CHECK (byte_size > 0),
    alt_text TEXT NOT NULL
);

CREATE TABLE question_assets (
    question_version_id INTEGER NOT NULL REFERENCES question_versions(id),
    asset_id INTEGER NOT NULL REFERENCES media_assets(id),
    PRIMARY KEY (question_version_id, asset_id)
);
CREATE INDEX question_assets_asset ON question_assets(asset_id);

CREATE TABLE lesson_assets (
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    asset_id INTEGER NOT NULL REFERENCES media_assets(id),
    PRIMARY KEY (lesson_id, asset_id)
);
CREATE INDEX lesson_assets_asset ON lesson_assets(asset_id);

CREATE TABLE schools (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE source_papers (
    id INTEGER PRIMARY KEY,
    school_id INTEGER NOT NULL REFERENCES schools(id),
    exam_year INTEGER NOT NULL,
    source_ref TEXT NOT NULL
);
CREATE INDEX source_papers_school ON source_papers(school_id, exam_year, id);
CREATE TABLE source_paper_topics (
    paper_id INTEGER NOT NULL REFERENCES source_papers(id),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    question_count INTEGER NOT NULL CHECK (question_count > 0),
    PRIMARY KEY (paper_id, topic_id)
);
CREATE INDEX source_paper_topics_topic ON source_paper_topics(topic_id, paper_id);

CREATE TABLE exam_forms (
    id INTEGER PRIMARY KEY,
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    school_id INTEGER REFERENCES schools(id),
    form_code TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    purpose TEXT NOT NULL,
    selection_mode TEXT NOT NULL CHECK (selection_mode IN ('fixed_topics', 'weighted_topics')),
    question_count INTEGER NOT NULL CHECK (question_count > 0),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    difficulty_mix_json TEXT NOT NULL CHECK (json_valid(difficulty_mix_json)),
    required_access TEXT NOT NULL CHECK (required_access IN ('regular', 'vip')),
    UNIQUE (form_code, version),
    UNIQUE (id, grade_id)
);
CREATE INDEX exam_forms_grade ON exam_forms(grade_id, id);
CREATE INDEX exam_forms_school ON exam_forms(school_id, id);
CREATE TABLE exam_form_topics (
    form_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    weight REAL NOT NULL CHECK (weight > 0),
    PRIMARY KEY (form_id, topic_id),
    FOREIGN KEY (form_id, grade_id) REFERENCES exam_forms(id, grade_id),
    FOREIGN KEY (topic_id, grade_id) REFERENCES topics(id, grade_id)
);
CREATE INDEX exam_form_topics_topic ON exam_form_topics(topic_id);

ALTER TABLE exams ADD COLUMN form_id INTEGER REFERENCES exam_forms(id);
ALTER TABLE exams ADD COLUMN academic_year_id INTEGER REFERENCES academic_years(id);
ALTER TABLE exams ADD COLUMN owner_student_id INTEGER REFERENCES students(id);
ALTER TABLE exams ADD COLUMN mode TEXT NOT NULL DEFAULT 'practice' CHECK (mode IN ('practice', 'test'));
ALTER TABLE exams ADD COLUMN week_limit INTEGER CHECK (week_limit BETWEEN 0 AND 53);
ALTER TABLE exams ADD COLUMN created_at TEXT;
CREATE INDEX exams_owner_history ON exams(owner_student_id, created_at DESC, id DESC);
CREATE INDEX exams_published ON exams(status, grade_level, id);
CREATE INDEX exams_form ON exams(form_id);

CREATE TABLE exam_items (
    exam_id INTEGER NOT NULL REFERENCES exams(id),
    position INTEGER NOT NULL CHECK (position > 0),
    question_version_id INTEGER NOT NULL REFERENCES question_versions(id),
    max_points INTEGER NOT NULL CHECK (max_points > 0),
    PRIMARY KEY (exam_id, position),
    UNIQUE (exam_id, question_version_id)
);
CREATE INDEX exam_items_version ON exam_items(question_version_id);
CREATE TABLE exam_attempts (
    id INTEGER PRIMARY KEY,
    exam_id INTEGER NOT NULL UNIQUE REFERENCES exams(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    started_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    submitted_at TEXT,
    earned_points INTEGER CHECK (earned_points >= 0),
    total_points INTEGER CHECK (total_points > 0),
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'submitted')),
    UNIQUE (id, exam_id),
    CHECK (due_at > started_at),
    CHECK ((status = 'in_progress' AND submitted_at IS NULL) OR
        (status = 'submitted' AND submitted_at IS NOT NULL AND earned_points IS NOT NULL AND total_points IS NOT NULL)),
    CHECK (earned_points IS NULL OR total_points IS NULL OR earned_points <= total_points)
);
CREATE INDEX exam_attempts_student_history ON exam_attempts(student_id, submitted_at DESC, id DESC);
CREATE INDEX exam_attempts_ranking ON exam_attempts(status, submitted_at, student_id);
CREATE TABLE exam_answers (
    attempt_id INTEGER NOT NULL,
    exam_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    response_json TEXT NOT NULL CHECK (json_valid(response_json)),
    awarded_points INTEGER NOT NULL CHECK (awarded_points >= 0),
    PRIMARY KEY (attempt_id, position),
    FOREIGN KEY (attempt_id, exam_id) REFERENCES exam_attempts(id, exam_id),
    FOREIGN KEY (exam_id, position) REFERENCES exam_items(exam_id, position)
);
CREATE INDEX exam_answers_item ON exam_answers(exam_id, position);

CREATE TABLE mascots (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE mascot_levels (
    level INTEGER PRIMARY KEY CHECK (level > 0),
    min_xp INTEGER NOT NULL UNIQUE CHECK (min_xp >= 1000)
);
CREATE TABLE mascot_variants (
    mascot_id INTEGER NOT NULL REFERENCES mascots(id),
    level INTEGER NOT NULL REFERENCES mascot_levels(level),
    image_ref TEXT NOT NULL,
    effect_ref TEXT,
    PRIMARY KEY (mascot_id, level)
);
CREATE TABLE student_companions (
    student_id INTEGER PRIMARY KEY REFERENCES students(id),
    mascot_id INTEGER NOT NULL REFERENCES mascots(id),
    xp INTEGER NOT NULL DEFAULT 1000 CHECK (xp >= 1000)
);
CREATE INDEX student_companions_ranking ON student_companions(xp DESC, student_id);
CREATE TABLE bots (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('training', 'matchmaking')),
    display_name TEXT NOT NULL,
    skill_level INTEGER NOT NULL CHECK (skill_level BETWEEN 1 AND 3),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    xp INTEGER NOT NULL DEFAULT 1000 CHECK (xp >= 1000)
);
CREATE TABLE duels (
    id INTEGER PRIMARY KEY,
    grade_id INTEGER NOT NULL REFERENCES grades(id),
    mode TEXT NOT NULL CHECK (mode IN ('public', 'friends', 'training')),
    join_code TEXT,
    status TEXT NOT NULL CHECK (status IN ('waiting', 'active', 'completed', 'abandoned')),
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 4),
    curriculum_mode TEXT NOT NULL CHECK (curriculum_mode IN ('weekly', 'exam')),
    settings_json TEXT NOT NULL CHECK (json_valid(settings_json)),
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT
);
CREATE UNIQUE INDEX duels_waiting_code ON duels(join_code) WHERE join_code IS NOT NULL AND status = 'waiting';
CREATE INDEX duels_matchmaking ON duels(status, mode, grade_id, difficulty, curriculum_mode, created_at);
CREATE TABLE duel_players (
    id INTEGER PRIMARY KEY,
    duel_id INTEGER NOT NULL REFERENCES duels(id),
    student_id INTEGER REFERENCES students(id),
    bot_id INTEGER REFERENCES bots(id),
    slot INTEGER NOT NULL CHECK (slot IN (1, 2)),
    hp INTEGER NOT NULL DEFAULT 100 CHECK (hp BETWEEN 0 AND 100),
    outcome TEXT CHECK (outcome IN ('win', 'lose', 'draw', 'disconnected')),
    UNIQUE (duel_id, slot),
    UNIQUE (duel_id, student_id),
    UNIQUE (id, duel_id),
    CHECK ((student_id IS NOT NULL) <> (bot_id IS NOT NULL))
);
CREATE INDEX duel_players_student ON duel_players(student_id, id);
CREATE INDEX duel_players_bot ON duel_players(bot_id);
CREATE TABLE duel_rounds (
    id INTEGER PRIMARY KEY,
    duel_id INTEGER NOT NULL REFERENCES duels(id),
    question_version_id INTEGER NOT NULL REFERENCES question_versions(id),
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 20),
    started_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    winner_player_id INTEGER,
    UNIQUE (duel_id, position),
    UNIQUE (id, duel_id),
    FOREIGN KEY (winner_player_id, duel_id) REFERENCES duel_players(id, duel_id)
);
CREATE INDEX duel_rounds_question ON duel_rounds(question_version_id);
CREATE TABLE duel_answers (
    round_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    duel_id INTEGER NOT NULL,
    response_json TEXT NOT NULL CHECK (json_valid(response_json)),
    received_at TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    PRIMARY KEY (round_id, player_id),
    FOREIGN KEY (round_id, duel_id) REFERENCES duel_rounds(id, duel_id),
    FOREIGN KEY (player_id, duel_id) REFERENCES duel_players(id, duel_id)
);
CREATE INDEX duel_answers_player ON duel_answers(player_id);

CREATE TABLE lesson_progress (
    student_id INTEGER NOT NULL REFERENCES students(id),
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    first_completed_at TEXT NOT NULL,
    PRIMARY KEY (student_id, lesson_id)
);
CREATE INDEX lesson_progress_ranking ON lesson_progress(first_completed_at, student_id);
CREATE INDEX lesson_progress_lesson ON lesson_progress(lesson_id);
CREATE TABLE online_intervals (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    started_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    ended_at TEXT,
    CHECK (last_seen_at >= started_at),
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);
CREATE INDEX online_intervals_student ON online_intervals(student_id, started_at);
CREATE TABLE xp_events (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES student_companions(student_id),
    duel_player_id INTEGER UNIQUE REFERENCES duel_players(id),
    lesson_id INTEGER,
    exam_attempt_id INTEGER UNIQUE REFERENCES exam_attempts(id),
    delta INTEGER NOT NULL,
    awarded_at TEXT NOT NULL,
    UNIQUE (student_id, lesson_id),
    FOREIGN KEY (student_id, lesson_id) REFERENCES lesson_progress(student_id, lesson_id),
    CHECK ((duel_player_id IS NOT NULL) + (lesson_id IS NOT NULL) + (exam_attempt_id IS NOT NULL) = 1)
);
CREATE INDEX xp_events_student_period ON xp_events(student_id, awarded_at, id);
CREATE INDEX xp_events_period ON xp_events(awarded_at, student_id);

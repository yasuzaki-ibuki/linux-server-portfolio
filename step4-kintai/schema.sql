-- 勤怠(1日1行)
CREATE TABLE IF NOT EXISTS attendance (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    work_date   DATE        NOT NULL UNIQUE,
    clock_in    TIMESTAMPTZ,
    clock_out   TIMESTAMPTZ,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (clock_out IS NULL OR clock_in IS NULL OR clock_out > clock_in)
);

-- 日報(1日1行)
CREATE TABLE IF NOT EXISTS daily_reports (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_date  DATE        NOT NULL UNIQUE,
    done         TEXT,
    issues       TEXT,
    plan         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

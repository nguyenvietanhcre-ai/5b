ALTER TABLE learning_preferences ADD COLUMN theme TEXT NOT NULL DEFAULT 'garden-adventure'
    CHECK (theme IN ('garden-adventure','morning-garden','crayon-workshop','clay-sprout','garden-notebook'));

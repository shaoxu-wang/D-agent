"""Stage 2C DSim project memory categories."""

STAGE2C_MEMORY_KINDS: frozenset[str] = frozenset(
    {
        "project_fact",
        "user_preference",
        "operating_profile",
        "diagnostic_hint",
        "project_caution",
        "engineering_conclusion",
    }
)

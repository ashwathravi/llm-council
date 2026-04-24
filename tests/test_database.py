from sqlalchemy import Column, DateTime, JSON, MetaData, String, Table, create_engine, inspect

from backend.database import _ensure_conversation_schema


def test_ensure_conversation_schema_adds_design_studio_columns_to_legacy_table():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "conversations",
        metadata,
        Column("id", String, primary_key=True),
        Column("user_id", String, nullable=False),
        Column("title", String),
        Column("created_at", DateTime),
        Column("framework", String),
        Column("council_models", JSON),
        Column("chairman_model", String),
        Column("messages", JSON),
        Column("origin", String),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        _ensure_conversation_schema(connection)

    columns = {column["name"] for column in inspect(engine).get_columns("conversations")}

    assert "session_type" in columns
    assert "specialist_template_id" in columns
    assert "execution_mode" in columns
    assert "session_config" in columns
    assert "primary_artifacts" in columns


def test_ensure_conversation_schema_is_idempotent_for_current_table():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    Table(
        "conversations",
        metadata,
        Column("id", String, primary_key=True),
        Column("user_id", String, nullable=False),
        Column("session_type", String),
        Column("specialist_template_id", String),
        Column("execution_mode", String),
        Column("session_config", JSON),
        Column("primary_artifacts", JSON),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        _ensure_conversation_schema(connection)
        _ensure_conversation_schema(connection)

    columns = [column["name"] for column in inspect(engine).get_columns("conversations")]

    assert columns.count("session_config") == 1
    assert columns.count("primary_artifacts") == 1

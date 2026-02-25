from sqlalchemy import Column
from clickhouse_sqlalchemy import types, engines
from sqlalchemy.orm import registry


mapper_registry = registry()
Base = mapper_registry.generate_base()

# Model for posts in Buffer table
class BufferPost(Base):
    __tablename__ = "telegram_posts_buffer"
    __table_args__ = (
        engines.Buffer(
            "vazir", "telegram_posts",
            16, 10, 600, 10000, 100000, 10000000, 200000000
        ),
    )

    channel = Column(types.String, primary_key=True)
    msgid = Column(types.UInt32, primary_key=True)
    ptype = Column(types.Nullable(types.String))
    views = Column(types.UInt64)
    reactions = Column(types.UInt64)
    is_forwarded = Column(types.UInt8)
    forwarded_from = Column(types.Nullable(types.String))
    txtContent = Column(types.Nullable(types.String))
    date = Column(types.DateTime(timezone='Asia/Tehran'))
    shdate = Column(types.String)
    day_of_week = Column(types.UInt8)
    is_holiday = Column(types.UInt8)
    insert_date = Column(types.DateTime(timezone='Asia/Tehran'))
    update_date = Column(types.DateTime(timezone='Asia/Tehran'))


# Model for comments in Buffer table
class BufferComment(Base):
    __tablename__ = "telegram_comments_buffer"
    __table_args__ = (
        engines.Buffer(
            "vazir", "telegram_comments",
            16, 10, 600, 10000, 100000, 10000000, 200000000
        ),
    )

    comment_id = Column(types.UInt32, primary_key=True)
    channel = Column(types.String, primary_key=True)
    msgid = Column(types.UInt32, primary_key=True)
    user_id = Column(types.UInt64)
    ptype = Column(types.Nullable(types.String))
    reactions = Column(types.UInt64)
    is_reply = Column(types.UInt8)
    reply_to = Column(types.Nullable(types.UInt32))
    txtContent = Column(types.Nullable(types.String))
    date = Column(types.DateTime(timezone='Asia/Tehran'))
    shdate = Column(types.String)
    day_of_week = Column(types.UInt8)
    is_holiday = Column(types.UInt8)
    insert_date = Column(types.DateTime(timezone='Asia/Tehran'))
    update_date = Column(types.DateTime(timezone='Asia/Tehran'))


# Model for reactions in Buffer table
class BufferReaction(Base):
    __tablename__ = "telegram_reactions_buffer"
    __table_args__ = (
        engines.Buffer(
            "vazir", "telegram_reactions",
            16, 10, 600, 10000, 100000, 10000000, 200000000
        ),
    )

    channel = Column(types.String, primary_key=True)
    msgid = Column(types.UInt32, primary_key=True)
    reaction = Column(types.String, primary_key=True)
    count = Column(types.UInt32)
    insert_date = Column(types.DateTime(timezone='Asia/Tehran'))
    update_date = Column(types.DateTime(timezone='Asia/Tehran'))

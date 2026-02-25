from sqlalchemy import create_engine, text
from clickhouse_sqlalchemy import make_session
from db.models import Base  # If Base is defined in models

# Initialize logger

# 1) Connection URL to ClickHouse
DB_URL = "clickhouse+http://reza:1234@localhost/vazir1"


engine = create_engine(DB_URL, echo=True)
SessionLocal = make_session  


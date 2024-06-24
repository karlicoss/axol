from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from loguru import logger
import orjson
import sqlalchemy
from sqlalchemy import (
    event,
    select,
    Column,
    Table,
)

from .common import (
    datetime_aware,
    DbResult,
    SearchResult,
)
from .utils import sqlalchemy_strict_sqlite


CrawlDt = datetime_aware


class Columns:
    UID = 'uid'
    # FIXME rename from crawl to search?
    CRAWL_TIMESTAMP_UTC = 'crawl_timestamp_utc'
    DATA = 'data'


class Database(AbstractContextManager):
    # todo read only mode?
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.engine = sqlalchemy.create_engine(f'sqlite:///{db_path}', echo=False)
        self.metadata = sqlalchemy.MetaData()

        # see https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl
        def do_connect(dbapi_connection, connection_record):
            # TOOD I think th commnt below is misleading?? it still works without??
            # disable pysqlite's emitting of the BEGIN statement entirely.
            # also stops it from emitting COMMIT before any DDL.
            dbapi_connection.isolation_level = None
        # TODO shit. why is it still emitting BEGIN (implicit) in addition to regular begin??
        # could it be to do with python3.12??
        # event.listen(self.engine, 'connect', do_connect)

        def _begin_immediate_transaction(conn) -> None:
            conn.exec_driver_sql('BEGIN IMMEDIATE')
        event.listen(self.engine, 'begin', _begin_immediate_transaction)

        self.results_table = Table(
            'results',
            self.metadata,
            # todo primary key?
            Column(Columns.UID                , sqlalchemy.Text   , nullable=False, unique=True),
            Column(Columns.CRAWL_TIMESTAMP_UTC, sqlalchemy.Integer, nullable=False),
            Column(Columns.DATA               , sqlalchemy.BLOB   , nullable=False),
        )

        with sqlalchemy_strict_sqlite():
            # NOTE: checkfirst=True is default -- if false it would complain if db already exists
            self.metadata.create_all(self.engine)

    def __exit__(self, *args, **kwargs) -> None:
        self.engine.dispose()


    def select_all(self) -> Iterator[DbResult]:
        # FIXME double check that simultaneous write and read work
        query = self.results_table.select().order_by(Columns.CRAWL_TIMESTAMP_UTC, Columns.UID)
        with self.engine.connect() as conn:
            for uid, crawl_timestamp_utc, blob in conn.execute(query):
                crawl_dt = datetime.fromtimestamp(crawl_timestamp_utc, tz=timezone.utc)
                j = orjson.loads(blob)
                yield (uid, crawl_dt, j)


    def insert(self, results: Iterator[SearchResult]) -> None:
        # TODO dry mode??
        crawl_dt = datetime.now(tz=timezone.utc)
        crawl_timestamp_utc = int(crawl_dt.timestamp())
        logger.info(f'[{self.db_path}] inserting crawled items, dt {crawl_dt} {crawl_timestamp_utc}')

        batch_new = 0
        batch_exist = 0
        with self.engine.begin() as conn:
            uids_in_db = {uid for (uid,) in conn.execute(select(self.results_table.c[Columns.UID]))}

            for_db = []
            for uid, j in results:
                if uid in uids_in_db:
                    batch_exist += 1
                    continue
                # todo store as jsonb? not sure if there is any benefit?
                batch_new += 1
                for_db.append({
                    Columns.UID: uid,
                    Columns.CRAWL_TIMESTAMP_UTC: crawl_timestamp_utc,
                    Columns.DATA: orjson.dumps(j),
                })
            # TODO old axol had batch insertion? (in 1000 items chunks)
            # figure out whether I still need it (ideally via a test?)
            if len(for_db) > 0:
                conn.execute(self.results_table.insert(), for_db)

        batch_total = batch_exist + batch_new
        # TODO log new total size?
        logger.info(f'[{self.db_path}] batch stats -- {batch_total} crawled, {batch_exist} existed, {batch_new} new')

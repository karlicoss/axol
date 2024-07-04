from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Callable, Iterable, Iterator, cast

from loguru import logger
import sqlalchemy
from sqlalchemy import (
    event,
    func,
    select,
    Column,
    Table,
)

from .common import (
    datetime_aware,
    Uid,
)
from .utils import sqlalchemy_strict_sqlite


CrawlDt = datetime_aware


class Columns:
    UID = 'uid'
    CRAWL_TIMESTAMP_UTC = 'crawl_timestamp_utc'
    DATA = 'data'


class Database(AbstractContextManager['Database']):
    def __init__(self, db_path: Path, *, writable: bool = False) -> None:
        assert db_path.is_absolute(), db_path

        if not writable:
            assert db_path.exists(), db_path

        self.db_path = db_path
        mode = '' if writable else '?mode=ro'
        creator = lambda: sqlite3.connect(f'file:{db_path}{mode}', uri=True)
        self.engine = sqlalchemy.create_engine('sqlite://', creator=creator, echo=False)

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
            # fmt: off
            Column(Columns.UID                , sqlalchemy.Text   , nullable=False, unique=True),
            Column(Columns.CRAWL_TIMESTAMP_UTC, sqlalchemy.Integer, nullable=False),
            Column(Columns.DATA               , sqlalchemy.BLOB   , nullable=False),
            # fmt: on
        )

        with sqlalchemy_strict_sqlite():
            # NOTE: checkfirst=True is default -- if false it would complain if db already exists
            self.metadata.create_all(self.engine)

    def __exit__(self, *args, **kwargs) -> None:
        self.engine.dispose()

    def select_all(self) -> Iterator[tuple[Uid, int, bytes]]:
        # TODO double check that simultaneous write and read work
        query = self.results_table.select().order_by(Columns.CRAWL_TIMESTAMP_UTC, Columns.UID)
        with self.engine.connect() as conn:
            yield from map(tuple, conn.execute(query))

    def delete(
        self,
        *,
        dry: bool,
        predicate: Callable[[bytes], bool],
    ) -> int:
        with self.engine.begin() as conn:
            dbapi_connection = conn.connection  # meh
            dbapi_connection.create_function("predicate", 1, predicate)  # type: ignore[attr-defined]
            if dry:
                squery = select(func.count()).select_from(self.results_table).where(func.predicate(self.results_table.c.data))
                res = conn.execute(squery)
                [(deleted,)] = list(res)
            else:
                dquery = self.results_table.delete().where(func.predicate(self.results_table.c.data))
                res = conn.execute(dquery)
                deleted = res.rowcount
        return deleted

    def insert(
        self,
        results: Iterable[tuple[Uid, bytes]],
        *,
        dry: bool,
    ) -> Iterator[tuple[Uid, CrawlDt, bytes]]:
        """
        Yields actually inserted items, along with the crawl timestamp
        """
        # FIXME ugh. reorder crawl_dt first?? also in the db...

        # todo dry mode??
        crawl_dt = datetime.now(tz=timezone.utc)
        crawl_timestamp_utc = int(crawl_dt.timestamp())
        logger.info(f'[{self.db_path}] inserting crawled items, dt {crawl_dt} {crawl_timestamp_utc}')

        new = 0
        exist = 0
        with self.engine.begin() as conn:
            uids_in_db = {uid for (uid,) in conn.execute(select(self.results_table.c[Columns.UID]))}

            for_db = []
            for uid, jb in results:
                if uid in uids_in_db:
                    exist += 1
                    continue
                # todo store as jsonb? not sure if there is any benefit?
                new += 1
                assert isinstance(jb, bytes), jb  # todo temporary for refactoring period
                for_db.append(
                    {
                        Columns.UID: uid,
                        Columns.CRAWL_TIMESTAMP_UTC: crawl_timestamp_utc,
                        Columns.DATA: jb,
                    }
                )
            # todo old axol had batch insertion? (in 1000 items chunks)
            # figure out whether I still need it (ideally via a test?)
            if len(for_db) > 0:
                if not dry:
                    conn.execute(self.results_table.insert(), for_db)
                else:
                    logger.warning(f'[{self.db_path}] dry mode, not updating the db')

        total = exist + new
        logger.info(f'[{self.db_path}] stats -- {total} crawled, {exist} existed, {new} new')

        for d in for_db:
            uid = cast(Uid, d[Columns.UID])
            jb = cast(bytes, d[Columns.DATA])
            yield uid, crawl_dt, jb  # meh

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
    make_uid,
    Uid,
)
from .utils import sqlalchemy_strict_sqlite


CrawlDt = datetime_aware


class Columns:
    CRAWL_TIMESTAMP_UTC = 'crawl_timestamp_utc'
    UID = 'uid'
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
            # fmt: off
            Column(Columns.CRAWL_TIMESTAMP_UTC, sqlalchemy.Integer, nullable=False),
            Column(Columns.UID                , sqlalchemy.Text   , nullable=False, unique=True),
            Column(Columns.DATA               , sqlalchemy.BLOB   , nullable=False),
            # fmt: on
        )

        with sqlalchemy_strict_sqlite():
            # NOTE: checkfirst=True is default -- if false it would complain if db already exists
            self.metadata.create_all(self.engine)

    def __exit__(self, *args, **kwargs) -> None:
        self.engine.dispose()

    def select_all(self) -> Iterator[tuple[int, Uid, bytes]]:
        # TODO double check that simultaneous write and read work
        query = self.results_table.select().order_by(Columns.CRAWL_TIMESTAMP_UTC, Columns.UID)
        with self.engine.connect() as conn:
            total_query = select(func.count()).select_from(self.results_table)
            [(total,)] = list(conn.execute(total_query))
            logger.info(f'total db items: {total}')

            for row in conn.execute(query):
                ts, uid, data = row
                # just in case
                assert isinstance(ts, int), row
                assert isinstance(uid, str), row
                assert isinstance(data, bytes), row
                yield ts, make_uid(uid), data

    def delete(
        self,
        *,
        dry: bool,
        predicate: Callable[[bytes], bool],
    ) -> Iterator[tuple[int, Uid, bytes]]:
        # fmt: off
        select_query = self.results_table.select().where(func.predicate(self.results_table.c.data))
        delete_query = self.results_table.delete().where(func.predicate(self.results_table.c.data))
        # fmt: on
        with self.engine.begin() as conn:
            dbapi_connection = conn.connection  # meh
            dbapi_connection.create_function("predicate", 1, predicate)  # type: ignore[attr-defined]
            to_prune = list(conn.execute(select_query))
            if not dry:
                res = conn.execute(delete_query)
                deleted = res.rowcount
                assert deleted == len(to_prune), (deleted, len(to_prune))  # just in case
        for row in to_prune:
            ts, uid, data = row
            yield ts, make_uid(uid), data

    def _insert(
        self,
        items: Iterable[tuple[CrawlDt, Uid, bytes]],
        *,
        dry: bool,
    ) -> Iterator[tuple[CrawlDt, Uid, bytes]]:
        new = 0
        exist = 0
        with self.engine.begin() as conn:
            uids_in_db = {uid for (uid,) in conn.execute(select(self.results_table.c[Columns.UID]))}
            seen = set()
            for_db = []
            for crawl_dt, uid, jb in items:
                # make sure we aren't passed down dupes from search
                # (search is better suited to deal with them properly)
                assert uid not in seen, (uid, jb)
                seen.add(uid)

                if uid in uids_in_db:
                    exist += 1
                    continue

                crawl_timestamp_utc = int(crawl_dt.timestamp())

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
            yield crawl_dt, uid, jb  # meh

    def insert(
        self,
        results: Iterable[tuple[Uid, bytes]],
        *,
        dry: bool,
    ) -> Iterator[tuple[CrawlDt, Uid, bytes]]:
        """
        Yields actually inserted items, along with the crawl timestamp
        """
        now_dt = datetime.now(tz=timezone.utc)
        logger.info(f'[{self.db_path}] inserting crawled items, dt {now_dt}')

        items = ((now_dt, uid, jb) for uid, jb in results)
        return self._insert(items, dry=dry)


def test_insert(tmp_path: Path) -> None:
    import pytest

    def results_1() -> Iterator[tuple[Uid, bytes]]:
        yield make_uid('1'), b'whatever 1'
        yield make_uid('2'), b'whatever 1'

    def results_2() -> Iterator[tuple[Uid, bytes]]:
        yield make_uid('3'), b'whatever 2'
        yield make_uid('2'), b'whatever 2'

    def results_3() -> Iterator[tuple[Uid, bytes]]:
        yield make_uid('4'), b'whatever 3'
        yield make_uid('4'), b'whatever 3'

    def results_4() -> Iterator[tuple[Uid, bytes]]:
        yield make_uid('1'), b'boom'
        yield make_uid('999'), b'whatever 4'
        yield make_uid('1'), b'boom'

    db_path = tmp_path / 'db.sqlite'
    with Database(db_path, writable=True) as db:
        ins_1 = [uid for _, uid, _ in db.insert(results_1(), dry=False)]
        assert ins_1 == ['1', '2']

    with Database(db_path, writable=True) as db:
        # inserting same stuff is a no-op
        ins_1 = [uid for _, uid, _ in db.insert(results_1(), dry=False)]
        assert ins_1 == []

        ins_2 = [uid for _, uid, _ in db.insert(results_2(), dry=False)]
        # item 2 actually changed, but we don't do anything with it, at least for now
        assert ins_2 == ['3']

        in_db = [(uid, blob) for _, uid, blob in db.select_all()]
        assert in_db == [
            ('1', b'whatever 1'),
            ('2', b'whatever 1'),  # item 2 wasn't updated!
            ('3', b'whatever 2'),
        ]

    with Database(db_path, writable=True) as db:
        with pytest.raises(AssertionError):
            list(db.insert(results_3(), dry=False))

    with Database(db_path, writable=True) as db:
        with pytest.raises(AssertionError):
            list(db.insert(results_4(), dry=False))


def test_insert_atomic(tmp_path: Path) -> None:
    import pytest

    db_path = tmp_path / 'db.sqlite'

    def results_ok() -> Iterator[tuple[Uid, bytes]]:
        for i in range(10):
            yield make_uid(str(i)), b'item {i}'

    with Database(db_path, writable=True) as db:
        list(db.insert(results_ok(), dry=False))

    with Database(db_path, writable=False) as db:
        assert len(list(db.select_all())) == 10

    def results_bad() -> Iterator[tuple[Uid, bytes]]:
        for i in range(1_000_000):
            yield make_uid(str(i)), b'item {i}'
        raise RuntimeError('BOOM')

    with Database(db_path, writable=True) as db:
        with pytest.raises(RuntimeError, match='BOOM'):
            list(db.insert(results_bad(), dry=False))

    # error during insertion should leave the db intact
    with Database(db_path, writable=False) as db:
        assert len(list(db.select_all())) == 10

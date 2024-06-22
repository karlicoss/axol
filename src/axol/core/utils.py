from contextlib import contextmanager


@contextmanager
def sqlalchemy_strict_sqlite():
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.sql.ddl import CreateTable

    # see https://github.com/sqlalchemy/sqlalchemy/issues/7398#issuecomment-1772821099
    @compiles(CreateTable, "sqlite")
    def tables_are_strict(create_table, compiler, **kw):
        return compiler.visit_create_table(create_table, **kw) + "STRICT"

    try:
        yield
    finally:
        # restore the original
        @compiles(CreateTable, "sqlite")
        def tables_are_strict(create_table, compiler, **kw):
            return compiler.visit_create_table(create_table, **kw)

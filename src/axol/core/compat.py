import sys

if sys.version_info[:2] >= (3, 11):
    add_note = BaseException.add_note
else:

    def add_note(e: BaseException, note: str) -> None:
        """
        Backport of BaseException.add_note
        """

        # The only (somewhat annoying) difference is it will log extra lines for notes past the main exception message:
        # (i.e. line 2 here:)

        # 1 [ERROR   2025-02-04 22:12:21] Main exception message
        # 2 ^ extra note
        # 3 Traceback (most recent call last):
        # 4   File "run.py", line 19, in <module>
        # 5     ee = test()
        # 6   File "run.py", line 5, in test
        # 7     raise RuntimeError("Main exception message")
        # 8 RuntimeError: Main exception message
        # 9 ^ extra note

        args = e.args
        if len(args) == 1 and isinstance(args[0], str):
            e.args = (e.args[0] + '\n' + note,)


from datetime import datetime

if sys.version_info[:2] >= (3, 11):
    fromisoformat = datetime.fromisoformat
else:
    # fromisoformat didn't support some things (e.g Z as UTC or stuff other than +00:00) before 3.11
    # https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat

    def fromisoformat(date_string: str) -> datetime:
        try:
            return datetime.fromisoformat(date_string)
        except ValueError:
            from dateutil import parser  # type: ignore[import-untyped]

            return parser.parse(date_string)

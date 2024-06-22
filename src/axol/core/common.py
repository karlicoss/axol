from datetime import datetime
from typing import Any

Json = dict[str, Any]

Uid = str

CrawlResult = tuple[Uid, Json]

datetime_aware = datetime

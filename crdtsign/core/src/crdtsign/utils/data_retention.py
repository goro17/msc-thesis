"""Utilities for managing the data retention policy."""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import arrow

from crdtsign.config import data_retention_config


def check_data_retention(file: Dict[str, str or bytes]) -> Tuple[bool, Optional[str]]:
    """Checks if the file is within scope of the assigned data retention policy."""
    file_timestamp = datetime.fromisoformat(file["signed_on"])
    exp_date = datetime.fromisoformat(file["expiration_date"]) if "expiration_date" in file else None

    data_retention_expiration_days = int(data_retention_config["data_retention_period"])

    if data_retention_expiration_days == 0:
        return False, None

    if exp_date is None or exp_date > file_timestamp + timedelta(days=data_retention_expiration_days):
        return True, str(file_timestamp + timedelta(days=data_retention_expiration_days))
    else:
        return False, None

def get_time_until_expiration(date_str: str) -> str:
    """Returns the time until the file's expiration date in human-readable form."""
    date_formatted = arrow.get(datetime.fromisoformat(date_str))

    return date_formatted.humanize(arrow.now(), only_distance=False)

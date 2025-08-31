from pathlib import Path

from crdtsign.storage import FileSignatureStorage, UserStorage
from crdtsign.user import User


user = User()
user_storage = UserStorage(
    client_id=user.user_id,
    host="0.0.0.0",
    port=8765,
    from_file=True if Path(".storage/users.bin").exists() else False
)
file_storage = FileSignatureStorage(
    client_id=user.user_id,
    host="0.0.0.0",
    port=8765,
    from_file=True if Path(".storage/signatures.bin").exists() else False
)
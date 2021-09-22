from typing import List

from monkey_island.cc.models.utils.field_encryptors.i_field_encryptor import IFieldEncryptor
from monkey_island.cc.server_utils.encryption import get_datastore_encryptor


class StringListEncryptor(IFieldEncryptor):
    @staticmethod
    def encrypt(value: List[str]):
        return [get_datastore_encryptor().enc(string) for string in value]

    @staticmethod
    def decrypt(value: List[str]):
        return [get_datastore_encryptor().dec(string) for string in value]
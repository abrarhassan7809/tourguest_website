from passlib.context import CryptContext

pwd_cxt = CryptContext(schemes=["argon2"], deprecated="auto")


class Hash:
    @staticmethod
    def argon2(password):
        is_password = pwd_cxt.hash(password)
        return is_password

    @staticmethod
    def verify(plain_password, hashed_password):
        is_verify = pwd_cxt.verify(plain_password, hashed_password)
        return is_verify
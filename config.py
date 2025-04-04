

import os

class Config:
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_SSL_CA = "/etc/ssl/certs/ca-certificates.crt"

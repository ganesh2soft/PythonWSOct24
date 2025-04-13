class Config:
    # Database URI format for MySQL (adjust to your credentials and database name))
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:P%40ssw0rd@localhost/traderdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable unnecessary modification tracking overhead


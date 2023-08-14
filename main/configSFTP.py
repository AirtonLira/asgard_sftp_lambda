class configFTP:

  # multipart parameters
  MB = 1024 ** 2
  GB = 1024 ** 3

  MULTIPART_THRESHOLD = 100 * MB
  MULTIPART_CHUNKSIZE=20 * MB
  MAX_CONCURRENCY=10
  USER_THREADS=True
  def __init__(self, SSH_CLIENT=None, SFTP_CLIENT=None, SSH_OK=False, SFTP_OK=False, FTP_HOST = "", FTP_PORT = "", FTP_USERNAME = "", FTP_PASSWORD = "", S3_BUCKET = "", PARENT_DIR_PATH = "/cartao-lopes-smartnx/faturas/", PROCESSED_DIR_PATH = "/cartao-lopes-smartnx/faturas/processadoSNXpay/", MULTIPART_THRESHOLD=MULTIPART_THRESHOLD, MULTIPART_CHUNKSIZE=MULTIPART_CHUNKSIZE, MAX_CONCURRENCY=MAX_CONCURRENCY, USER_THREADS=USER_THREADS,
              FIXED_DIR_PATH="rpe"):
    # paramiko parameters
    self.SSH_CLIENT = SSH_CLIENT
    self.SFTP_CLIENT = SFTP_CLIENT
    self.SSH_OK = SSH_OK
    self.SFTP_OK = SFTP_OK

    # ftp credentials
    self.FTP_HOST = FTP_HOST
    self.FTP_PORT = FTP_PORT
    self.FTP_USERNAME = FTP_USERNAME
    self.FTP_PASSWORD = FTP_PASSWORD

    # s3 parameters
    self.S3_BUCKET = S3_BUCKET

    # sftp directory paths
    self.PARENT_DIR_PATH = PARENT_DIR_PATH
    self.PROCESSED_DIR_PATH = PROCESSED_DIR_PATH
    self.FIXED_DIR_PATH = FIXED_DIR_PATH
    
    # sftp multipart configs
    self.MULTIPART_THRESHOLD = MULTIPART_THRESHOLD
    self.MULTIPART_CHUNKSIZE = MULTIPART_CHUNKSIZE
    self.MAX_CONCURRENCY = MAX_CONCURRENCY
    self.USER_THREADS = USER_THREADS
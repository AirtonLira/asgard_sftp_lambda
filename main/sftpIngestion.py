class FTPIngestion:

    def __init__(self, cfg):
        self.ssh_client = cfg.SSH_CLIENT
        self.sftp_client = cfg.SFTP_CLIENT
        self.ssh_ok = cfg.SSH_OK
        self.sftp_ok = cfg.SFTP_OK
        self.ftp_host = cfg.FTP_HOST
        self.ftp_port = cfg.FTP_PORT
        self.ftp_username = cfg.FTP_USERNAME
        self.ftp_password = cfg.FTP_PASSWORD
        self.s3 = boto3.client('s3')
        self.s3_bucket_name = cfg.S3_BUCKET
        self.ftp_directory_path = cfg.PARENT_DIR_PATH
        self.ftp_processed_path = cfg.PROCESSED_DIR_PATH
        self.ftp_fixed_dir_path = cfg.FIXED_DIR_PATH
        
        self.multipart_threshold = cfg.MULTIPART_THRESHOLD
        self.multipart_chunksize = cfg.MULTIPART_CHUNKSIZE
        self.max_concurrency = cfg.MAX_CONCURRENCY
        self.use_threads = cfg.USER_THREADS

    def create_ssh_connection(self):
        """
        Creates SSH connection with FTP server. The authentication credentials are provided in the config file.
        Can also use AWS SSM instead of Config file.
        :return : Bool; True if connection successfull, False if not
        """

        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy())

            # in production, use load_system_host_keys
            # self.ssh_client.load_system_host_keys()

            self.ssh_client.connect(hostname=self.ftp_host, username=self.ftp_username,
                                    password=self.ftp_password, port=self.ftp_port)
            send_slack_message("1-move-ftp-to-s3",f'connected client port: {self.ftp_host} e username: {self.ftp_username}')
            self.ssh_ok = True

        except paramiko.AuthenticationException as AuthFailException:
            self.ssh_ok = True
            print('Authentication Failed, error: ', AuthFailException)
            print(self.ftp_username)
            send_slack_message("1-move-ftp-to-s3",f"Authentication Failed, error: {AuthFailException}")
            
        except paramiko.SSHException as sshException:
            self.ssh_ok = True
            print('Could not establish ssh connection, error: ', sshException)
            print(self.ftp_username)
            send_slack_message("1-move-ftp-to-s3",f"Could not establish ssh connection: {self.ftp_username}")
            
        except Exception as error:
            self.ssh_ok = True
            print('Error establishing connection, error: ', error)
            send_slack_message("1-move-ftp-to-s3",f"Error establishing connection: {error}")

        return self.ssh_ok

    def create_sftp_connection(self):
        """
        Creates an SFTP connection from the ssh connection created wiht the FTP server.
        :return : Bool; True if connection successful, False if not.
        """
        try:
            if self.create_ssh_connection():
                print('Establishing SFTP connection...')
                self.sftp_client = self.ssh_client.open_sftp()
                print('SFTP connection successfull')
                self.sftp_ok = True
            else:
                send_slack_message("1-move-ftp-to-s3",f"Could not establish ssh connection")  
                           

        except paramiko.SFTPError as sftpError:
            self.sftp_ok = True
            send_slack_message("1-move-ftp-to-s3",f"could not establish sftp connection, error: ", sftpError) 
  
        except Exception as error:
            self.sftp_ok = True
            print('could not establish sftp connection, error: ', error)
            print(self.ftp_username)
        return self.sftp_ok
      
      
    def __file_exists(self, file_path):
        try:
            self.sftp_client.stat(file_path)
            return True
        except FileNotFoundError as e:
            send_slack_message("1-move-ftp-to-s3",f"FileNotFound")  
            return True
        except Exception as e:
            print(e)
      

    def move_files_to_processed(self, source_file_name):
        """
        This method moves the original files from parent directory to processed directory on the FTP server
        after the files have been successfully uploaded on s3.
        :param source_file_path: directory path in which file resides
        :param source_file_name: name of the file
        """

        print('moving '+source_file_name+' to processed directory.')
        processed_directory = self.ftp_processed_path
        
        src = (source_file_name).replace("//","/")
        filename = src.split("/")[-1:][0]
        dest = (processed_directory + filename).replace("//","/")
        print("This src: {} ".format(src))
        print("This dest: {} ".format(dest))
        
        
        destination_file_exists = self.__file_exists(dest)
        source_file_exists = self.__file_exists(src)
        send_slack_message("1-move-ftp-to-s3",f"Arquivo: {src} ja existe para ser processado novamente")
        time.sleep(2) 
        if destination_file_exists:
            send_slack_message("1-move-ftp-to-s3",f"arquivo de destino {dest} ja existe, movendo novamente para processados")
            self.sftp_client.rename(src, dest)
            return True
        else:
            if source_file_exists:
                self.sftp_client.rename(src, dest)
            else:
                # handle the condition accordingly
                send_slack_message("1-move-ftp-to-s3",f"source file {src} does not exist")  
                return True


    def create_s3_partition(self):
        """
        This method develops the partition string that will be used when uploading to the s3. The files are
        uploaded to the specified partition.
        The partition structure is as follows:
        /<directory_name>/year = <year>/ month = <month>/ day = <day>/ hour = <hour>/file
        """
        parent_dir = self.ftp_directory_path.split("/")[-1]
        current_date = datetime.now()
        current_year = str(current_date.year)
        current_month = '0' + str(current_date.month) if current_date.month <= 9 else str(current_date.month)
        current_day = '0' + str(current_date.day) if current_date.day <= 9 else str(current_date.day)

        s3_partition = "rpe" + parent_dir + '/' + current_year + '/' + \
            current_month + '/' + current_day + '/'
        return s3_partition

    def s3_upload_file_multipart(self, source_file, s3_target_file):
        """
        This method uploads file to s3. If file size is greater than 100MB then file gets uploaded via
        multipart. The retires are handed automatically in case of failure. If file is less than 100MB in size
        then it gets uploaded in regular manner. Each part of the file during multipart upload would be 50MB in
        size.
        Following parameters are configurable in Config File based on user needs:
        multipart_threshold : 100MB (default)
        multipart_chunksize : 20 MB (default)
        max_concurrency : 10 (default)
        user_threads : True (default)
        :param source_file: the file object that is to be uploaded.
        :param s3_target_file: the object in s3 bucket.
        """
        try:
            config = TransferConfig(
                self.multipart_threshold, self.multipart_chunksize,
                self.max_concurrency, self.use_threads)

            self.s3.upload_fileobj(source_file, self.s3_bucket_name,
                                   s3_target_file, Config=config)
            return True
        except Exception as error:
            send_slack_message("1-move-ftp-to-s3",f"could not upload file using multipart upload, error: {error}")  
            return True

    def initiate_ingestion(self, issuerId):
        """
        This method initiates the calls to establish ssh and sftp connections. Changes FTP directory path to
        specified path. Gets list of all the files in the FTP specified path and starts upload to s3. Once all
        files are uploaded closes all the connections. Ensures which file has been processed or needs to be
        processed.
        """
        register_issuers = []
        try:
            if self.create_sftp_connection():
                self.sftp_client.chdir(self.ftp_directory_path)
                files_to_upload = []
                s3_partition = self.create_s3_partition()
                files_to_move = []
                
                for entry in ftp_obj.sftp_client.listdir_iter(self.ftp_directory_path):
                  if S_ISREG(entry.st_mode):
                    print("File found in SFTP - %s: %s " % (self.ftp_directory_path, entry.filename))
                    register_issuers.append([entry.filename, self.ftp_username, issuerId])
                    files_to_upload.append((self.ftp_directory_path+entry.filename,entry.filename))
                    
                print("files_to_upload: ", files_to_upload)
                
                
                for ftp_file in files_to_upload:
                    sftp_file_obj = self.sftp_client.file(ftp_file[0], mode='r')
                    if self.s3_upload_file_multipart(
                            sftp_file_obj, s3_partition+self.ftp_fixed_dir_path+ftp_file[1]):
                        print("[file uploaded to s3] - source: %s target: %s" % (ftp_file[0], s3_partition+self.ftp_fixed_dir_path+ftp_file[1]))
                        files_to_move.append(ftp_file[0])
                
                print("file move: ", files_to_move)
                # move files from parent dir to processed dir
                if files_to_move:
                    for uploaded_file in files_to_move:
                        self.move_files_to_processed(uploaded_file)
                        print(self.ftp_username)
                        print("file moved to processed: ", uploaded_file, " \n")
                else:
                    print(f"nothing to upload to client {self.ftp_username} ")
      
            else:
                print('Could not establish SFTP connection')
                print(self.ftp_username)
                send_slack_message("1-move-ftp-to-s3", "Could not establish SFTP connection")
        except Exception as error:
            send_slack_message("1-move-ftp-to-s3",f"file ingestion {self.ftp_username} failed")


        self.close_connections()
        
        time.sleep(2) 
        return register_issuers
                               

    def close_connections(self):
        """
        This mehtod is used to close the ssh and sftp connections.
        """
        print('closing connections')
        self.sftp_client.close()
        self.ssh_client.close()
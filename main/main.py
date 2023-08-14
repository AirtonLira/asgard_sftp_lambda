import os
import boto3
import time
import urllib
import json
import sys
import requests



S3_BUCKET_NAME = "invoice-file-s3-prod"

def send_slack_message(titulo, descricao):
  hora = __captura_hora_local()
  horastr = hora.strftime("%d/%m/%Y - %H:%M:%S")
  payload = {"text": horastr + " - "+titulo + " - "+descricao}
  webhook = "https://hooks.slack.com/services/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"
  requests.post(webhook, json.dumps(payload))


def __captura_hora_local():
    utc_dt = datetime.now(timezone.utc)
    BRASILIA = pytz.timezone('Brazil/East')
    data = utc_dt.astimezone(BRASILIA)
    return data


def associateElasticIP(ip_associate):
    instance = json.loads(urllib.request.urlopen(
        '<http://169.254.169.254/latest/dynamic/instance-identity/document>').read())
    conn = boto3.client('ec2', region_name=aws_region)
    address = [x for x in conn.describe_addresses()['Addresses']
                                                  if x["PublicIp"] == ip_associate][0]
    result = conn.associate_address(
        InstanceId=instance[u'instanceId'], AllocationId=address["AllocationId"])
    return result


def lambda_handler(event, context):
    
    print("Hello World!")
    return {
        'statusCode': 200,
        'body': 'Verificaçao'
    }
    issuers = getListIssuers()

    list_issuers = []
    if type(issuers) == list:
        for issuer in issuers:
            try:
                if issuer.ftpInvoiceFileSourcePath is not None:
                    configFtpMarketPay = configFTP(FTP_HOST=issuer.ftpHost, FTP_PORT=issuer.ftpPort, FTP_USERNAME=issuer.ftpUsername, FTP_PASSWORD=issuer.ftpPassword, S3_BUCKET="S3_BUCKET_NAME",
                                            PARENT_DIR_PATH=issuer.ftpInvoiceFileSourcePath, PROCESSED_DIR_PATH=issuer.ftpInvoiceFileTargetPath, FIXED_DIR_PATH=issuer.ftpUsername+"/")

                    ftp_obj = FTPIngestion(configFtpMarketPay)
                    ftp_obj.s3_bucket_name = S3_BUCKET_NAME

                    ftp_obj.create_ssh_connection()
                    ftp_obj.create_sftp_connection()

                    list_issuers.append(ftp_obj.initiate_ingestion(issuer.id))
            except:
                print(sys.exc_info()[0])
                send_slack_message(
                    "1-move-ftp-to-s3", f"Erro ao informar dados do cliente {issuer.ftpUsername} para a função de conexão com SFTP do cliente - Erro: {sys.exc_info()[0]}")


    else:
            configFtpMarketPay = configFTP(FTP_HOST=issuers.ftpHost, FTP_PORT=issuers.ftpPort, FTP_USERNAME=issuers.ftpUsername, FTP_PASSWORD=issuers.ftpPassword, S3_BUCKET="S3_BUCKET_NAME",
                                        PARENT_DIR_PATH=issuers.ftpInvoiceFileSourcePath, PROCESSED_DIR_PATH=issuers.ftpInvoiceFileTargetPath, FIXED_DIR_PATH=issuers.ftpUsername+"/")

            ftp_obj = FTPIngestion(configFtpMarketPay)
            ftp_obj.s3_bucket_name = "S3_BUCKET_NAME"

            ftp_obj.create_ssh_connection()
            ftp_obj.create_sftp_connection()

            list_issuers.append(ftp_obj.initiate_ingestion(issuers.id))

    return {
        'statusCode': 200,
        'body': 'Verificação dos SFTP efetuado com sucesso'
    }

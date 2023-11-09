package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"path/filepath"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/pkg/sftp"
	"golang.org/x/crypto/ssh"
)

type Horizon struct {
	IsUsed       bool   `json:"isUsed"`
	UrlBase      string `json:"urlBase"`
	Password     string `json:"password"`
	UserName     string `json:"userName"`
	TokenAccess  string `json:"tokenAccess"`
	TokenHorizon string `json:"tokenHorizon"`
}

type DataItem struct {
	ID                          string             `json:"id"`
	CreatedAt                   string             `json:"createdAt"`
	UpdatedAt                   string             `json:"updatedAt"`
	Name                        string             `json:"name"`
	ExternalId                  string             `json:"externalId"`
	Active                      bool               `json:"active"`
	FtpHost                     string             `json:"ftpHost"`
	FtpPort                     int                `json:"ftpPort"`
	FtpUsername                 string             `json:"ftpUsername"`
	FtpPassword                 string             `json:"ftpPassword"`
	FtpInvoiceFileSourcePath    string             `json:"ftpInvoiceFileSourcePath"`
	FtpInvoiceFileTargetPath    string             `json:"ftpInvoiceFileTargetPath"`
	BucketInvoiceFileTargetPath string             `json:"bucketInvoiceFileTargetPath"`
	LayoutType                  string             `json:"layoutType"`
	Config                      map[string]Horizon `json:"config"`
}

type Root struct {
	Data      []DataItem `json:"data"`
	Count     int        `json:"count"`
	Total     int        `json:"total"`
	Page      int        `json:"page"`
	PageCount int        `json:"pageCount"`
}

type SlackMessage struct {
	Text string `json:"text"`
}

type DatabricksJobRunRequest struct {
	JobID int `json:"job_id"`
}

func sendToSlack(message string) {
	webhookURL := "https://hooks.slack.com/services/T03E68ER141/B05TK210VUZ/xxxxxxxxxxx"
	slackBody, _ := json.Marshal(SlackMessage{Text: message})
	req, err := http.NewRequest(http.MethodPost, webhookURL, bytes.NewBuffer(slackBody))
	if err != nil {
		logMessage := fmt.Sprintf("%s - ERROR - Erro ao criar requisição para Slack: %v", time.Now().Format("2006-01-02 15:04:05"), err)
		log.Println(logMessage)
		return
	}

	req.Header.Add("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		logMessage := fmt.Sprintf("%s - ERROR - Erro ao enviar mensagem para Slack: %v", time.Now().Format("2006-01-02 15:04:05"), err)
		log.Println(logMessage)
		return
	}
	defer resp.Body.Close()
}

func startJobDatabricks() {
	// Defina as informações do Job que você deseja chamar
	jobID := 287062496108544 // ID do Job no Databricks

	// Crie uma estrutura com os dados da requisição
	requestBody := DatabricksJobRunRequest{
		JobID: jobID,
	}

	// Converta a estrutura para JSON
	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		fmt.Println("Erro ao converter para JSON:", err)
		return
	}

	// Faça a requisição HTTP POST para a API do Databricks
	apiURL := "https://xxxxxxx.cloud.databricks.com/api/2.0/jobs/run-now"
	apiToken := "xxxxxxxxxxxxxxx"

	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(jsonData))
	if err != nil {
		erroMsg := fmt.Sprintf("Erro ao criar requisição:", err)
		fmt.Printf(erroMsg)
		sendToSlack(erroMsg)
		return
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", apiToken))

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		erroMsg := fmt.Sprintf("Erro ao fazer requisição:", err)
		fmt.Printf(erroMsg)
		sendToSlack(erroMsg)
		return
	}
	defer resp.Body.Close()

	// Verifique o código de status da resposta
	if resp.StatusCode != http.StatusOK {
		erroMsg := fmt.Sprintf("Erro na resposta da API:", resp.Status)
		fmt.Printf(erroMsg)
		sendToSlack(erroMsg)
		return
	}

	fmt.Println("Job do Databricks chamado com sucesso!")
	sendToSlack("Job do Databricks chamado com sucesso!")
}

func main() {
	lambda.Start(HandleRequest)
}

func HandleRequest() {

	arquivosImport := 0
	countArquivos := 0
	resp, err := http.Get("xxxxxxxxxxxx")
	if err != nil {
		logMessage := fmt.Sprintf("%s - ERROR - Erro ao consumir a API: %v", time.Now().Format("2006-01-02 15:04:05"), err)
		log.Println(logMessage)
		sendToSlack(logMessage)
		return
	}
	defer resp.Body.Close()
	sendToSlack("[Asgard - lambda] Consumido emissores da API do atena")

	var issuers Root
	if err := json.NewDecoder(resp.Body).Decode(&issuers); err != nil {
		logMessage := fmt.Sprintf("%s - ERROR - Erro ao decodificar o JSON: %v", time.Now().Format("2006-01-02 15:04:05"), err)
		log.Println(logMessage)
		sendToSlack(logMessage)
		return
	}

	sess := session.Must(session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"), // Altere para a sua região
	}))

	s3svc := s3.New(sess)

	for _, issuer := range issuers.Data {
		config := &ssh.ClientConfig{
			User: issuer.FtpUsername,
			Auth: []ssh.AuthMethod{
				ssh.Password(issuer.FtpPassword),
			},
			HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		}

		connection, err := ssh.Dial("tcp", fmt.Sprintf("%s:%d", issuer.FtpHost, issuer.FtpPort), config)
		if err != nil {
			logMessage := fmt.Sprintf("%s - ERROR - Erro ao conectar ao SFTP: %v", time.Now().Format("2006-01-02 15:04:05"), err)
			log.Println(logMessage)
			sendToSlack(logMessage)
			continue
		}

		client, err := sftp.NewClient(connection)
		if err != nil {
			logMessage := fmt.Sprintf("%s - ERROR - Erro ao criar cliente SFTP: %v", time.Now().Format("2006-01-02 15:04:05"), err)
			log.Println(logMessage)
			sendToSlack(logMessage)
			continue
		}
		sendToSlack("[Asgard - lambda] Conectado com sucesso com servidor SFTP RPE/DOCK")

		// Lista arquivos do diretório
		files, err := client.ReadDir(issuer.FtpInvoiceFileSourcePath)
		if err != nil {
			log.Fatal(err)
		}
		for _, file := range files {
			log.Printf("Diretorios encontrados: %v", file.Name())
			countArquivos++
		}

		if countArquivos > 0 {

			for _, file := range files {

				// Fazer o download dos arquivos
				arquivo := fmt.Sprintf("%v%v", issuer.FtpInvoiceFileSourcePath, file.Name())

				ext := filepath.Ext(arquivo)
				if ext == ".fat" || ext == ".FAT" || ext == ".TXT" || ext == ".txt" || ext == ".zip" {
					log.Printf("Arquivos encontrados para importação: %v", arquivo)

					sendToSlack("[Asgard - lambda] Arquivos encontrados para importação: " + arquivo)

					//Encontrado arquivos de importação
					arquivosImport += 1

					srcFile, err := client.Open(arquivo)
					if err != nil {
						logMessage := fmt.Sprintf("%s - ERROR - Erro ao abrir arquivo no SFTP: %v", time.Now().Format("2006-01-02 15:04:05"), err)
						log.Println(logMessage)
						sendToSlack(logMessage)

						// Falha em qual quer etapa da importação retira da contagem de arquivos.
						arquivosImport -= 1
						continue
					}
					defer srcFile.Close()

					// Definir o caminho no S3
					t := time.Now()
					s3Path := fmt.Sprintf("%s/%d/%02d/%02d/%s/", issuer.LayoutType, t.Year(), t.Month(), t.Day(), issuer.ExternalId)
					_, err = s3svc.PutObject(&s3.PutObjectInput{
						Bucket: aws.String("invoice-file-s3-prod"),
						Key:    aws.String(s3Path + srcFile.Name()),
						Body:   srcFile,
					})
					if err != nil {
						logMessage := fmt.Sprintf("%s - ERROR - Erro ao enviar arquivo para o S3: %v", time.Now().Format("2006-01-02 15:04:05"), err)
						log.Println(logMessage)
						sendToSlack(logMessage)

						// Falha em qual quer etapa da importação retira da contagem de arquivos.
						arquivosImport -= 1
						continue
					}
					sendToSlack("[Asgard - lambda] Enviado arquivo com sucesso para o S3 " + arquivo)

					// Mover arquivo no SFTP
					err = client.Rename(arquivo, issuer.FtpInvoiceFileTargetPath)
					if err != nil {
						logMessage := fmt.Sprintf("%s - ERROR - Erro ao mover arquivo no SFTP para pasta processados: %v", time.Now().Format("2006-01-02 15:04:05"), err)
						log.Println(logMessage)
						sendToSlack(logMessage)

						// Falha em qual quer etapa da importação retira da contagem de arquivos.
						arquivosImport -= 1
						continue
					}

					client.Close()
					connection.Close()

				}
			}
		}

	}

	logMessage := fmt.Sprintf("%s - INFO - Processamento concluído!", time.Now().Format("2006-01-02 15:04:05"))
	log.Println(logMessage)
	sendToSlack(logMessage)

	//Caso arquivosImport seja maior ou igual 1 significa que tem arquivos importados e prontos para processamento
	if arquivosImport >= 1 {
		startJobDatabricks()
	}
}

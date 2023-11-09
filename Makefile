build:
	rm -f main 
	rm -f deployment.zip
	GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o main main.go
	zip deployment.zip main
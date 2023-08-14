terraform {
  backend "s3" {
    bucket  = "state-terraform-asgard"
    key     = "state/app/asgard/asgard.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
  required_version = ">= 0.15"
  required_providers { 
  aws = { 
    version = ">= 3.36.0" 
   }
  } 
}

provider "aws" {
  region = "us-east-1"
}

data "archive_file" "zip" {
  source_dir  = "${path.module}/../main/"
  type        = "zip"
  output_path = "${path.module}/../main/main.zip"
}


resource "aws_cloudwatch_log_group" "log_group" {
  name = "/aws/lambda/${var.function_name}"

  retention_in_days = 7
}


resource "aws_iam_role" "lambda_exec_role" {
  name        = "asgard_invoice"
  path        = "/"
  description = "Lambda que valida a existencia de arquivos para processamento nos SFTP da RPE/DOCK"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "function_logging_policy" {
  name   = "function-logging-asgard-policy"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        Action : [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect : "Allow",
        Resource : "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "function_logging_policy_attachment" {
  role = aws_iam_role.lambda_exec_role.id
  policy_arn = aws_iam_policy.function_logging_policy.arn
}

resource "aws_lambda_function" "asgard_lambda" {
  role             = "${aws_iam_role.lambda_exec_role.arn}"
  handler          = "main.lambda_handler"
  source_code_hash = filebase64sha256(data.archive_file.zip.output_path)


  runtime          = "python3.10"
  timeout     = 30
  memory_size = 128

  function_name    = "${var.function_name}"
  filename = data.archive_file.zip.output_path
  layers = ["${aws_lambda_layer_version.asgard-layer.arn}"]


  timeouts {
    create = "15m"
    update = "15m"
    delete = "15m"
  }

   depends_on = [
    aws_lambda_layer_version.asgard-layer
  ]
}

output "aws_lambda_function" {
  value = aws_lambda_function.asgard_lambda.function_name
}





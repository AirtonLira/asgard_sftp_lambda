resource "aws_lambda_layer_version" "asgard-layer" {
  filename            = "${path.module}/../build/asgard_package.zip"
  layer_name          = "asgard-layer"
  compatible_runtimes = ["python3.10"]
}
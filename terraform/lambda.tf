resource "aws_lambda_function" "my_lambda" {
    filename         = "${path.module}/../upload.zip"
    function_name    = "my_lambda_function"
    role             = aws_iam_role.lambda_role.arn
    handler          = "processing2.handler"
    runtime          = "python3.10"  # check (3.8 wont work with wrangler)
    # source_code_hash = filebase64sha256("${path.module}/../upload.zip")
    layers           = ["arn:aws:lambda:eu-west-2:336392948345:layer:AWSSDKPandas-Python310:8"]
    memory_size   = 1024
    timeout       = 60
environment {
    variables = {
    EXAMPLE_ENV_VAR = "value"
    }
}
}


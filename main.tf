# Provider configuration for AWS
provider "aws" {
  region = "eu-north-1"  # AWS region
}

# AWS Kinesis Stream resource
resource "aws_kinesis_stream" "data_stream" {
  name             = "data_stream_kinesis_070324"  # Name of the Kinesis stream
  shard_count      = 1  # Number of shards in the stream
  retention_period = 24  # Retention period for data in hours
}

# Generates a zip archive of Python code
data "archive_file" "zip_the_python_code" {
 type        = "zip"  # Type of archive
 source_dir  = "${path.module}/scripts/"  # Directory containing Python code to be zipped
 output_path = "${path.module}/scripts/transform.zip"  # Path for the generated zip archive
}

# AWS Lambda function resource
resource "aws_lambda_function" "processor" {
  function_name = "EventProcessor"  # Name of the Lambda function
  handler       = "transform.lambda_handler"  # Entry point for the Lambda function
  runtime       = "python3.8"  # Runtime environment for the Lambda function
  role          = aws_iam_role.lambda_role.arn  # IAM role for the Lambda function

  environment {  # Environment variables for the Lambda function
    variables = {
      TARGET_BUCKET = "s3-target-bucket-070324"  # Target S3 bucket name
    }
  }

  filename = "${path.module}/scripts/transform.zip"  # Path to the deployment package for the Lambda function
}

# Event source mapping from Kinesis to Lambda
resource "aws_lambda_event_source_mapping" "kinesis_to_lambda" {
  event_source_arn  = aws_kinesis_stream.data_stream.arn  # ARN of the Kinesis stream
  function_name     = aws_lambda_function.processor.arn  # ARN of the Lambda function
  starting_position = "LATEST"  # Starting position in the stream for the Lambda function
}

# AWS S3 bucket resource
resource "aws_s3_bucket" "target_bucket_070324" {
  bucket = "s3-target-bucket-070324"  # Name of the S3 bucket
  acl    = "private"  # Access control list for the bucket
}

# AWS DynamoDB table resource
resource "aws_dynamodb_table" "events_table" {
  name           = "EventsTable"  # Name of the DynamoDB table
  billing_mode   = "PROVISIONED"  # Billing mode for the table
  read_capacity  = 1  # Read capacity units for the table
  write_capacity = 1  # Write capacity units for the table
  hash_key       = "event_uuid"  # Hash key for the table

  attribute {  # Attribute definition for the hash key
    name = "event_uuid"  # Name of the attribute
    type = "S"  # Type of the attribute (String)
  }
}

# IAM user for Lambda
resource "aws_iam_user" "lambda_user" {
  name = "lambda_user"  # Name of the IAM user
}

# IAM policy for Lambda
resource "aws_iam_policy" "lambda_policy" {
  name = "lambda_policy"  # Name of the IAM policy

  policy = jsonencode({  # Policy document defining permissions
    Version = "2012-10-17",  # Version of the policy language
    Statement = [  # List of policy statements
      {
        Effect = "Allow",  # Allow or Deny actions
        Action = [  # List of actions allowed
          "s3:PutObject",  # Action to put an object in S3 bucket
          "s3:GetObject",  # Action to get an object from S3 bucket
          "kinesis:GetRecords",  # Action to get records from Kinesis stream
          "kinesis:GetShardIterator",  # Action to get shard iterator from Kinesis stream
          "kinesis:DescribeStream",  # Action to describe a Kinesis stream
          "kinesis:DescribeStreamSummary",  # Action to describe summary of Kinesis stream
          "kinesis:ListShards",  # Action to list shards of a Kinesis stream
          "kinesis:ListStreams",  # Action to list Kinesis streams
          "dynamodb:GetItem",  # Action to get an item from DynamoDB table
          "dynamodb:PutItem",  # Action to put an item into DynamoDB table
        ],
        Resource = [  # List of resources to which the actions apply
          "arn:aws:s3:::s3-target-bucket-070324/*",  # ARN of S3 bucket and objects
          "arn:aws:dynamodb:*:*:table/EventsTable",  # ARN of DynamoDB table
          aws_kinesis_stream.data_stream.arn  # ARN of Kinesis stream
        ]
      }
    ]
  })
}

# Attachment of IAM policy to IAM user
resource "aws_iam_user_policy_attachment" "lambda_attach" {
  user = aws_iam_user.lambda_user.name  # IAM user to attach policy
  policy_arn = aws_iam_policy.lambda_policy.arn  # ARN of the IAM policy
}

# IAM role for Lambda execution
resource "aws_iam_role" "lambda_role" {
  name = "lambda_execution_role"  # Name of the IAM role
  assume_role_policy = jsonencode({  # Policy document defining who can assume the role
    "Version" : "2012-10-17",  # Version of the policy language
    "Statement" : [  # List of policy statements
      {
        "Effect" : "Allow",  # Allow or Deny actions
        "Principal" : {  # Entity that is allowed or denied access
          "Service" : "lambda.amazonaws.com"  # Service allowed to assume the role
        },
        "Action" : "sts:AssumeRole"  # Action to allow assuming the role
      }
    ]
  })
}

# Attachment of IAM policy to IAM role
resource "aws_iam_role_policy_attachment" "lambda_role_attach" {
  role = aws_iam_role.lambda_role.name  # IAM role to attach policy
  policy_arn = aws_iam_policy.lambda_policy.arn  # ARN of the IAM policy
}

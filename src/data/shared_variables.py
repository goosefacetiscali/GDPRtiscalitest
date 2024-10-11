import json
import os
import boto3
from botocore.exceptions import ClientError

shared_variables = {}

# Ask user for bucket name
bucket_name = input("Please enter the bucket name: ")
shared_variables["bucket"] = bucket_name

def export_to_json():
    json_path = os.path.join('src', 'utils', 'shared_variables.json')
    
    with open(json_path, 'w') as json_file:
        json.dump(shared_variables, json_file, indent=4)
    print("Shared variables exported to JSON for Lambda at:", json_path)

def export_to_tfvars():
    tfvars_path = os.path.join('terraform', 'variables.tf')

    with open(tfvars_path, 'w') as tfvars_file:
        for key, value in shared_variables.items():
            tfvars_file.write(f'variable {key} {{\n')
            tfvars_file.write(f'    default = "{value}"\n')
            tfvars_file.write(f'}}\n\n')
    print("Shared variables exported to Terraform variables file at:", tfvars_path)

def create_s3_bucket(bucket_name):
    s3_client = boto3.client('s3')

    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': 'eu-west-2'  
            }
        )
        print(f"Bucket '{bucket_name}' created successfully.")
    except ClientError as e:
        print(f"Error creating bucket: {e}")

def create_provider_config(bucket_name):
    provider_config_path = os.path.join('terraform', 'provider.tf')

    with open(provider_config_path, 'w') as f:
        f.write(f"""
provider "aws" {{
    region = "eu-west-2"
}}

terraform {{ 
    required_providers {{
      aws = {{
        source = "hashicorp/aws"
        version = "5.66.0"
      }}
    }}

    backend "s3" {{
      bucket = "{bucket_name}"
      key    = "terraform.tfstate"
      region = "eu-west-2"
    }}
}}
""")
    print("Provider configuration created at:", provider_config_path)

if __name__ == "__main__":
    export_to_json()
    export_to_tfvars()
    create_s3_bucket(shared_variables["bucket"])
    create_provider_config(shared_variables["bucket"])
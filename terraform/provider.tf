
provider "aws" {
    region = "eu-west-2"
}

terraform { 
    required_providers {
      aws = {
        source = "hashicorp/aws"
        version = "5.66.0"
      }
    }

    backend "s3" {
      bucket = "gdproctober"
      key    = "terraform.tfstate"
      region = "eu-west-2"
    }
}

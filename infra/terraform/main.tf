###############################################################################
# Terraform — root module
# Replace provider config and backend with your own values before applying.
###############################################################################

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and configure for remote state:
  # backend "s3" {
  #   bucket = "my-tfstate"
  #   key    = "project-mono/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

# ----- Networking (placeholder) -----
module "vpc" {
  source = "./modules/vpc"
  # Pass variables as needed
}

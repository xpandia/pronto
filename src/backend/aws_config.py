"""
Pronto — AWS service configurations.
Bedrock, DynamoDB, S3, Lambda, and CDK/CloudFormation stubs.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

# ---------------------------------------------------------------------------
# Region / environment
# ---------------------------------------------------------------------------
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
STAGE: str = os.getenv("STAGE", "dev")
TABLE_PREFIX: str = f"pronto-{STAGE}"

# ---------------------------------------------------------------------------
# Bedrock
# ---------------------------------------------------------------------------
BEDROCK_CONFIG = Config(
    region_name=AWS_REGION,
    retries={"max_attempts": 3, "mode": "adaptive"},
    read_timeout=120,
    connect_timeout=5,
)

SUPPORTED_MODELS: dict[str, dict[str, Any]] = {
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {
        "provider": "anthropic",
        "display_name": "Claude 3.5 Sonnet v2",
        "max_tokens": 8192,
        "input_cost_per_1k": 0.003,
        "output_cost_per_1k": 0.015,
    },
    "anthropic.claude-3-5-haiku-20241022-v1:0": {
        "provider": "anthropic",
        "display_name": "Claude 3.5 Haiku",
        "max_tokens": 8192,
        "input_cost_per_1k": 0.001,
        "output_cost_per_1k": 0.005,
    },
    "anthropic.claude-3-opus-20240229-v1:0": {
        "provider": "anthropic",
        "display_name": "Claude 3 Opus",
        "max_tokens": 4096,
        "input_cost_per_1k": 0.015,
        "output_cost_per_1k": 0.075,
    },
    "amazon.titan-text-premier-v1:0": {
        "provider": "amazon",
        "display_name": "Amazon Titan Text Premier",
        "max_tokens": 3072,
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015,
    },
    "meta.llama3-1-70b-instruct-v1:0": {
        "provider": "meta",
        "display_name": "Llama 3.1 70B Instruct",
        "max_tokens": 2048,
        "input_cost_per_1k": 0.00099,
        "output_cost_per_1k": 0.00099,
    },
    "mistral.mistral-large-2407-v1:0": {
        "provider": "mistral",
        "display_name": "Mistral Large (24.07)",
        "max_tokens": 8192,
        "input_cost_per_1k": 0.004,
        "output_cost_per_1k": 0.012,
    },
}


@lru_cache(maxsize=1)
def get_bedrock_runtime_client():
    """Return a cached Bedrock Runtime client."""
    return boto3.client(
        "bedrock-runtime",
        config=BEDROCK_CONFIG,
    )


@lru_cache(maxsize=1)
def get_bedrock_client():
    """Return a cached Bedrock management client."""
    return boto3.client("bedrock", region_name=AWS_REGION)


# ---------------------------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------------------------
DYNAMODB_TABLES: dict[str, dict[str, Any]] = {
    "prompts": {
        "TableName": f"{TABLE_PREFIX}-prompts",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},   # USER#<user_id>
            {"AttributeName": "sk", "KeyType": "RANGE"},   # PROMPT#<prompt_id>
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "gsi1pk", "AttributeType": "S"},
            {"AttributeName": "gsi1sk", "AttributeType": "S"},
            {"AttributeName": "gsi2pk", "AttributeType": "S"},
            {"AttributeName": "gsi2sk", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "gsi1pk", "KeyType": "HASH"},  # PROMPT#<prompt_id>
                    {"AttributeName": "gsi1sk", "KeyType": "RANGE"},  # VERSION#<version>
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI2",
                "KeySchema": [
                    {"AttributeName": "gsi2pk", "KeyType": "HASH"},  # MARKETPLACE
                    {"AttributeName": "gsi2sk", "KeyType": "RANGE"},  # <category>#<score>
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    "evaluations": {
        "TableName": f"{TABLE_PREFIX}-evaluations",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},   # PROMPT#<prompt_id>
            {"AttributeName": "sk", "KeyType": "RANGE"},   # EVAL#<eval_id>
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    "ab_tests": {
        "TableName": f"{TABLE_PREFIX}-ab-tests",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},   # USER#<user_id>
            {"AttributeName": "sk", "KeyType": "RANGE"},   # ABTEST#<test_id>
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    "analytics": {
        "TableName": f"{TABLE_PREFIX}-analytics",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},   # PROMPT#<prompt_id>
            {"AttributeName": "sk", "KeyType": "RANGE"},   # TS#<iso_timestamp>
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "AttributeName": "ttl",
            "Enabled": True,
        },
    },
    "users": {
        "TableName": f"{TABLE_PREFIX}-users",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},   # USER#<user_id>
            {"AttributeName": "sk", "KeyType": "RANGE"},   # PROFILE
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
}


@lru_cache(maxsize=1)
def get_dynamodb_resource():
    return boto3.resource("dynamodb", region_name=AWS_REGION)


def get_table(table_key: str):
    """Return a DynamoDB Table resource for the given logical name."""
    ddb = get_dynamodb_resource()
    return ddb.Table(DYNAMODB_TABLES[table_key]["TableName"])


def ensure_tables_exist() -> list[str]:
    """Create DynamoDB tables if they do not already exist (for local dev)."""
    ddb_client = boto3.client("dynamodb", region_name=AWS_REGION)
    existing = ddb_client.list_tables()["TableNames"]
    created: list[str] = []
    for _key, schema in DYNAMODB_TABLES.items():
        if schema["TableName"] not in existing:
            params = {
                k: v
                for k, v in schema.items()
                if k != "TimeToLiveSpecification"
            }
            ddb_client.create_table(**params)
            created.append(schema["TableName"])
            # Enable TTL separately if specified
            ttl_spec = schema.get("TimeToLiveSpecification")
            if ttl_spec:
                ddb_client.update_time_to_live(
                    TableName=schema["TableName"],
                    TimeToLiveSpecification=ttl_spec,
                )
    return created


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------
S3_BUCKET_NAME: str = os.getenv("PRONTO_S3_BUCKET", f"{TABLE_PREFIX}-artifacts")

S3_BUCKET_CONFIG: dict[str, Any] = {
    "Bucket": S3_BUCKET_NAME,
    "CreateBucketConfiguration": {"LocationConstraint": AWS_REGION}
    if AWS_REGION != "us-east-1"
    else {},
    "VersioningConfiguration": {"Status": "Enabled"},
    "ServerSideEncryptionConfiguration": {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                },
                "BucketKeyEnabled": True,
            }
        ]
    },
    "LifecycleConfiguration": {
        "Rules": [
            {
                "ID": "archive-old-artifacts",
                "Status": "Enabled",
                "Transitions": [
                    {"Days": 90, "StorageClass": "STANDARD_IA"},
                    {"Days": 365, "StorageClass": "GLACIER"},
                ],
            }
        ]
    },
    "Prefixes": {
        "prompt_exports": "exports/prompts/",
        "evaluation_results": "evaluations/",
        "ab_test_reports": "ab-tests/reports/",
        "user_uploads": "uploads/",
    },
}


@lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


# ---------------------------------------------------------------------------
# Lambda function stubs
# ---------------------------------------------------------------------------
LAMBDA_FUNCTIONS: dict[str, dict[str, Any]] = {
    "prompt-evaluator": {
        "FunctionName": f"{TABLE_PREFIX}-prompt-evaluator",
        "Runtime": "python3.12",
        "Handler": "handler.evaluate_prompt",
        "Timeout": 300,
        "MemorySize": 512,
        "Description": "Runs a prompt against a target model and records metrics.",
        "Environment": {
            "Variables": {
                "STAGE": STAGE,
                "TABLE_PREFIX": TABLE_PREFIX,
            }
        },
    },
    "ab-test-analyzer": {
        "FunctionName": f"{TABLE_PREFIX}-ab-test-analyzer",
        "Runtime": "python3.12",
        "Handler": "handler.analyze_ab_test",
        "Timeout": 120,
        "MemorySize": 256,
        "Description": "Computes statistical significance for A/B prompt tests.",
        "Environment": {
            "Variables": {
                "STAGE": STAGE,
                "TABLE_PREFIX": TABLE_PREFIX,
            }
        },
    },
    "marketplace-indexer": {
        "FunctionName": f"{TABLE_PREFIX}-marketplace-indexer",
        "Runtime": "python3.12",
        "Handler": "handler.index_prompt",
        "Timeout": 60,
        "MemorySize": 256,
        "Description": "Indexes published prompts for marketplace search.",
    },
    "analytics-aggregator": {
        "FunctionName": f"{TABLE_PREFIX}-analytics-aggregator",
        "Runtime": "python3.12",
        "Handler": "handler.aggregate",
        "Timeout": 300,
        "MemorySize": 512,
        "Description": "Aggregates per-prompt analytics into daily/weekly rollups.",
    },
}


def invoke_lambda(function_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Invoke a Lambda function synchronously and return its parsed response."""
    client = boto3.client("lambda", region_name=AWS_REGION)
    resp = client.invoke(
        FunctionName=LAMBDA_FUNCTIONS[function_key]["FunctionName"],
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    return json.loads(resp["Payload"].read())


def invoke_lambda_async(function_key: str, payload: dict[str, Any]) -> str:
    """Fire-and-forget Lambda invocation. Returns the request ID."""
    client = boto3.client("lambda", region_name=AWS_REGION)
    resp = client.invoke(
        FunctionName=LAMBDA_FUNCTIONS[function_key]["FunctionName"],
        InvocationType="Event",
        Payload=json.dumps(payload),
    )
    return resp["ResponseMetadata"]["RequestId"]


# ---------------------------------------------------------------------------
# CDK / CloudFormation template stub
# ---------------------------------------------------------------------------
def generate_cloudformation_template() -> dict[str, Any]:
    """Generate a minimal CloudFormation template for all Pronto resources."""
    resources: dict[str, Any] = {}

    # DynamoDB tables
    for key, schema in DYNAMODB_TABLES.items():
        logical_id = f"ProntoTable{''.join(w.capitalize() for w in key.split('_'))}"
        resource: dict[str, Any] = {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "TableName": schema["TableName"],
                "KeySchema": schema["KeySchema"],
                "AttributeDefinitions": schema["AttributeDefinitions"],
                "BillingMode": schema["BillingMode"],
            },
        }
        if "GlobalSecondaryIndexes" in schema:
            resource["Properties"]["GlobalSecondaryIndexes"] = schema[
                "GlobalSecondaryIndexes"
            ]
        if "TimeToLiveSpecification" in schema:
            resource["Properties"]["TimeToLiveSpecification"] = schema[
                "TimeToLiveSpecification"
            ]
        resources[logical_id] = resource

    # S3 bucket
    resources["ProntoArtifactsBucket"] = {
        "Type": "AWS::S3::Bucket",
        "Properties": {
            "BucketName": S3_BUCKET_NAME,
            "VersioningConfiguration": {"Status": "Enabled"},
            "BucketEncryption": S3_BUCKET_CONFIG[
                "ServerSideEncryptionConfiguration"
            ],
        },
    }

    # Lambda functions
    for key, fn_cfg in LAMBDA_FUNCTIONS.items():
        logical_id = f"ProntoLambda{''.join(w.capitalize() for w in key.split('-'))}"
        resources[logical_id] = {
            "Type": "AWS::Lambda::Function",
            "Properties": {
                "FunctionName": fn_cfg["FunctionName"],
                "Runtime": fn_cfg["Runtime"],
                "Handler": fn_cfg["Handler"],
                "Timeout": fn_cfg["Timeout"],
                "MemorySize": fn_cfg["MemorySize"],
                "Description": fn_cfg.get("Description", ""),
                "Role": {"Fn::GetAtt": ["ProntoLambdaExecutionRole", "Arn"]},
            },
        }

    # IAM execution role for Lambdas
    resources["ProntoLambdaExecutionRole"] = {
        "Type": "AWS::IAM::Role",
        "Properties": {
            "RoleName": f"{TABLE_PREFIX}-lambda-role",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
            "ManagedPolicyArns": [
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            ],
            "Policies": [
                {
                    "PolicyName": "ProntoDynamoDBAccess",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "dynamodb:GetItem",
                                    "dynamodb:PutItem",
                                    "dynamodb:UpdateItem",
                                    "dynamodb:DeleteItem",
                                    "dynamodb:Query",
                                    "dynamodb:Scan",
                                ],
                                "Resource": "*",
                            }
                        ],
                    },
                },
                {
                    "PolicyName": "ProntoBedrockAccess",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "bedrock:InvokeModel",
                                    "bedrock:InvokeModelWithResponseStream",
                                ],
                                "Resource": "*",
                            }
                        ],
                    },
                },
            ],
        },
    }

    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": f"Pronto backend infrastructure ({STAGE})",
        "Resources": resources,
        "Outputs": {
            "PromptsTableName": {
                "Value": DYNAMODB_TABLES["prompts"]["TableName"],
            },
            "ArtifactsBucketName": {"Value": S3_BUCKET_NAME},
        },
    }

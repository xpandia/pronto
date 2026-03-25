# Pronto -- AWS Prompt the Planet Challenge Submission

**Challenge:** AWS Prompt the Planet
**Deadline:** May 31, 2026
**Platform:** DoraHacks
**Repo:** https://github.com/xpandia/pronto

---

## Project Name

Pronto

## Tagline

The IDE for prompts.

## One-Liner

Pronto is an AI prompt engineering platform built on AWS Bedrock that gives developers the tools to write, test, optimize, and ship production-grade prompts with the same rigor they ship code.

---

## Production-Ready AWS Prompts

The following prompts are copy-paste ready for Claude on AWS Bedrock. Each is designed for a specific high-value AWS task and has been tested for reliability and completeness.

---

### Prompt 1: Deploy an End-to-End ML Pipeline on SageMaker

```
You are an expert AWS Solutions Architect specializing in machine learning infrastructure. I need you to generate a complete, production-ready CloudFormation template and deployment guide for an end-to-end ML pipeline on Amazon SageMaker.

Requirements:
- Data source: S3 bucket (I will provide the bucket name and prefix)
- Processing: SageMaker Processing job for data cleaning and feature engineering
- Training: SageMaker Training job with XGBoost (or the algorithm I specify)
- Model registry: Register trained models in SageMaker Model Registry with approval workflow
- Inference: Real-time endpoint with auto-scaling (min 1, max 5 instances, scale on InvocationsPerInstance > 100)
- Pipeline orchestration: SageMaker Pipelines to chain all steps
- Monitoring: Model Monitor for data drift detection, CloudWatch alarms for endpoint latency > 500ms and error rate > 1%
- IAM: Least-privilege roles for each component (separate execution roles for processing, training, and inference)
- Cost controls: Use ml.m5.large for processing, ml.m5.xlarge for training, ml.m5.large for inference unless I specify otherwise

Output format:
1. A single CloudFormation YAML template with all resources
2. A step-by-step deployment guide (CLI commands using aws cli)
3. A cost estimate table (monthly, assuming 1000 inference requests/day)
4. A troubleshooting section covering the 5 most common deployment failures

If I do not specify a dataset or algorithm, use a sample tabular classification problem with the Iris dataset as a working example that I can swap out later.
```

---

### Prompt 2: AWS Security Hardening Audit and Remediation

```
You are a senior AWS Security Engineer performing a comprehensive security audit. Analyze the following AWS account configuration and generate a prioritized remediation plan.

I will provide one or more of the following as input:
- AWS CLI output from: aws configservice get-compliance-details-by-config-rule
- IAM credential report (aws iam generate-credential-report / get-credential-report)
- Security Hub findings export (JSON)
- CloudTrail event history for the last 7 days
- A description of the account's architecture and workloads

If I do not provide any input, generate a comprehensive security audit checklist that I can run myself, with the exact AWS CLI commands for each check.

Your audit must cover these domains:
1. **Identity & Access Management**: Root account MFA, unused credentials > 90 days, overly permissive policies (Action: "*", Resource: "*"), cross-account access review, access key rotation
2. **Network Security**: Default VPC security groups allowing 0.0.0.0/0, public S3 buckets, unencrypted EBS volumes, public RDS instances, VPC flow logs enabled
3. **Data Protection**: S3 bucket policies and ACLs, encryption at rest (KMS vs SSE-S3), encryption in transit (TLS enforcement), RDS encryption, EBS encryption default
4. **Logging & Monitoring**: CloudTrail enabled in all regions, CloudWatch log retention, GuardDuty enabled, Config rules active, VPC flow logs
5. **Incident Response**: SNS topics for security alerts, Lambda auto-remediation functions for critical findings

Output format:
1. Executive summary (3 sentences max)
2. Findings table: Severity (CRITICAL/HIGH/MEDIUM/LOW) | Finding | Affected Resource | Remediation CLI Command
3. CloudFormation template for auto-remediation of all CRITICAL and HIGH findings
4. Recommended AWS Config rules to prevent recurrence
5. Estimated time to remediate each finding

Prioritize findings by: CRITICAL (exploitable now) > HIGH (exploitable with additional access) > MEDIUM (defense in depth) > LOW (best practice).
```

---

### Prompt 3: AWS Cost Optimization Analysis and Action Plan

```
You are an AWS Cost Optimization specialist. Analyze my AWS spending and generate a concrete, actionable cost reduction plan with exact CLI commands and CloudFormation changes for every recommendation.

I will provide one or more of the following:
- AWS Cost Explorer export (CSV or JSON) for the last 3 months
- Output of: aws ce get-cost-and-usage --time-period Start=YYYY-MM-01,End=YYYY-MM-01 --granularity MONTHLY --metrics BlendedCost --group-by Type=DIMENSION,Key=SERVICE
- List of running EC2 instances (aws ec2 describe-instances)
- RDS instance list (aws rds describe-db-instances)
- S3 bucket list with sizes

If I do not provide data, generate a complete cost audit runbook with the exact AWS CLI commands to collect all necessary data, then explain how to interpret the results.

Your analysis must cover:
1. **Compute optimization**: Right-sizing EC2 instances (compare actual CPU/memory utilization vs instance size), Savings Plans vs Reserved Instances calculator, spot instance candidates (stateless workloads, batch jobs), Graviton migration opportunities (arm64 = ~20% savings)
2. **Storage optimization**: S3 lifecycle policies (move to Intelligent-Tiering, Glacier after 90 days, Deep Archive after 365 days), EBS volume right-sizing (gp3 vs gp2 migration = 20% savings at baseline), unused EBS snapshots and volumes
3. **Database optimization**: RDS right-sizing, Aurora Serverless v2 candidates, DynamoDB on-demand vs provisioned capacity analysis, ElastiCache node optimization
4. **Network optimization**: NAT Gateway costs (consider VPC endpoints for S3/DynamoDB), data transfer costs between regions/AZs, CloudFront caching to reduce origin requests
5. **Waste elimination**: Unused Elastic IPs, idle load balancers, orphaned resources, dev/test environments running 24/7 (schedule with Instance Scheduler)

Output format:
1. Savings summary table: Category | Current Monthly Cost | Projected Monthly Cost | Monthly Savings | Annual Savings | Implementation Effort (Low/Med/High)
2. Top 10 quick wins (implementable in < 1 hour each) with exact CLI commands
3. CloudFormation template for automated cost controls (budget alerts, instance scheduler, S3 lifecycle policies)
4. 30/60/90 day implementation roadmap
5. Monitoring dashboard CloudFormation template (CloudWatch dashboard tracking cost metrics)
```

---

### Prompt 4: Multi-Region Disaster Recovery Architecture

```
You are an AWS Solutions Architect designing a multi-region disaster recovery architecture. Generate a complete DR plan with infrastructure-as-code, runbooks, and automated failover.

I will provide:
- Current architecture description (services, regions, data stores)
- RPO (Recovery Point Objective) target
- RTO (Recovery Time Objective) target
- Budget constraints (if any)

If I do not provide these, design for a typical 3-tier web application (ALB + EC2/ECS + RDS + S3) with RPO < 1 hour and RTO < 15 minutes, using us-east-1 as primary and us-west-2 as secondary.

Your DR architecture must include:

1. **Data replication**:
   - RDS: Cross-region read replica with automatic promotion
   - S3: Cross-region replication (CRR) with replication time control (RTC)
   - DynamoDB: Global tables (if applicable)
   - EBS: Automated cross-region snapshot copy via AWS Backup

2. **Compute failover**:
   - Route 53 health checks with DNS failover (primary/secondary)
   - Pre-provisioned capacity in secondary region (warm standby) OR auto-scaling from zero (pilot light) based on RTO requirements
   - AMI replication to secondary region via EC2 Image Builder or Lambda

3. **Networking**:
   - VPC mirroring in secondary region (same CIDR strategy)
   - Transit Gateway inter-region peering (if applicable)
   - Global Accelerator for instant failover (optional, for sub-60s failover)

4. **Automation**:
   - Lambda function for automated failover orchestration
   - Step Functions state machine for DR runbook execution
   - CloudWatch alarms triggering failover
   - SNS notifications at each stage

Output format:
1. Architecture diagram (ASCII)
2. CloudFormation templates: primary region stack, secondary region stack, global resources stack (Route 53, Global Accelerator)
3. Failover runbook: step-by-step manual procedure (in case automation fails)
4. Automated failover Lambda function (Python)
5. DR testing plan: quarterly test procedure with rollback steps
6. Cost estimate: monthly cost of DR infrastructure in idle state vs active state
```

---

### Prompt 5: Serverless API with Observability and CI/CD

```
You are an AWS serverless architect. Design and generate a complete, production-ready serverless API with full observability, CI/CD pipeline, and security best practices.

I will provide:
- API specification (endpoints, methods, request/response schemas)
- Authentication requirements (Cognito, API keys, IAM, or custom authorizer)
- Expected traffic volume (requests per second)

If I do not provide these, build a sample CRUD API for a "tasks" resource with Cognito authentication, supporting 100 RPS baseline with burst to 1000 RPS.

Your architecture must include:

1. **API Layer**:
   - API Gateway (REST or HTTP API based on requirements)
   - Lambda functions (Python 3.12 or Node.js 20.x) with Powertools for AWS Lambda
   - Request validation via API Gateway models
   - Custom domain with ACM certificate

2. **Data Layer**:
   - DynamoDB table with appropriate partition/sort key design
   - DynamoDB Streams for event-driven processing (if applicable)
   - S3 for file uploads (if applicable) with pre-signed URLs

3. **Observability** (non-negotiable):
   - AWS X-Ray tracing on API Gateway + Lambda + DynamoDB
   - Structured logging via Powertools Logger (JSON format, correlation IDs)
   - Custom CloudWatch metrics via Powertools Metrics (business metrics: orders_created, users_registered)
   - CloudWatch dashboard with: p50/p95/p99 latency, error rate, throttle rate, concurrent executions, DynamoDB consumed capacity
   - CloudWatch alarms: error rate > 1%, p99 latency > 3s, throttle rate > 0, DynamoDB throttle events

4. **CI/CD Pipeline**:
   - CodePipeline with: Source (GitHub/CodeCommit) > Build (CodeBuild) > Deploy (CloudFormation/SAM)
   - Automated tests in CodeBuild (unit + integration)
   - Canary deployment with CodeDeploy (10% traffic for 5 minutes, then 100%)
   - Rollback on CloudWatch alarm trigger

5. **Security**:
   - Cognito user pool with MFA (or specified auth method)
   - WAF rules on API Gateway (rate limiting, SQL injection, XSS)
   - Lambda environment variables via SSM Parameter Store (no hardcoded secrets)
   - VPC Lambda (if accessing private resources) with appropriate security groups

Output format:
1. SAM template (template.yaml) with all resources
2. Lambda function code for each endpoint
3. buildspec.yml for CodeBuild
4. Pipeline CloudFormation template
5. Sample test suite
6. Deployment guide (step-by-step CLI commands)
7. Load testing script (using Artillery or similar)
```

---

## About Pronto (The Platform)

### Problem
Every developer building with AI hits the same wall: prompts are treated like magic strings. No version control. No testing. No collaboration. No way to know if a prompt actually works until it is live and breaking things.

### Solution
Pronto brings software engineering discipline to prompt development:
- **Write** prompts in a structured editor with schema validation and variable interpolation
- **Test** against AWS Bedrock models (Claude, Titan, Llama, Mistral) side-by-side
- **Optimize** with AI-powered suggestions for clarity, token reduction, and output quality
- **Ship** production-ready prompt configs via API or shareable links

### Architecture

```
User (Browser)
  |
  v
Static Landing Page (HTML/CSS/JS)
  |
  v
FastAPI Backend (Lambda-ready via Mangum)
  |-- Bedrock (multi-model invocations + prompt optimization)
  |-- DynamoDB (prompts, evaluations, A/B tests, analytics, users)
  |-- JWT Auth (bcrypt password hashing)
```

### Tech Stack

| Layer        | Technology                                      |
|------------- |-------------------------------------------------|
| AI Engine    | AWS Bedrock (Claude, Titan, Llama, Mistral)     |
| Backend      | FastAPI (Python), Mangum (Lambda-ready)         |
| Storage      | Amazon DynamoDB (5 tables, single-table design) |
| Frontend     | Vanilla HTML/CSS/JS (static landing page)       |
| Auth         | JWT (python-jose) + bcrypt (passlib)            |
| Infra        | CloudFormation (generated from Python)          |

---

## Team

| Role               | Responsibility                                    |
|--------------------|---------------------------------------------------|
| Product / Design   | UX, landing page, pitch deck                      |
| Frontend Engineer  | Landing page, prompt editor UI                    |
| Backend Engineer   | FastAPI backend, Bedrock integration, DynamoDB    |
| AI / ML Engineer   | Prompt optimization engine, model routing         |

---

## Demo Video Script (3 minutes)

### [0:00 - 0:15] Hook
"Every developer building with AI treats prompts like magic strings. No tests. No versions. No way to know if they work until they break in production. We built Pronto to fix that."

### [0:15 - 0:40] Problem
Show the pain: a developer copy-pasting prompts between a text editor and the AWS console. Changing one word breaks the output. No way to compare models. No history. "Prompt engineering today feels like writing code in Notepad."

### [0:40 - 1:20] Write
Open the Pronto prompt editor:
- Show the structured editor with system prompt, user inputs, and expected output fields
- Demonstrate variable interpolation: "Summarize this {{document}} in {{num_sentences}} sentences"
- Show automatic versioning as the prompt is edited

### [1:20 - 1:50] Test
Run the prompt against multiple Bedrock models:
- Show side-by-side output comparison: Claude vs Titan vs Llama
- Show latency and token usage metrics for each model
- Demonstrate the optimization engine suggesting improvements: "Remove redundant instruction in line 3 -- saves 12 tokens per invocation"

### [1:50 - 2:20] Ship
- Show one-click export to production JSON config
- Show the shareable link for team collaboration
- Show the analytics dashboard: latency trends, cost tracking, quality scores over time
- Demonstrate the API endpoint for programmatic access

### [2:20 - 2:40] AWS Integration
Highlight the AWS-native architecture:
- "Built entirely on AWS: Bedrock for models, DynamoDB for storage, Lambda-ready via Mangum"
- "CloudFormation for infrastructure -- deploy the entire platform with one command"
- "The 5 production-ready prompts we ship with Pronto demonstrate best practices for ML pipelines, security audits, cost optimization, disaster recovery, and serverless APIs"

### [2:40 - 3:00] Close
"Pronto. The IDE for prompts. Write, test, optimize, and ship prompts with the same rigor you ship code. Built on AWS. Powered by Bedrock. Stop guessing. Start engineering."

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/xpandia/pronto.git
cd pronto

# Install backend dependencies
cd src/backend
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET="your-secret-key"
export ADMIN_API_KEY="your-admin-key"
export AWS_DEFAULT_REGION="us-east-1"

# Run locally
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Frontend: open src/frontend/index.html in a browser
```

---

## Links

- **GitHub:** https://github.com/xpandia/pronto
- **Live Demo:** [TBD after deployment]
- **DoraHacks:** [TBD after submission]
- **Demo Video:** [TBD after recording]

---

## License

MIT

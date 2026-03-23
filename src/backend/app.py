"""
Pronto — The IDE for Prompts
FastAPI backend: CRUD, evaluation, A/B testing, marketplace, analytics.
"""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Query, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel, Field

from aws_config import (
    SUPPORTED_MODELS,
    get_bedrock_runtime_client,
    get_table,
    get_s3_client,
    S3_BUCKET_NAME,
    generate_cloudformation_template,
)

# ═══════════════════════════════════════════════════════════════════════════
# Security configuration
# ═══════════════════════════════════════════════════════════════════════════
JWT_SECRET: str = os.environ.get("JWT_SECRET", "change-me-before-production")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_HOURS: int = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ADMIN_API_KEY: str = os.environ.get("ADMIN_API_KEY", "pronto-admin-dev-key")

# ═══════════════════════════════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Pronto API",
    description="The IDE for Prompts — backend service",
    version="0.1.0",
)
ALLOWED_ORIGINS: list[str] = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════
# Pydantic models
# ═══════════════════════════════════════════════════════════════════════════

class PromptVisibility(str, Enum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class PromptVariable(BaseModel):
    name: str
    description: str = ""
    default_value: str = ""


class PromptCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    system_prompt: str = ""
    user_prompt: str = Field(..., min_length=1)
    variables: list[PromptVariable] = []
    tags: list[str] = []
    category: str = "general"
    visibility: PromptVisibility = PromptVisibility.PRIVATE
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)


class PromptUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: list[PromptVariable] | None = None
    tags: list[str] | None = None
    category: str | None = None
    visibility: PromptVisibility | None = None
    model_id: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)


class PromptResponse(BaseModel):
    prompt_id: str
    user_id: str
    version: int
    title: str
    description: str
    system_prompt: str
    user_prompt: str
    variables: list[PromptVariable]
    tags: list[str]
    category: str
    visibility: str
    model_id: str
    temperature: float
    max_tokens: int
    created_at: str
    updated_at: str


class EvalRequest(BaseModel):
    prompt_id: str
    model_ids: list[str] = []
    test_inputs: list[dict[str, str]] = [{}]
    temperature: float | None = None
    max_tokens: int | None = None
    num_runs: int = Field(default=1, ge=1, le=10)


class EvalResult(BaseModel):
    eval_id: str
    prompt_id: str
    model_id: str
    input_variables: dict[str, str]
    output: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_estimate: float
    run_index: int


class ABTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    prompt_a_id: str
    prompt_b_id: str
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    test_inputs: list[dict[str, str]] = [{}]
    num_runs: int = Field(default=3, ge=1, le=20)


class ABTestResult(BaseModel):
    test_id: str
    name: str
    prompt_a_id: str
    prompt_b_id: str
    model_id: str
    results_a: list[EvalResult]
    results_b: list[EvalResult]
    summary: dict[str, Any]
    created_at: str


class MarketplacePublish(BaseModel):
    prompt_id: str
    price: float = 0.0
    license: str = "MIT"


class MarketplaceEntry(BaseModel):
    prompt_id: str
    user_id: str
    title: str
    description: str
    category: str
    tags: list[str]
    price: float
    license: str
    downloads: int
    avg_rating: float
    published_at: str


class AnalyticsResponse(BaseModel):
    prompt_id: str
    total_runs: int
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: float
    total_cost: float
    runs_by_model: dict[str, int]


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


# ═══════════════════════════════════════════════════════════════════════════
# Auth stubs
# ═══════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _create_access_token(user_id: str) -> str:
    """Create a signed JWT for the given user."""
    from datetime import timedelta
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> str:
    """Extract and validate user_id from a JWT Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _require_admin(
    x_admin_key: str | None = Header(default=None),
) -> None:
    """Verify the admin API key for sensitive endpoints."""
    if not x_admin_key or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing admin API key")


# ═══════════════════════════════════════════════════════════════════════════
# Bedrock invocation helpers
# ═══════════════════════════════════════════════════════════════════════════

def _render_prompt(template: str, variables: dict[str, str]) -> str:
    """Replace {{var}} placeholders with supplied values."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def _invoke_model(
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Call a Bedrock model and return output + usage metrics."""
    client = get_bedrock_runtime_client()
    model_info = SUPPORTED_MODELS.get(model_id)
    if not model_info:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model: {model_id}. Supported: {list(SUPPORTED_MODELS)}",
        )

    effective_max = min(max_tokens, model_info["max_tokens"])
    provider = model_info["provider"]

    # Build provider-specific payloads
    if provider == "anthropic":
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": effective_max,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

    elif provider == "amazon":
        text_config = {"maxTokenCount": effective_max, "temperature": temperature}
        body = {
            "inputText": f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt,
            "textGenerationConfig": text_config,
        }

    elif provider == "meta":
        full_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        body = {
            "prompt": full_prompt,
            "max_gen_len": effective_max,
            "temperature": temperature,
        }

    elif provider == "mistral":
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        body = {
            "messages": messages,
            "max_tokens": effective_max,
            "temperature": temperature,
        }

    else:
        raise HTTPException(status_code=500, detail=f"Unknown provider: {provider}")

    t0 = time.perf_counter()
    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
    except ClientError as exc:
        raise HTTPException(status_code=502, detail=f"Bedrock error: {exc}") from exc

    latency_ms = (time.perf_counter() - t0) * 1000
    resp_body = json.loads(response["body"].read())

    # Parse provider-specific responses
    if provider == "anthropic":
        output_text = resp_body["content"][0]["text"]
        input_tokens = resp_body["usage"]["input_tokens"]
        output_tokens = resp_body["usage"]["output_tokens"]
    elif provider == "amazon":
        output_text = resp_body["results"][0]["outputText"]
        input_tokens = resp_body.get("inputTextTokenCount", 0)
        output_tokens = resp_body["results"][0].get("tokenCount", 0)
    elif provider == "meta":
        output_text = resp_body["generation"]
        input_tokens = resp_body.get("prompt_token_count", 0)
        output_tokens = resp_body.get("generation_token_count", 0)
    elif provider == "mistral":
        output_text = resp_body["choices"][0]["message"]["content"]
        input_tokens = resp_body["usage"]["prompt_tokens"]
        output_tokens = resp_body["usage"]["completion_tokens"]
    else:
        output_text, input_tokens, output_tokens = "", 0, 0

    cost = (
        input_tokens / 1000 * model_info["input_cost_per_1k"]
        + output_tokens / 1000 * model_info["output_cost_per_1k"]
    )

    return {
        "output": output_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round(latency_ms, 2),
        "cost_estimate": round(cost, 6),
    }


# ═══════════════════════════════════════════════════════════════════════════
# DynamoDB helpers
# ═══════════════════════════════════════════════════════════════════════════

def _decimal_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def _to_dynamo(data: dict[str, Any]) -> dict[str, Any]:
    """Convert floats to Decimal for DynamoDB."""
    return json.loads(json.dumps(data, default=str), parse_float=Decimal)


def _from_dynamo(item: dict[str, Any]) -> dict[str, Any]:
    """Convert Decimals back to floats."""
    return json.loads(json.dumps(item, default=_decimal_default))


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Health
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pronto", "timestamp": _now_iso()}


@app.get("/models")
async def list_models():
    """Return all supported Bedrock models."""
    return {
        model_id: {
            "display_name": info["display_name"],
            "provider": info["provider"],
            "max_tokens": info["max_tokens"],
            "input_cost_per_1k": info["input_cost_per_1k"],
            "output_cost_per_1k": info["output_cost_per_1k"],
        }
        for model_id, info in SUPPORTED_MODELS.items()
    }


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Prompt CRUD
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/prompts", response_model=PromptResponse, status_code=201)
async def create_prompt(
    body: PromptCreate,
    user_id: str = Depends(get_current_user),
):
    table = get_table("prompts")
    prompt_id = _new_id()
    now = _now_iso()
    item = {
        "pk": f"USER#{user_id}",
        "sk": f"PROMPT#{prompt_id}",
        "gsi1pk": f"PROMPT#{prompt_id}",
        "gsi1sk": "VERSION#1",
        "prompt_id": prompt_id,
        "user_id": user_id,
        "version": 1,
        "title": body.title,
        "description": body.description,
        "system_prompt": body.system_prompt,
        "user_prompt": body.user_prompt,
        "variables": [v.model_dump() for v in body.variables],
        "tags": body.tags,
        "category": body.category,
        "visibility": body.visibility.value,
        "model_id": body.model_id,
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
        "created_at": now,
        "updated_at": now,
    }
    table.put_item(Item=_to_dynamo(item))
    return _from_dynamo(item)


@app.get("/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    version: int | None = None,
    user_id: str = Depends(get_current_user),
):
    table = get_table("prompts")
    if version:
        resp = table.query(
            IndexName="GSI1",
            KeyConditionExpression="gsi1pk = :pk AND gsi1sk = :sk",
            ExpressionAttributeValues={
                ":pk": f"PROMPT#{prompt_id}",
                ":sk": f"VERSION#{version}",
            },
        )
    else:
        # Get latest version — query by prompt_id across all versions, sort desc
        resp = table.query(
            IndexName="GSI1",
            KeyConditionExpression="gsi1pk = :pk AND begins_with(gsi1sk, :prefix)",
            ExpressionAttributeValues={
                ":pk": f"PROMPT#{prompt_id}",
                ":prefix": "VERSION#",
            },
            ScanIndexForward=False,
            Limit=1,
        )
    items = resp.get("Items", [])
    if not items:
        raise HTTPException(status_code=404, detail="Prompt not found")
    item = _from_dynamo(items[0])
    # Visibility check
    if item.get("visibility") == "private" and item.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return item


@app.get("/prompts", response_model=list[PromptResponse])
async def list_prompts(
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=50, le=100),
    category: str | None = None,
    tag: str | None = None,
):
    table = get_table("prompts")
    key_expr = "pk = :pk AND begins_with(sk, :prefix)"
    expr_values: dict[str, Any] = {
        ":pk": f"USER#{user_id}",
        ":prefix": "PROMPT#",
    }
    filter_parts: list[str] = []
    if category:
        filter_parts.append("category = :cat")
        expr_values[":cat"] = category
    if tag:
        filter_parts.append("contains(tags, :tag)")
        expr_values[":tag"] = tag

    kwargs: dict[str, Any] = {
        "KeyConditionExpression": key_expr,
        "ExpressionAttributeValues": expr_values,
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if filter_parts:
        kwargs["FilterExpression"] = " AND ".join(filter_parts)

    resp = table.query(**kwargs)
    return [_from_dynamo(i) for i in resp.get("Items", [])]


@app.put("/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    body: PromptUpdate,
    user_id: str = Depends(get_current_user),
):
    existing = await get_prompt(prompt_id, user_id=user_id)
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not the owner")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    merged = {**existing, **updates, "updated_at": _now_iso()}
    if "variables" in updates:
        merged["variables"] = [
            v.model_dump() if isinstance(v, PromptVariable) else v
            for v in updates["variables"]
        ]
    if "visibility" in updates:
        merged["visibility"] = updates["visibility"].value if isinstance(updates["visibility"], PromptVisibility) else updates["visibility"]

    table = get_table("prompts")
    merged["pk"] = f"USER#{user_id}"
    merged["sk"] = f"PROMPT#{prompt_id}"
    merged["gsi1pk"] = f"PROMPT#{prompt_id}"
    merged["gsi1sk"] = f"VERSION#{existing['version']}"
    table.put_item(Item=_to_dynamo(merged))
    return _from_dynamo(merged)


@app.delete("/prompts/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: str,
    user_id: str = Depends(get_current_user),
):
    existing = await get_prompt(prompt_id, user_id=user_id)
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not the owner")

    table = get_table("prompts")
    # Delete all versions
    resp = table.query(
        IndexName="GSI1",
        KeyConditionExpression="gsi1pk = :pk",
        ExpressionAttributeValues={":pk": f"PROMPT#{prompt_id}"},
    )
    with table.batch_writer() as batch:
        for item in resp.get("Items", []):
            batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})


@app.post("/prompts/{prompt_id}/version", response_model=PromptResponse, status_code=201)
async def create_version(
    prompt_id: str,
    body: PromptUpdate,
    user_id: str = Depends(get_current_user),
):
    """Create a new version of an existing prompt (copy-on-write)."""
    existing = await get_prompt(prompt_id, user_id=user_id)
    if existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not the owner")

    new_version = existing["version"] + 1
    now = _now_iso()
    updates = body.model_dump(exclude_none=True)
    merged = {**existing, **updates}
    merged["version"] = new_version
    merged["created_at"] = now
    merged["updated_at"] = now
    merged["pk"] = f"USER#{user_id}"
    merged["sk"] = f"PROMPT#{prompt_id}"
    merged["gsi1pk"] = f"PROMPT#{prompt_id}"
    merged["gsi1sk"] = f"VERSION#{new_version}"
    if "variables" in updates:
        merged["variables"] = [
            v.model_dump() if isinstance(v, PromptVariable) else v
            for v in updates["variables"]
        ]
    if "visibility" in updates:
        merged["visibility"] = updates["visibility"].value if isinstance(updates["visibility"], PromptVisibility) else updates["visibility"]

    table = get_table("prompts")
    table.put_item(Item=_to_dynamo(merged))
    return _from_dynamo(merged)


@app.get("/prompts/{prompt_id}/versions", response_model=list[PromptResponse])
async def list_versions(
    prompt_id: str,
    user_id: str = Depends(get_current_user),
):
    table = get_table("prompts")
    resp = table.query(
        IndexName="GSI1",
        KeyConditionExpression="gsi1pk = :pk AND begins_with(gsi1sk, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"PROMPT#{prompt_id}",
            ":prefix": "VERSION#",
        },
        ScanIndexForward=True,
    )
    items = resp.get("Items", [])
    if not items:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if items[0].get("visibility") == "private" and _from_dynamo(items[0]).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return [_from_dynamo(i) for i in items]


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Prompt evaluation engine
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/evaluate", response_model=list[EvalResult])
async def evaluate_prompt(
    body: EvalRequest,
    user_id: str = Depends(get_current_user),
):
    """Run a prompt against one or more models with given test inputs."""
    prompt = await get_prompt(body.prompt_id, user_id=user_id)
    model_ids = body.model_ids or [prompt["model_id"]]

    results: list[EvalResult] = []
    eval_table = get_table("evaluations")
    analytics_table = get_table("analytics")

    for model_id in model_ids:
        for test_input in body.test_inputs:
            rendered_user = _render_prompt(prompt["user_prompt"], test_input)
            rendered_system = _render_prompt(prompt["system_prompt"], test_input)

            for run_idx in range(body.num_runs):
                resp = _invoke_model(
                    model_id=model_id,
                    system_prompt=rendered_system,
                    user_prompt=rendered_user,
                    temperature=body.temperature if body.temperature is not None else prompt["temperature"],
                    max_tokens=body.max_tokens if body.max_tokens is not None else prompt["max_tokens"],
                )

                eval_id = _new_id()
                result = EvalResult(
                    eval_id=eval_id,
                    prompt_id=body.prompt_id,
                    model_id=model_id,
                    input_variables=test_input,
                    output=resp["output"],
                    input_tokens=resp["input_tokens"],
                    output_tokens=resp["output_tokens"],
                    latency_ms=resp["latency_ms"],
                    cost_estimate=resp["cost_estimate"],
                    run_index=run_idx,
                )
                results.append(result)

                # Persist evaluation record
                eval_item = {
                    "pk": f"PROMPT#{body.prompt_id}",
                    "sk": f"EVAL#{eval_id}",
                    **result.model_dump(),
                    "user_id": user_id,
                    "created_at": _now_iso(),
                }
                eval_table.put_item(Item=_to_dynamo(eval_item))

                # Record analytics event
                analytics_item = {
                    "pk": f"PROMPT#{body.prompt_id}",
                    "sk": f"TS#{_now_iso()}#{eval_id}",
                    "model_id": model_id,
                    "input_tokens": resp["input_tokens"],
                    "output_tokens": resp["output_tokens"],
                    "latency_ms": resp["latency_ms"],
                    "cost_estimate": resp["cost_estimate"],
                    "user_id": user_id,
                }
                analytics_table.put_item(Item=_to_dynamo(analytics_item))

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Routes — A/B testing
# ═══════════════════════════════════════════════════════════════════════════

def _compute_ab_summary(
    results_a: list[EvalResult],
    results_b: list[EvalResult],
) -> dict[str, Any]:
    """Compute comparative statistics for an A/B test."""

    def _stats(results: list[EvalResult]) -> dict[str, Any]:
        latencies = [r.latency_ms for r in results]
        costs = [r.cost_estimate for r in results]
        input_toks = [r.input_tokens for r in results]
        output_toks = [r.output_tokens for r in results]
        return {
            "num_runs": len(results),
            "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0,
            "p50_latency_ms": round(statistics.median(latencies), 2) if latencies else 0,
            "stddev_latency_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
            "avg_cost": round(statistics.mean(costs), 6) if costs else 0,
            "total_cost": round(sum(costs), 6),
            "avg_input_tokens": round(statistics.mean(input_toks), 1) if input_toks else 0,
            "avg_output_tokens": round(statistics.mean(output_toks), 1) if output_toks else 0,
            "avg_output_length": round(statistics.mean([len(r.output) for r in results]), 1) if results else 0,
        }

    stats_a = _stats(results_a)
    stats_b = _stats(results_b)

    winner_latency = "A" if stats_a["avg_latency_ms"] <= stats_b["avg_latency_ms"] else "B"
    winner_cost = "A" if stats_a["avg_cost"] <= stats_b["avg_cost"] else "B"

    return {
        "variant_a": stats_a,
        "variant_b": stats_b,
        "winner_latency": winner_latency,
        "winner_cost": winner_cost,
        "latency_diff_pct": round(
            abs(stats_a["avg_latency_ms"] - stats_b["avg_latency_ms"])
            / max(stats_a["avg_latency_ms"], stats_b["avg_latency_ms"], 1)
            * 100,
            2,
        ),
        "cost_diff_pct": round(
            abs(stats_a["avg_cost"] - stats_b["avg_cost"])
            / max(stats_a["avg_cost"], stats_b["avg_cost"], 1e-9)
            * 100,
            2,
        ),
    }


@app.post("/ab-tests", response_model=ABTestResult, status_code=201)
async def create_ab_test(
    body: ABTestCreate,
    user_id: str = Depends(get_current_user),
):
    """Run an A/B test comparing two prompts on the same model and inputs."""
    prompt_a = await get_prompt(body.prompt_a_id, user_id=user_id)
    prompt_b = await get_prompt(body.prompt_b_id, user_id=user_id)

    results_a: list[EvalResult] = []
    results_b: list[EvalResult] = []

    for test_input in body.test_inputs:
        rendered_a_user = _render_prompt(prompt_a["user_prompt"], test_input)
        rendered_a_sys = _render_prompt(prompt_a["system_prompt"], test_input)
        rendered_b_user = _render_prompt(prompt_b["user_prompt"], test_input)
        rendered_b_sys = _render_prompt(prompt_b["system_prompt"], test_input)

        for run_idx in range(body.num_runs):
            # Variant A
            resp_a = _invoke_model(
                model_id=body.model_id,
                system_prompt=rendered_a_sys,
                user_prompt=rendered_a_user,
                temperature=prompt_a["temperature"],
                max_tokens=prompt_a["max_tokens"],
            )
            results_a.append(EvalResult(
                eval_id=_new_id(),
                prompt_id=body.prompt_a_id,
                model_id=body.model_id,
                input_variables=test_input,
                output=resp_a["output"],
                input_tokens=resp_a["input_tokens"],
                output_tokens=resp_a["output_tokens"],
                latency_ms=resp_a["latency_ms"],
                cost_estimate=resp_a["cost_estimate"],
                run_index=run_idx,
            ))

            # Variant B
            resp_b = _invoke_model(
                model_id=body.model_id,
                system_prompt=rendered_b_sys,
                user_prompt=rendered_b_user,
                temperature=prompt_b["temperature"],
                max_tokens=prompt_b["max_tokens"],
            )
            results_b.append(EvalResult(
                eval_id=_new_id(),
                prompt_id=body.prompt_b_id,
                model_id=body.model_id,
                input_variables=test_input,
                output=resp_b["output"],
                input_tokens=resp_b["input_tokens"],
                output_tokens=resp_b["output_tokens"],
                latency_ms=resp_b["latency_ms"],
                cost_estimate=resp_b["cost_estimate"],
                run_index=run_idx,
            ))

    summary = _compute_ab_summary(results_a, results_b)
    test_id = _new_id()
    now = _now_iso()

    # Persist
    ab_table = get_table("ab_tests")
    ab_item = {
        "pk": f"USER#{user_id}",
        "sk": f"ABTEST#{test_id}",
        "test_id": test_id,
        "name": body.name,
        "prompt_a_id": body.prompt_a_id,
        "prompt_b_id": body.prompt_b_id,
        "model_id": body.model_id,
        "results_a": [r.model_dump() for r in results_a],
        "results_b": [r.model_dump() for r in results_b],
        "summary": summary,
        "created_at": now,
    }
    ab_table.put_item(Item=_to_dynamo(ab_item))

    return ABTestResult(
        test_id=test_id,
        name=body.name,
        prompt_a_id=body.prompt_a_id,
        prompt_b_id=body.prompt_b_id,
        model_id=body.model_id,
        results_a=results_a,
        results_b=results_b,
        summary=summary,
        created_at=now,
    )


@app.get("/ab-tests", response_model=list[ABTestResult])
async def list_ab_tests(
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
):
    table = get_table("ab_tests")
    resp = table.query(
        KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"USER#{user_id}",
            ":prefix": "ABTEST#",
        },
        ScanIndexForward=False,
        Limit=limit,
    )
    return [_from_dynamo(i) for i in resp.get("Items", [])]


@app.get("/ab-tests/{test_id}", response_model=ABTestResult)
async def get_ab_test(
    test_id: str,
    user_id: str = Depends(get_current_user),
):
    table = get_table("ab_tests")
    resp = table.get_item(Key={"pk": f"USER#{user_id}", "sk": f"ABTEST#{test_id}"})
    item = resp.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="A/B test not found")
    return _from_dynamo(item)


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Marketplace
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/marketplace/publish", response_model=MarketplaceEntry, status_code=201)
async def publish_to_marketplace(
    body: MarketplacePublish,
    user_id: str = Depends(get_current_user),
):
    """Publish a prompt to the public marketplace."""
    prompt = await get_prompt(body.prompt_id, user_id=user_id)
    if prompt["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not the owner")

    table = get_table("prompts")
    now = _now_iso()
    # Update prompt visibility and marketplace metadata
    table.update_item(
        Key={"pk": f"USER#{user_id}", "sk": f"PROMPT#{body.prompt_id}"},
        UpdateExpression=(
            "SET visibility = :vis, gsi2pk = :mpk, gsi2sk = :msk, "
            "price = :price, #lic = :lic, downloads = :dl, "
            "avg_rating = :rating, published_at = :pub"
        ),
        ExpressionAttributeNames={"#lic": "license"},
        ExpressionAttributeValues=_to_dynamo({
            ":vis": "public",
            ":mpk": "MARKETPLACE",
            ":msk": f"{prompt['category']}#0000000000",
            ":price": body.price,
            ":lic": body.license,
            ":dl": 0,
            ":rating": 0.0,
            ":pub": now,
        }),
    )

    return MarketplaceEntry(
        prompt_id=body.prompt_id,
        user_id=user_id,
        title=prompt["title"],
        description=prompt["description"],
        category=prompt["category"],
        tags=prompt["tags"],
        price=body.price,
        license=body.license,
        downloads=0,
        avg_rating=0.0,
        published_at=now,
    )


@app.get("/marketplace", response_model=list[MarketplaceEntry])
async def browse_marketplace(
    category: str | None = None,
    limit: int = Query(default=50, le=100),
    cursor: str | None = None,
):
    """Browse public marketplace prompts."""
    table = get_table("prompts")
    key_expr = "gsi2pk = :mpk"
    expr_values: dict[str, Any] = {":mpk": "MARKETPLACE"}

    if category:
        key_expr += " AND begins_with(gsi2sk, :cat)"
        expr_values[":cat"] = f"{category}#"

    kwargs: dict[str, Any] = {
        "IndexName": "GSI2",
        "KeyConditionExpression": key_expr,
        "ExpressionAttributeValues": expr_values,
        "ScanIndexForward": False,
        "Limit": limit,
    }

    resp = table.query(**kwargs)
    entries: list[MarketplaceEntry] = []
    for item in resp.get("Items", []):
        d = _from_dynamo(item)
        entries.append(MarketplaceEntry(
            prompt_id=d["prompt_id"],
            user_id=d["user_id"],
            title=d["title"],
            description=d["description"],
            category=d["category"],
            tags=d.get("tags", []),
            price=d.get("price", 0.0),
            license=d.get("license", "MIT"),
            downloads=d.get("downloads", 0),
            avg_rating=d.get("avg_rating", 0.0),
            published_at=d.get("published_at", d.get("created_at", "")),
        ))
    return entries


@app.post("/marketplace/{prompt_id}/fork", response_model=PromptResponse, status_code=201)
async def fork_prompt(
    prompt_id: str,
    user_id: str = Depends(get_current_user),
):
    """Fork a marketplace prompt into the current user's library."""
    original = await get_prompt(prompt_id, user_id=user_id)

    # Increment download counter on original
    table = get_table("prompts")
    table.update_item(
        Key={"pk": f"USER#{original['user_id']}", "sk": f"PROMPT#{prompt_id}"},
        UpdateExpression="SET downloads = if_not_exists(downloads, :zero) + :one",
        ExpressionAttributeValues={":zero": 0, ":one": 1},
    )

    forked = PromptCreate(
        title=f"{original['title']} (fork)",
        description=original["description"],
        system_prompt=original["system_prompt"],
        user_prompt=original["user_prompt"],
        variables=[PromptVariable(**v) for v in original.get("variables", [])],
        tags=original.get("tags", []),
        category=original.get("category", "general"),
        visibility=PromptVisibility.PRIVATE,
        model_id=original.get("model_id", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        temperature=original.get("temperature", 0.7),
        max_tokens=original.get("max_tokens", 1024),
    )
    return await create_prompt(forked, user_id=user_id)


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Prompt analytics
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/analytics/{prompt_id}", response_model=AnalyticsResponse)
async def get_prompt_analytics(
    prompt_id: str,
    user_id: str = Depends(get_current_user),
):
    """Aggregate analytics for a prompt: token usage, latency, cost."""
    # Verify ownership / access
    await get_prompt(prompt_id, user_id=user_id)

    table = get_table("analytics")
    resp = table.query(
        KeyConditionExpression="pk = :pk",
        ExpressionAttributeValues={":pk": f"PROMPT#{prompt_id}"},
    )
    items = [_from_dynamo(i) for i in resp.get("Items", [])]

    if not items:
        return AnalyticsResponse(
            prompt_id=prompt_id,
            total_runs=0,
            total_input_tokens=0,
            total_output_tokens=0,
            avg_latency_ms=0.0,
            total_cost=0.0,
            runs_by_model={},
        )

    total_input = sum(i.get("input_tokens", 0) for i in items)
    total_output = sum(i.get("output_tokens", 0) for i in items)
    latencies = [i.get("latency_ms", 0) for i in items]
    total_cost = sum(i.get("cost_estimate", 0) for i in items)

    runs_by_model: dict[str, int] = {}
    for i in items:
        mid = i.get("model_id", "unknown")
        runs_by_model[mid] = runs_by_model.get(mid, 0) + 1

    return AnalyticsResponse(
        prompt_id=prompt_id,
        total_runs=len(items),
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        avg_latency_ms=round(statistics.mean(latencies), 2) if latencies else 0.0,
        total_cost=round(total_cost, 6),
        runs_by_model=runs_by_model,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Search & discovery
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/search")
async def search_prompts(
    q: str = Query(..., min_length=1, max_length=200),
    category: str | None = None,
    tag: str | None = None,
    limit: int = Query(default=20, le=100),
):
    """Search public marketplace prompts by keyword in title/description."""
    table = get_table("prompts")
    # Scan marketplace items (GSI2) with filter — for production, use
    # OpenSearch or DynamoDB Streams -> search index.
    filter_parts = [
        "(contains(title, :q) OR contains(description, :q))",
    ]
    expr_values: dict[str, Any] = {
        ":mpk": "MARKETPLACE",
        ":q": q,
    }

    if category:
        filter_parts.append("category = :cat")
        expr_values[":cat"] = category
    if tag:
        filter_parts.append("contains(tags, :tag)")
        expr_values[":tag"] = tag

    resp = table.query(
        IndexName="GSI2",
        KeyConditionExpression="gsi2pk = :mpk",
        FilterExpression=" AND ".join(filter_parts),
        ExpressionAttributeValues=expr_values,
        Limit=limit,
    )
    results = []
    for item in resp.get("Items", []):
        d = _from_dynamo(item)
        results.append({
            "prompt_id": d["prompt_id"],
            "title": d["title"],
            "description": d["description"],
            "category": d.get("category", ""),
            "tags": d.get("tags", []),
            "user_id": d["user_id"],
            "downloads": d.get("downloads", 0),
            "avg_rating": d.get("avg_rating", 0.0),
        })
    return {"results": results, "count": len(results)}


# ═══════════════════════════════════════════════════════════════════════════
# Routes — User authentication stubs
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register_user(body: UserCreate):
    """Register a new user with bcrypt-hashed password and return a JWT."""
    table = get_table("users")
    user_id = _new_id()
    now = _now_iso()

    # Hash password with bcrypt
    hashed_password = pwd_context.hash(body.password)

    item = {
        "pk": f"USER#{user_id}",
        "sk": "PROFILE",
        "user_id": user_id,
        "email": body.email,
        "display_name": body.display_name,
        "password_hash": hashed_password,
        "created_at": now,
    }
    table.put_item(Item=_to_dynamo(item))

    access_token = _create_access_token(user_id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user_id,
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login_user(email: str, password: str):
    """Authenticate user by email/password and return a signed JWT."""
    table = get_table("users")
    # Scan for user by email (for production, add a GSI on email)
    resp = table.scan(
        FilterExpression="email = :email",
        ExpressionAttributeValues={":email": email},
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = _from_dynamo(items[0])
    stored_hash = user.get("password_hash", "")

    if not pwd_context.verify(password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = _create_access_token(user["user_id"])
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user["user_id"],
    )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_profile(user_id: str = Depends(get_current_user)):
    """Return the current user's profile."""
    table = get_table("users")
    resp = table.get_item(Key={"pk": f"USER#{user_id}", "sk": "PROFILE"})
    item = resp.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    d = _from_dynamo(item)
    return UserResponse(
        user_id=d["user_id"],
        email=d["email"],
        display_name=d["display_name"],
        created_at=d["created_at"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Prompt optimization (AI-powered)
# ═══════════════════════════════════════════════════════════════════════════

class OptimizeRequest(BaseModel):
    prompt_text: str = Field(..., min_length=1, description="The prompt to optimize")
    goal: str = Field(
        default="general",
        description="Optimization goal: general, clarity, conciseness, cost, creativity",
    )
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"


class OptimizeSuggestion(BaseModel):
    category: str
    original_issue: str
    suggestion: str
    improved_snippet: str


class OptimizeResponse(BaseModel):
    original_prompt: str
    optimized_prompt: str
    suggestions: list[OptimizeSuggestion]
    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_estimate: float


OPTIMIZE_SYSTEM_PROMPT = """You are an expert prompt engineer. Your job is to analyze a user's prompt and return an improved version along with specific suggestions.

You MUST respond with valid JSON in exactly this format (no markdown, no code fences):
{
  "optimized_prompt": "<the full improved prompt>",
  "suggestions": [
    {
      "category": "<one of: clarity, specificity, structure, cost_efficiency, creativity>",
      "original_issue": "<brief description of the issue in the original>",
      "suggestion": "<what to change and why>",
      "improved_snippet": "<the specific improved text>"
    }
  ]
}

Guidelines for optimization:
- Make instructions more specific and unambiguous
- Add output format constraints if missing
- Remove redundant or vague language
- Add role/persona framing if it would help
- Suggest breaking complex prompts into steps
- For "cost" goal: reduce token count while preserving intent
- For "creativity" goal: add techniques like chain-of-thought or few-shot examples
- For "conciseness" goal: make it shorter without losing meaning
- For "clarity" goal: restructure for maximum readability
- Provide 2-5 actionable suggestions
"""


@app.post("/optimize", response_model=OptimizeResponse)
async def optimize_prompt(
    body: OptimizeRequest,
    user_id: str = Depends(get_current_user),
):
    """Use Bedrock to analyze a prompt and suggest AI-powered improvements."""
    user_message = f"Optimization goal: {body.goal}\n\nPrompt to optimize:\n---\n{body.prompt_text}\n---"

    result = _invoke_model(
        model_id=body.model_id,
        system_prompt=OPTIMIZE_SYSTEM_PROMPT,
        user_prompt=user_message,
        temperature=0.4,
        max_tokens=4096,
    )

    # Parse the structured JSON response from the model
    try:
        parsed = json.loads(result["output"])
        optimized_prompt = parsed.get("optimized_prompt", body.prompt_text)
        raw_suggestions = parsed.get("suggestions", [])
        suggestions = [
            OptimizeSuggestion(
                category=s.get("category", "general"),
                original_issue=s.get("original_issue", ""),
                suggestion=s.get("suggestion", ""),
                improved_snippet=s.get("improved_snippet", ""),
            )
            for s in raw_suggestions
        ]
    except (json.JSONDecodeError, KeyError):
        # If the model didn't return valid JSON, return the raw output as the
        # optimized prompt with a single meta-suggestion
        optimized_prompt = result["output"]
        suggestions = [
            OptimizeSuggestion(
                category="general",
                original_issue="Could not parse structured suggestions",
                suggestion=result["output"],
                improved_snippet="",
            )
        ]

    return OptimizeResponse(
        original_prompt=body.prompt_text,
        optimized_prompt=optimized_prompt,
        suggestions=suggestions,
        model_id=body.model_id,
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        latency_ms=result["latency_ms"],
        cost_estimate=result["cost_estimate"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# Routes — Infrastructure / admin
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/admin/cloudformation")
async def get_cloudformation_template(_: None = Depends(_require_admin)):
    """Return the generated CloudFormation template for all Pronto resources."""
    return generate_cloudformation_template()


@app.post("/admin/init-tables")
async def init_tables(_: None = Depends(_require_admin)):
    """Create DynamoDB tables if they don't exist (dev/local use)."""
    from aws_config import ensure_tables_exist
    created = ensure_tables_exist()
    return {"created_tables": created}


# ═══════════════════════════════════════════════════════════════════════════
# Entrypoint
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

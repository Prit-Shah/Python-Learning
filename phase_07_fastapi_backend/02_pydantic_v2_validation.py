"""
02_pydantic_v2_validation.py

============================================================
1. CONCEPT
============================================================

Data validation, schema enforcement, and serialization in modern FastAPI backend
services are governed by Pydantic v2:

1. The Pydantic v2 Architecture:
   - Completely rewritten around `pydantic-core`, an engine implemented in Rust.
   - Provides 5x to 20x faster validation and JSON serialization compared to v1.
   - Operates as the parsing and data validation backbone of FastAPI.

2. Core Modeling Constructs:
   - `BaseModel`: The foundation class for all structured schemas.
   - `Field(...)`: Declarative field constraints (`gt`, `ge`, `lt`, `le`, `min_length`,
     `max_length`, `pattern`, `default_factory`).
   - `ConfigDict`: Class configuration configuring behavior (e.g. `extra="forbid"`,
     `from_attributes=True` for ORM models, `str_strip_whitespace=True`).

3. Custom Validators:
   - `@field_validator("field_name")`: Validates or transforms individual fields.
     Operates in `mode="before"` (raw input) or `mode="after"` (post-coercion, default).
   - `@model_validator(mode="after")`: Cross-field validation (e.g. verifying
     `end_date > start_date` or `password == confirm_password`).

4. Serialization & Data Filtering:
   - `model.model_dump()`: Converts model instance into a Python `dict`.
     Supports `exclude={"password"}`, `exclude_unset=True`, `exclude_none=True`.
   - `model.model_dump_json()`: Serializes model directly to a JSON string in Rust.
   - `TypeAdapter`: Validates and serializes root-level lists, dicts, or primitives
     without defining a wrapping class.

5. Request vs Response Data Segregation:
   - Inbound DTO (`UserCreate`): Accepts raw input, plaintext passwords, tokens.
   - Outbound DTO (`UserResponse`): Omit password hashes, internal DB sequences,
     and private telemetry.
   - FastAPI's `response_model=UserResponse` automatically applies this projection
     before sending HTTP bytes to the client.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Pydantic v2)               | JavaScript / TypeScript (Zod)      |
+------------------------------+------------------------------------+------------------------------------+
| Schema Definition            | `class User(BaseModel):`           | `const UserSchema = z.object({..})`|
| Type Coercion & Validation   | Runtime via Rust (`pydantic-core`)| Runtime via JavaScript AST parsing |
| Field Constraints            | `Field(..., min_length=3, ge=0)`   | `z.string().min(3)`, `z.number().min(0)`|
| Custom Field Validator       | `@field_validator("field")`        | `.refine(...)` / `.transform(...)` |
| Cross-Field Validator        | `@model_validator(mode="after")`   | `.refine((data) => data.p1 === ...)`|
| Serialization to Object      | `model.model_dump()`               | `schema.parse(rawObj)`             |
| Serialization to JSON        | `model.model_dump_json()`          | `JSON.stringify(parsed)`           |
| Forbid Extra Properties      | `model_config = ConfigDict(extra='forbid')` | `.strict()`              |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Validation Differences:
1. In TypeScript, interfaces exist purely at compile-time and are erased.
   Pydantic models execute strict runtime parsing, validating and coercing types
   on every request payload.
2. In Pydantic v2, string trimming, regex checking, and JSON parsing are executed
   in native Rust memory buffers, achieving speeds orders of magnitude faster
   than pure JS schema libraries.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The pydantic-core Rust Engine:
   - When a `BaseModel` class is declared, Pydantic builds a core schema definition
     dictionary and compiles it into a Rust validator (`SchemaValidator`).
   - During `model_validate_json(raw_json_bytes)`, parsing bypasses CPython entirely:
     Rust validates the JSON bytes directly into field values, constructing the
     Python object in a single pass.

2. v1 to v2 Deprecations & Migration:
   - `@validator` -> `@field_validator`
   - `@root_validator` -> `@model_validator`
   - `.dict()` -> `.model_dump()`
   - `.json()` -> `.model_dump_json()`
   - `class Config:` -> `model_config = ConfigDict(...)`


============================================================
4. COMMON GOTCHAS
============================================================

1. Mutable Default Arguments in Fields:
   - Writing `tags: list[str] = []` inside a BaseModel.
   - Pydantic protects against this in most cases, but best practice is:
     `tags: list[str] = Field(default_factory=list)`.

2. Over-coercion in Default Mode:
   - Pydantic v2 by default coerces strings like `"123"` into integers if the field
     is typed `int`.
   - If strict validation without coercion is required, specify `strict=True`
     in `Field()` or `ConfigDict(strict=True)`.

3. Leaking Internal Fields Without response_model:
   - Returning an internal database object directly from a FastAPI endpoint without
     specifying `response_model=UserResponse` leaks password hashes and private keys
     to the client!


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the architecture of Pydantic v2 and how it differs from Pydantic v1."
Script:
"Pydantic v2 was completely re-architected with a dual-layer design: the public-facing
Python API (`BaseModel`, `Field`, `ConfigDict`) and the internal validation engine
`pydantic-core`, implemented in Rust. In v1, validation was executed in pure Python,
which created performance bottlenecks during high-throughput serialization. In v2,
class definitions compile down to a Rust `SchemaValidator` that operates directly on
memory buffers, yielding a 5x to 20x throughput improvement. Key syntactic updates include
replacing `.dict()` and `.json()` with `.model_dump()` and `.model_dump_json()`, and
adopting `@field_validator` and `@model_validator`."

Q2: "What is the purpose of response_model in FastAPI and how does it prevent security leaks?"
Script:
"The `response_model` parameter in FastAPI route decorators acts as a secure outbound data
filter and serialization contract. When an endpoint returns a database entity or domain model,
that object often contains sensitive attributes such as hashed passwords, internal tenant IDs,
or audit flags. By specifying a dedicated outbound schema like `response_model=UserResponse`,
FastAPI automatically filters and projects the returned data to include strictly the fields
defined in `UserResponse`, guaranteeing that sensitive backend state can never accidentally
leak over the wire."

Q3: "How do field_validator and model_validator differ in Pydantic v2?"
Script:
"`@field_validator` is used for single-field validation and normalization. It receives the
specific field value and can operate either in `mode='before'` to intercept raw, unparsed
inputs or in `mode='after'` to inspect already-coerced Python types. In contrast,
`@model_validator` operates across the entire model instance, receiving all validated
attributes simultaneously. It is typically configured with `mode='after'` to enforce
complex business invariants and cross-field relationships, such as verifying that a
confirmation password matches the primary password or that a subscription end date occurs
after its start date."
"""

import sys
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# PYDANTIC SCHEMAS: USER CREATION & RESPONSE
# ============================================================

class UserRegistrationRequest(BaseModel):
    """Inbound request model with field-level and model-level validation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",  # Reject unexpected fields
    )

    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    email: str = Field(..., min_length=5)
    age: int = Field(..., ge=18, le=120)
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    tags: list[str] = Field(default_factory=list)

    # Field-level validator: Ensure email is lowercase and valid format
    @field_validator("email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        value = value.lower()
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Email must contain a valid @ domain structure")
        return value

    # Cross-field model-level validator: Verify password matching
    @model_validator(mode="after")
    def verify_password_match(self) -> "UserRegistrationRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserPublicResponse(BaseModel):
    """Outbound response model omitting sensitive password information."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    age: int
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)


def run_tests():
    # ============================================================
    # 1. SUCCESSFUL MODEL PARSING & VALIDATION
    # ============================================================

    valid_payload = {
        "username": "alice_dev",
        "email": "  ALICE@APEX.INTERNAL  ",
        "age": 28,
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "tags": ["admin", "backend"],
    }

    user = UserRegistrationRequest(**valid_payload)

    # Trimming whitespace and email normalization verified
    assert user.username == "alice_dev"
    assert user.email == "alice@apex.internal"
    assert user.age == 28
    assert user.tags == ["admin", "backend"]


    # ============================================================
    # 2. VALIDATION FAILURE: FIELD CONSTRAINTS
    # ============================================================

    # Age under 18 failure
    invalid_age_payload = valid_payload.copy()
    invalid_age_payload["age"] = 15

    caught_age_error = False
    try:
        UserRegistrationRequest(**invalid_age_payload)
    except ValidationError as err:
        caught_age_error = True
        error_details = err.errors()
        assert error_details[0]["loc"] == ("age",)
        assert "greater than or equal to 18" in error_details[0]["msg"]
    assert caught_age_error is True

    # Invalid email format failure
    invalid_email_payload = valid_payload.copy()
    invalid_email_payload["email"] = "not_an_email"

    caught_email_error = False
    try:
        UserRegistrationRequest(**invalid_email_payload)
    except ValidationError as err:
        caught_email_error = True
        assert "Email must contain a valid @ domain structure" in str(err)
    assert caught_email_error is True


    # ============================================================
    # 3. VALIDATION FAILURE: CROSS-FIELD (PASSWORD MISMATCH)
    # ============================================================

    mismatched_password_payload = valid_payload.copy()
    mismatched_password_payload["confirm_password"] = "DifferentPassword123!"

    caught_mismatch_error = False
    try:
        UserRegistrationRequest(**mismatched_password_payload)
    except ValidationError as err:
        caught_mismatch_error = True
        assert "Passwords do not match" in str(err)
    assert caught_mismatch_error is True


    # ============================================================
    # 4. FORBIDDEN EXTRA ATTRIBUTES (extra='forbid')
    # ============================================================

    extra_fields_payload = valid_payload.copy()
    extra_fields_payload["malicious_role"] = "superadmin"

    caught_extra_error = False
    try:
        UserRegistrationRequest(**extra_fields_payload)
    except ValidationError as err:
        caught_extra_error = True
        assert "extra_forbidden" in str(err) or "Extra inputs are not permitted" in str(err)
    assert caught_extra_error is True


    # ============================================================
    # 5. SERIALIZATION: model_dump & model_dump_json
    # ============================================================

    # Exclude passwords upon serialization
    dumped_dict = user.model_dump(exclude={"password", "confirm_password"})
    assert "password" not in dumped_dict
    assert "confirm_password" not in dumped_dict
    assert dumped_dict["username"] == "alice_dev"

    # Direct JSON serialization
    json_bytes_str = user.model_dump_json(exclude={"password", "confirm_password"})
    assert isinstance(json_bytes_str, str)
    assert '"username":"alice_dev"' in json_bytes_str or '"username": "alice_dev"' in json_bytes_str


    # ============================================================
    # 6. RESPONSE MODEL PROJECTION
    # ============================================================

    # Simulating conversion to public response DTO
    internal_user_record = {
        "user_id": 101,
        "username": user.username,
        "email": user.email,
        "age": user.age,
        "tags": user.tags,
        "hashed_password": "argon2_secret_hash_not_for_client",
    }

    public_dto = UserPublicResponse(**internal_user_record)
    public_dict = public_dto.model_dump()

    # Verify sensitive hash is stripped
    assert "hashed_password" not in public_dict
    assert public_dict["user_id"] == 101
    assert public_dict["is_active"] is True


if __name__ == "__main__":
    run_tests()
    print("02_pydantic_v2_validation.py tests passed!")

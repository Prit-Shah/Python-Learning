"""
Phase 7: Backend with FastAPI - Pydantic v2 Schema Validation
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Pydantic v2 is the data validation and settings management engine of FastAPI, completely
     rewritten in Rust ('pydantic-core') for 5-20x faster serialization and validation.
   - Core Concepts:
     * 'BaseModel': The foundation class for all structured data models.
     * 'Field(..., min_length=..., ge=..., pattern=...)': Declarative field-level constraints.
     * Custom Field Validators ('@field_validator'): Validate or transform individual fields.
     * Custom Model Validators ('@model_validator(mode="after")'): Cross-field validation
       (e.g. verifying password == confirm_password).
     * Request vs Response Models:
       - 'UserCreate': Accepts raw input including plaintext password.
       - 'UserResponse': Omits password hash, returning only public fields ('response_model=UserResponse').
     * Serialization:
       - 'model.model_dump()': Converts to Python dictionary.
       - 'model.model_dump_json()': Serializes directly to JSON string via Rust.
   - JS/TS Analogy:
     * Pydantic is the Python equivalent of 'Zod' or 'Valibot'.
     * In TypeScript, types exist ONLY at compile time and disappear at runtime.
     * In Pydantic, types perform STRICT runtime coercion, parsing, and error generation!

2. UNDER THE HOOD (CPython & Memory):
   - Pydantic v2 compiles your Python class definitions into Rust validation schemas.
   - Parsing JSON directly invokes C/Rust memory buffers, bypassing intermediate Python objects
     for maximum throughput.

3. COMMON GOTCHA:
   - Migrating from v1 to v2:
     * v1 used '@validator'; v2 uses '@field_validator'.
     * v1 used '.dict()'; v2 uses '.model_dump()'.
     * v1 used '.json()'; v2 uses '.model_dump_json()'.
   - Mutable default arguments in fields: Always use 'Field(default_factory=list)' instead of 'Field(default=[])'.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does Pydantic v2 enforce data validation in FastAPI, how does it compare to
       TypeScript/Zod, and what is the purpose of response_model?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Pydantic v2 & Rust Core:
      "Pydantic v2 powers FastAPI's data layer. Unlike TypeScript where interfaces are erased
       at compile-time, Pydantic performs strict runtime validation and type coercion.
       In v2, all validation logic is compiled down to Rust via 'pydantic-core', making parsing
       and serializing payloads blisteringly fast."
   2. Granular Validation Rules:
      "We use 'Field()' for boundary constraints (like regex patterns, min/max values) and
       '@field_validator' for custom business logic. For cross-field dependencies—such as
       ensuring 'start_date < end_date' or password confirmation matching—we use '@model_validator(mode='after')'."
   3. The Crucial Role of response_model:
      "The 'response_model' parameter in FastAPI route decorators serves three vital security and performance goals:
       1. Data Filtering: It strips sensitive internal attributes (like password hashes or internal IDs)
          before the payload leaves the server.
       2. Automatic Documentation: It populates the OpenAPI/Swagger JSON schema with accurate return contracts.
       3. Performance: It validates outgoing responses to prevent malformed data from reaching the frontend."
================================================================================
"""

import sys
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ValidationError

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# PYDANTIC V2 SCHEMAS DEMONSTRATION
# ==============================================================================

class UserRegistration(BaseModel):
    """Demonstrates field constraints, field validator, and cross-field model validator."""
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    age: Optional[int] = Field(None, ge=18, le=120)
    tags: List[str] = Field(default_factory=list)

    # 1. Custom Field Validator: Normalize email to lowercase
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format.")
        return v.strip().lower()

    # 2. Cross-field Model Validator: Verify password matching
    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserRegistration":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class UserPublicResponse(BaseModel):
    """Safe response model stripping password attributes."""
    id: int
    username: str
    email: str
    tags: List[str]


def demonstrate_pydantic_validation():
    print("\n--- 1. Validating Valid Registration Payload ---")
    valid_data = {
        "username": "alice_dev",
        "email": "Alice@Company.COM",
        "password": "SuperSecretPassword123",
        "confirm_password": "SuperSecretPassword123",
        "age": 28,
        "tags": ["python", "ai", "fastapi"]
    }
    
    user = UserRegistration.model_validate(valid_data)
    print(f"  Validated username: {user.username}")
    print(f"  Normalized email:   {user.email}")
    print(f"  Dumped dictionary:  {user.model_dump(exclude={'password', 'confirm_password'})}")


def demonstrate_validation_errors():
    print("\n--- 2. Capturing Validation Errors (Invalid Input) ---")
    invalid_data = {
        "username": "a!",  # Too short, illegal character
        "email": "bad_email",
        "password": "pass1",
        "confirm_password": "pass2",  # Mismatch
        "age": 16  # Under 18
    }

    try:
        UserRegistration.model_validate(invalid_data)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        print(f"  Caught {len(e.errors())} validation errors as expected:")
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            print(f"    * [{loc}]: {err['msg']}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

class ProductOrder(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., ge=1, le=100)
    unit_price: float = Field(..., gt=0.0)
    discount_code: Optional[str] = None

    @field_validator("discount_code")
    @classmethod
    def validate_discount(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in {"SAVE10", "SAVE20", "VIP"}:
            raise ValueError("Invalid discount code.")
        return v.upper() if v else None


def run_tests():
    print("\n[*] Running automated self-tests for 02_pydantic_v2_validation.py...")
    # Test valid order
    order = ProductOrder(product_id=10, quantity=2, unit_price=49.99, discount_code="save10")
    assert order.discount_code == "SAVE10"
    assert order.model_dump()["unit_price"] == 49.99

    # Test invalid discount code
    try:
        ProductOrder(product_id=1, quantity=1, unit_price=10.0, discount_code="INVALID_CODE")
        assert False, "Should raise ValidationError on bad discount code"
    except ValidationError:
        pass

    # Test negative quantity
    try:
        ProductOrder(product_id=1, quantity=-5, unit_price=10.0)
        assert False, "Should raise ValidationError on negative quantity"
    except ValidationError:
        pass

    print("[SUCCESS] All Pydantic validation tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 7 - Pydantic v2 Schema Validation")
    print("=" * 65)
    demonstrate_pydantic_validation()
    demonstrate_validation_errors()
    print("-" * 65)
    run_tests()
    print("=" * 65)

#!/usr/bin/env python3
"""SSPL Phase III - Payload Signing and Verification"""
import hashlib
import hmac
import json
import os
import time

MAX_TRACE_AGE_SECONDS = 300
MAX_SERVICE_REQUEST_AGE_SECONDS = 300

def make_canonical(obj: Any) -> Any:
    from typing import Any as TypAny
    if isinstance(obj, dict):
        return {k: make_canonical(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, (list, tuple)):
        return [make_canonical(x) for x in obj]
    elif isinstance(obj, set):
        return [make_canonical(x) for x in sorted(list(obj), key=str)]
    elif hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return make_canonical(obj.model_dump(mode="json"))
    elif hasattr(obj, "__dict__"):
        return make_canonical(obj.__dict__)
    return obj

def canonical_serialize(obj: Any) -> str:
    return json.dumps(make_canonical(obj), separators=(',', ':'), default=str)

from typing import Any

class PayloadSigner:
    """Signs and verifies payloads for SSPL Phase III compliance."""
    
    def __init__(self, secret_key: str = None):
        resolved_secret = secret_key or os.getenv('SSPL_SECRET_KEY')

        if not resolved_secret:
            environment = os.getenv('ENVIRONMENT', '').strip().lower()
            if environment == 'prod':
                raise ValueError('SSPL_SECRET_KEY must be set in production')
            resolved_secret = 'default-secret-key-change-in-prod'

        self.secret_key = resolved_secret
    
    def sign_payload(self, payload_dict: dict) -> dict:
        """Sign payload and return with signature field."""
        # Create canonical string from payload
        canonical = canonical_serialize(payload_dict)
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to payload
        signed_payload = payload_dict.copy()
        signed_payload['signature'] = signature
        signed_payload['signature_algorithm'] = 'HMAC-SHA256'
        
        return signed_payload
    
    def verify_payload(self, payload_dict: dict, signature: str = None) -> bool:
        """Verify payload signature."""
        if signature is None:
            signature = payload_dict.get('signature')
        
        if not signature:
            return False
        
        # Remove signature fields for verification
        payload_copy = payload_dict.copy()
        payload_copy.pop('signature', None)
        payload_copy.pop('signature_algorithm', None)
        
        # Recreate canonical string
        canonical = canonical_serialize(payload_copy)
        
        # Generate expected signature
        expected_signature = hmac.new(
            self.secret_key.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(signature, expected_signature)

# Global signer instance
_signer = None

def get_signer() -> PayloadSigner:
    """Get or create global signer instance."""
    global _signer
    if _signer is None:
        _signer = PayloadSigner()
    return _signer

def sign_payload(payload_dict: dict) -> dict:
    """Convenience function to sign payload."""
    return get_signer().sign_payload(payload_dict)

def verify_payload(payload_dict: dict, signature: str = None) -> bool:
    """Convenience function to verify payload."""
    return get_signer().verify_payload(payload_dict, signature)


def generate_body_hash(payload_dict: dict) -> str:
    canonical = canonical_serialize(payload_dict)

    return hashlib.sha256(
        canonical.encode()
    ).hexdigest()


def build_trace_payload(
    trace_id: str,
    timestamp: str,
    body_hash: str
) -> str:
    return f"{trace_id}:{timestamp}:{body_hash}"


def sign_trace(
    trace_id: str,
    timestamp: str,
    payload_dict: dict
) -> str:

    signer = get_signer()

    body_hash = generate_body_hash(payload_dict)

    payload = build_trace_payload(
        trace_id,
        timestamp,
        body_hash
    )

    return hmac.new(
        signer.secret_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_trace_signature(
    trace_id: str,
    timestamp: str,
    signature: str,
    payload_dict: dict
) -> bool:

    if not trace_id:
        return False

    if not timestamp:
        return False

    if not signature:
        return False

    try:
        request_time = int(timestamp)
    except Exception:
        return False

    now = int(time.time())

    if abs(now - request_time) > MAX_TRACE_AGE_SECONDS:
        return False

    expected_signature = sign_trace(
        trace_id,
        timestamp,
        payload_dict
    )

    return hmac.compare_digest(
        signature,
        expected_signature
    )


def build_service_payload(
    service_id: str,
    timestamp: str,
    nonce: str,
    body_hash: str
) -> str:
    return (
        f"{service_id}:"
        f"{timestamp}:"
        f"{nonce}:"
        f"{body_hash}"
    )


def sign_service_request(
    service_id: str,
    timestamp: str,
    nonce: str,
    payload_dict: dict
) -> str:

    signer = get_signer()

    body_hash = generate_body_hash(
        payload_dict
    )

    payload = build_service_payload(
        service_id,
        timestamp,
        nonce,
        body_hash
    )

    return hmac.new(
        signer.secret_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_service_request(
    service_id: str,
    timestamp: str,
    nonce: str,
    signature: str,
    payload_dict: dict
) -> bool:

    if not service_id:
        return False

    if not timestamp:
        return False

    if not nonce:
        return False

    if not signature:
        return False

    try:
        request_time = int(timestamp)
    except Exception:
        return False

    now = int(time.time())

    if abs(now - request_time) > MAX_SERVICE_REQUEST_AGE_SECONDS:
        return False

    expected_signature = sign_service_request(
        service_id,
        timestamp,
        nonce,
        payload_dict
    )

    return hmac.compare_digest(
        signature,
        expected_signature
    )
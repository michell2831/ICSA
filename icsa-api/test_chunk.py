from services.pss_service import build_text_chunk

svc = {
    "name": "Certificate of Good Moral Character",
    "office": "OSAS",
    "sla_target_value": 120,
    "sla_target_unit": "minutes",
    "processing_steps": ["Fill out request form", "Pay processing fee at Cashier", "Wait for release"],
    "required_documents": ["Valid ID"],
    "expected_output": "Signed Certificate",
}

print(build_text_chunk(svc))
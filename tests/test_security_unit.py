from dotenv import load_dotenv

from app.security import hash_password, safe_text, verify_password

load_dotenv()


def test_password_is_hashed_and_verifiable():
    digest = hash_password("correct horse battery staple")
    assert digest != "correct horse battery staple"
    assert verify_password("correct horse battery staple", digest)
    assert not verify_password("wrong password", digest)


def test_response_text_is_escaped():
    assert safe_text('<script>alert("x")</script>') == "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"


def test_database_environment_is_available():
    from app.db import initialize_schema
    initialize_schema()

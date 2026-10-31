import os
import tempfile

# Before watchme is imported: a throwaway data folder, short timers, no outside services.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="watchme-test-")
os.environ["CHECKIN_TIMEOUT_S"] = "0.3"
os.environ["URGENT_CHECKIN_TIMEOUT_S"] = "0.2"
for name in ("META_API_KEY", "MODEL_API_KEY", "BASETEN_API_KEY", "JEV_BASE_URL", "KEV_BASE_URL", "TWILIO_ACCOUNT_SID", "SMTP_HOST"):
    os.environ[name] = ""

"""Runtime configuration, all overridable by environment variables.

AWS credentials are never read here: boto3's default credential chain supplies them.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Default OUTSIDE ~/Desktop: iCloud-synced folders caused SQLite "disk I/O error" on the decision log.
DATA_DIR = Path(os.getenv("CLEARSIGHT_DATA_DIR") or Path.home() / ".clearsight")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# The team's existing NWS client / facility store live in <repo>/parser.
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
BEDROCK_REGION = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
BEDROCK_FAST_MODEL_ID = os.getenv("BEDROCK_FAST_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")  # hazard + impact agents
AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "4096"))

NWS_USER_AGENT = os.getenv("NWS_USER_AGENT", "ClearSight-USDA-hackathon (contact: set NWS_USER_AGENT)")
os.environ.setdefault("NWS_USER_AGENT", NWS_USER_AGENT)

FACILITIES_DB = os.getenv("CLEARSIGHT_FACILITIES_DB", str(DATA_DIR / "facilities.db"))
DECISIONS_DB = os.getenv("CLEARSIGHT_DECISIONS_DB", str(DATA_DIR / "decisions.db"))

# Optional 511 credentials. Without them road data is reported as unavailable (never invented).
NE511_API_KEY = os.getenv("NE511_API_KEY", "")
FL511_API_KEY = os.getenv("FL511_API_KEY", "")

from enum import Enum
class Role(str,Enum):
    admin="admin"
    analyst="analyst"
    viewer="viewer"
class ReviewStatus(str,Enum):
    queued="queued"
    running="running"
    completed="completed"
    approved="approved"
    failed="failed"
class SyncRunStatus(str,Enum):
    queued="queued"
    running="running"
    completed="completed"
    failed="failed"
class CenterBatchStatus(str,Enum):
    synced="synced"
    reconciled="reconciled"
    diverged="diverged"
    repairing="repairing"
class ReviewSource(str,Enum):
    ledger="ledger"
    center="center"
LINES=["一线","二线","三线"]

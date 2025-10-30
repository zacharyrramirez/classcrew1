#!/usr/bin/env python3
"""
verify_firestore_payments.py

Quick verification script to list payment records for a given user from Firestore.
Requires Firebase Admin to be configured via utils.firebase (Streamlit secrets or local config.toml).

Usage (PowerShell):
  python scripts/verify_firestore_payments.py -u <user_id>

If no user_id is provided, all payments will be listed (limited to 50).
"""

import argparse
import os
from typing import Optional

# Ensure repo root is on path
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

try:
    from utils import firebase as firebase_utils
except Exception as e:
    print(f"Error importing Firebase utils: {e}")
    firebase_utils = None


def list_payments(user_id: Optional[str] = None, limit: int = 50):
    if not (firebase_utils and getattr(firebase_utils, 'db', None)):
        print('Firestore client not initialized. Ensure Firebase credentials are configured and utils.firebase.db is available.')
        return

    coll = firebase_utils.db.collection('payments')
    if user_id:
        q = coll.where('user_id', '==', user_id).limit(limit)
    else:
        q = coll.limit(limit)

    docs = list(q.stream())
    if not docs:
        print('No payment documents found.')
        return

    print(f"Found {len(docs)} payment document(s):\n")
    for d in docs:
        data = d.to_dict()
        pid = data.get('payment_intent_id', d.id)
        print(f"- id={d.id} pid={pid} user={data.get('user_id')} assign={data.get('assignment_id')} status={data.get('status')} type={data.get('payment_type')} amount={data.get('amount')} ts={data.get('timestamp')}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List Firestore payments for a user')
    parser.add_argument('-u', '--user', dest='user_id', type=str, default=None, help='User ID/email to filter by')
    parser.add_argument('-n', '--limit', dest='limit', type=int, default=50, help='Max number of documents to print')
    args = parser.parse_args()

    list_payments(args.user_id, args.limit)

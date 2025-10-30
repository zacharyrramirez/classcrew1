#!/usr/bin/env python3
"""
scripts/migrate_payments_to_firestore.py

Scan local payment JSON files (e.g. /app/data/payments_{user}.json) and upload
each payment entry to Firestore collection `payments` when Firestore is
configured via `utils.firebase`.

Usage:
  python scripts/migrate_payments_to_firestore.py --dry-run
  python scripts/migrate_payments_to_firestore.py --data-dir ./data --mark-migrated

Notes:
- This script will skip uploading entries that already exist in Firestore by
  checking the `payment_intent_id` field when present.
- Always run with `--dry-run` first to review what will be uploaded.
"""
from __future__ import annotations
import os
import sys
import json
import glob
import argparse
from pathlib import Path
from typing import List, Dict, Any

try:
    # Import the firebase utils from the project
    from utils import firebase as firebase_utils
except Exception:
    firebase_utils = None


def find_payment_files(search_paths: List[str]) -> List[Path]:
    files: List[Path] = []
    for p in search_paths:
        p_path = Path(p)
        if not p_path.exists():
            continue
        for f in p_path.glob('payments_*.json'):
            files.append(f)
    return files


def load_payments(file_path: Path) -> List[Dict[str, Any]]:
    try:
        with file_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return []


def payment_exists_in_firestore(db, payment: Dict[str, Any]) -> bool:
    # Prefer checking by Stripe payment intent id when available
    pid = payment.get('payment_intent_id')
    try:
        if pid:
            # Check document by id for O(1) existence check
            try:
                doc = db.collection('payments').document(pid).get()
                return doc.exists
            except Exception as e:
                print(f"Warning: Firestore document existence check failed: {e}")
                # Fall back to a query
        # If no pid or doc check failed, try a conservative query by fields
        user_id = payment.get('user_id')
        assignment_id = payment.get('assignment_id')
        query = db.collection('payments')
        if user_id:
            query = query.where('user_id', '==', user_id)
        if assignment_id:
            query = query.where('assignment_id', '==', assignment_id)
        query = query.where('status', '==', 'completed').limit(1)
        docs = query.stream()
        for _ in docs:
            return True
        return False
    except Exception as e:
        # If the query fails (e.g., missing indexes), conservatively return False
        print(f"Warning: Firestore existence check failed: {e}")
        return False


def upload_payment_to_firestore(db, payment: Dict[str, Any]) -> bool:
    try:
        # Firestore Admin SDK will accept native Python types; keep the payload small
        pid = payment.get('payment_intent_id')
        if pid:
            db.collection('payments').document(pid).set(payment)
        else:
            db.collection('payments').add(payment)
        return True
    except Exception as e:
        print(f"Failed to upload payment to Firestore: {e}")
        return False


def mark_file_migrated(path: Path) -> None:
    # Rename file to indicate migration (append .migrated)
    try:
        new_name = path.with_suffix(path.suffix + '.migrated')
        path.rename(new_name)
        print(f"Renamed {path} -> {new_name}")
    except Exception as e:
        print(f"Failed to rename {path}: {e}")


def main(argv=None):
    parser = argparse.ArgumentParser(description='Migrate local payment JSON logs to Firestore')
    parser.add_argument('--data-dir', default=None, help='Directory to search for payment files (default: /app/data, ./data, ./app/data)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be uploaded but do not perform writes')
    parser.add_argument('--mark-migrated', action='store_true', help='Rename files after successful migration to mark them migrated')
    args = parser.parse_args(argv)

    search_paths = []
    if args.data_dir:
        search_paths.append(args.data_dir)
    # Common locations
    search_paths.extend(['/app/data', './data', './app/data'])

    files = find_payment_files(search_paths)
    if not files:
        print('No payment files found in search paths:', search_paths)
        return 0

    if not args.dry_run:
        # Ensure Firestore client is available
        if not (firebase_utils and getattr(firebase_utils, 'db', None)):
            print('Firestore client not initialized. Please ensure Firebase credentials are configured and utils.firebase.db is available.')
            return 2

    total_files = len(files)
    total_uploaded = 0
    total_skipped = 0

    for file_path in files:
        print(f"Processing {file_path}...")
        payments = load_payments(file_path)
        if not payments:
            print(f"  No payments found in {file_path}")
            continue

        uploaded_for_file = 0
        skipped_for_file = 0
        for payment in payments:
            if args.dry_run:
                print(f"  [dry-run] Would upload payment_intent_id={payment.get('payment_intent_id')} user_id={payment.get('user_id')}")
                uploaded_for_file += 1
                continue

            # Skip if exists
            if payment_exists_in_firestore(firebase_utils.db, payment):
                skipped_for_file += 1
                continue

            ok = upload_payment_to_firestore(firebase_utils.db, payment)
            if ok:
                uploaded_for_file += 1
            else:
                print(f"  Failed to upload payment: {payment.get('payment_intent_id')}")

        total_uploaded += uploaded_for_file
        total_skipped += skipped_for_file

        print(f"  Uploaded: {uploaded_for_file}, Skipped (already exists): {skipped_for_file}")

        if args.mark_migrated and not args.dry_run:
            mark_file_migrated(file_path)

    print('Migration complete')
    print(f"Files processed: {total_files}, Uploaded: {total_uploaded}, Skipped: {total_skipped}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

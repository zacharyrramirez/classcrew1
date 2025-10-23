"""
anonymize.py
Utilities for anonymizing and (optionally) deanonymizing user IDs in grading workflows.
Never persist mapping files beyond the grading/upload session!
"""

import json

def generate_anonymized_mapping(user_ids):
    """
    Given a list of unique user IDs (strings or ints), returns a mapping from original ID
    to anonymized label, e.g., { '235': 'user001', '208': 'user002', ... }.
    Mapping is deterministic for a given sorted user_ids input.
    """
    return {str(uid): f"user{str(i + 1).zfill(3)}" for i, uid in enumerate(sorted(user_ids))}

def anonymize_user_id(user_id, mapping):
    """
    Returns the anonymized label for a given user_id, using a mapping generated above.
    """
    return mapping.get(str(user_id), f"user???")  # Or: raise KeyError(f"User ID {user_id} not found")

def deanonymize_user_id(anon_id, mapping):
    """
    Returns the original user ID for a given anonymized label, using a reversed mapping.
    Only use before grades are pushed to Canvas. Will return None if not found.
    """
    reverse = {v: k for k, v in mapping.items()}
    return reverse.get(anon_id)

def audit_mapping_integrity(mapping):
    """
    Checks for duplicate anonymized labels or duplicate originals (should never happen!).
    Raises ValueError if any duplicates are found.
    """
    if len(set(mapping.values())) != len(mapping.values()):
        raise ValueError("Duplicate anonymized labels found!")
    if len(set(mapping.keys())) != len(mapping.keys()):
        raise ValueError("Duplicate user IDs in mapping!")
    return True

def save_mapping_to_file(mapping, filename):
    """
    Save the mapping as a JSON file for temporary storage during grading.
    NEVER commit mapping files to source control. Delete after grades are uploaded!
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)

def load_mapping_from_file(filename):
    """
    Load a mapping from a JSON file.
    """
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

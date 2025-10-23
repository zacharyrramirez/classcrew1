"""
grading_analytics.py
Utilities for analyzing grading performance and identifying patterns that need prompt adjustments.
"""

import pandas as pd
import re
from typing import Dict, List, Tuple

def analyze_grading_logs(log_text: str) -> Dict:
    """
    Analyze grading logs to identify patterns and performance metrics.
    
    Args:
        log_text: Raw grading log output
        
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "total_submissions": 0,
        "unfair_flags": 0,
        "unfairness_rate": 0.0,
        "common_issues": {},
        "score_changes": [],
        "confidence_scores": [],
        "file_detection_errors": 0,
        "rubric_interpretation_errors": 0
    }
    
    # Count total submissions
    submission_matches = re.findall(r"🤖 Grading complete for user\d+", log_text)
    analysis["total_submissions"] = len(submission_matches)
    
    # Count unfair flags
    unfair_matches = re.findall(r"⚠️ Gemini flagged user\d+ as unfair", log_text)
    analysis["unfair_flags"] = len(unfair_matches)
    
    if analysis["total_submissions"] > 0:
        analysis["unfairness_rate"] = analysis["unfair_flags"] / analysis["total_submissions"]
    
    # Extract score changes
    score_changes = re.findall(r"♻️ Gemini revised grade for user\d+ from (\d+) to (\d+) points", log_text)
    analysis["score_changes"] = [(int(old), int(new)) for old, new in score_changes]
    
    # Extract confidence scores
    confidence_matches = re.findall(r"confidence: ([\d.]+)", log_text)
    analysis["confidence_scores"] = [float(conf) for conf in confidence_matches]
    
    # Identify common issues
    common_patterns = {
        "file_detection": [
            r"did not provide specific updates",
            r"did not provide.*PDF",
            r"missing.*profile",
            r"no.*submission"
        ],
        "rubric_interpretation": [
            r"contradicts.*rubric",
            r"does not meet.*rubric",
            r"rubric.*requires",
            r"rubric.*expectations"
        ],
        "overly_strict": [
            r"too harsh",
            r"too strict",
            r"overly.*strict",
            r"should have been more lenient"
        ],
        "overly_generous": [
            r"too lenient",
            r"too generous",
            r"overly.*generous",
            r"gave full credit.*despite"
        ]
    }
    
    for category, patterns in common_patterns.items():
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, log_text, re.IGNORECASE))
        analysis["common_issues"][category] = count
    
    return analysis

def generate_prompt_recommendations(analysis: Dict) -> List[str]:
    """
    Generate specific recommendations for prompt improvements based on analysis.
    
    Args:
        analysis: Results from analyze_grading_logs()
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # High unfairness rate
    if analysis["unfairness_rate"] > 0.5:
        recommendations.append(
            "⚠️ HIGH UNFAIRNESS RATE: Consider making the reviewer more conservative. "
            "Current rate: {:.1%}".format(analysis["unfairness_rate"])
        )
    
    # File detection issues
    if analysis["common_issues"]["file_detection"] > 0:
        recommendations.append(
            "📁 FILE DETECTION ISSUES: Strengthen file detection instructions in OpenAI prompt. "
            "Add more explicit guidance about recognizing submitted documents."
        )
    
    # Rubric interpretation issues
    if analysis["common_issues"]["rubric_interpretation"] > 0:
        recommendations.append(
            "📋 RUBRIC INTERPRETATION ISSUES: Clarify rubric interpretation guidelines. "
            "Add examples of what constitutes meeting vs not meeting criteria."
        )
    
    # Overly strict grading
    if analysis["common_issues"]["overly_strict"] > analysis["common_issues"]["overly_generous"]:
        recommendations.append(
            "🎯 OVERLY STRICT GRADING: Consider making the grader more lenient. "
            "Focus on evidence of understanding rather than perfect execution."
        )
    
    # Score change analysis
    if analysis["score_changes"]:
        avg_change = sum(abs(new - old) for old, new in analysis["score_changes"]) / len(analysis["score_changes"])
        if avg_change > 30:
            recommendations.append(
                "📊 LARGE SCORE CHANGES: Significant revisions suggest fundamental grading issues. "
                "Review rubric clarity and grading criteria."
            )
    
    # Confidence analysis
    if analysis["confidence_scores"]:
        avg_confidence = sum(analysis["confidence_scores"]) / len(analysis["confidence_scores"])
        if avg_confidence < 0.7:
            recommendations.append(
                "🤔 LOW CONFIDENCE: Reviewer is uncertain about many decisions. "
                "Consider clarifying review criteria and thresholds."
            )
    
    return recommendations

def create_performance_report(log_text: str) -> str:
    """
    Create a comprehensive performance report from grading logs.
    
    Args:
        log_text: Raw grading log output
        
    Returns:
        Formatted report string
    """
    analysis = analyze_grading_logs(log_text)
    recommendations = generate_prompt_recommendations(analysis)
    
    report = f"""
# Grading Performance Report

## Summary Statistics
- Total Submissions: {analysis['total_submissions']}
- Unfair Flags: {analysis['unfair_flags']}
- Unfairness Rate: {analysis['unfairness_rate']:.1%}

## Common Issues Detected
"""
    
    for issue, count in analysis["common_issues"].items():
        if count > 0:
            report += f"- {issue.replace('_', ' ').title()}: {count} instances\n"
    
    if analysis["score_changes"]:
        avg_change = sum(abs(new - old) for old, new in analysis["score_changes"]) / len(analysis["score_changes"])
        report += f"\n## Score Changes\n- Average Score Change: {avg_change:.1f} points\n"
    
    if analysis["confidence_scores"]:
        avg_confidence = sum(analysis["confidence_scores"]) / len(analysis["confidence_scores"])
        report += f"- Average Confidence: {avg_confidence:.2f}\n"
    
    report += "\n## Recommendations\n"
    for rec in recommendations:
        report += f"- {rec}\n"
    
    return report

if __name__ == "__main__":
    # Example usage
    with open("grading_logs.txt", "r") as f:
        logs = f.read()
    
    report = create_performance_report(logs)
    print(report) 
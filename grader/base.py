"""
base.py
Abstract base classes for graders and reviewers.
All graders/reviewers should inherit from these to ensure a standard interface.
"""

from abc import ABC, abstractmethod

class GraderBase(ABC):
    """
    Abstract base class for AI grading engines.
    All graders must implement the grade() method.
    """

    @abstractmethod
    def grade(self, submission_text, rubric_items, pdf_path=None):
        """
        Grades a submission using a rubric.
        Args:
            submission_text (str): The student's (anonymized) submission as plain text.
            rubric_items (list): List of rubric criteria/dicts.
            pdf_path (str, optional): Path to PDF file for vision-based grading.
        Returns:
            dict: Grading results, e.g., rubric scores, feedback, etc.
        """
        pass

class ReviewerBase(ABC):
    """
    Abstract base class for AI fairness/review checkers.
    All reviewers must implement the review() method.
    """

    @abstractmethod
    def review(self, grading_result, rubric_items, submission_path):
        """
        Reviews a grading result for fairness or correctness.
        Args:
            grading_result (dict): The output from a grader (rubric scores, feedback).
            rubric_items (list): The rubric criteria.
            submission_path (str): Path to the student's original submission (PDF, etc.).
        Returns:
            tuple: (is_fair (bool), reason (str), revised_grade (dict), confidence (float))
        """
        pass

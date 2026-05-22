COLLECTION_NAME = "interview_questions"
VECTOR_SIZE = 512  # BAAI/bge-small-zh-v1.5 (Chinese-optimized, free)
DISTANCE_METRIC = "Cosine"

JOB_TYPES = ["backend", "frontend", "fullstack", "data", "devops", "mobile", "general"]
DIFFICULTY_LEVELS = ["easy", "medium", "hard"]
QUESTION_TYPES = ["behavioral", "technical", "system_design", "coding"]

PAYLOAD_SCHEMA = {
    "job_type": "keyword",
    "difficulty": "keyword",
    "tech_stack": "keyword[]",
    "question_type": "keyword",
    "question": "text",
    "answer_hint": "text",
}

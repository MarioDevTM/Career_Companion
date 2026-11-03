import json
from contextlib import contextmanager
import httpx

from src.schemas import (
    JobAnalysisOutput,
    QuizGenerationOutput,
    StudyPlanOutput,
    AnswerCoachOutput,
)
from src.services.ollama_service import OllamaService


class FakeHTTPResponse:
    def __init__(self, status_code=200, json_data=None, lines=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self._lines = list(lines or [])
        self.text = text

    def json(self):
        return self._json_data

    def iter_lines(self):
        for line in self._lines:
            yield line

    def read(self):
        return self.text.encode("utf-8")


class FakeOllamaHTTPClient:
    def __init__(self, get_responses=None, post_responses=None, stream_responses=None):
        self.get_responses = list(get_responses or [])
        self.post_responses = list(post_responses or [])
        self.stream_responses = list(stream_responses or [])
        self.get_calls = []
        self.post_calls = []
        self.stream_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        outcome = self.get_responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        outcome = self.post_responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    @contextmanager
    def stream(self, method, url, **kwargs):
        self.stream_calls.append((method, url, kwargs))
        outcome = self.stream_responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        yield outcome


def test_ollama_connectivity_and_model_availability_success():
    fake_client = FakeOllamaHTTPClient(
        get_responses=[
            FakeHTTPResponse(200, {"models": [{"name": "qwen2.5:0.5b"}]})
        ],
        post_responses=[
            FakeHTTPResponse(
                200,
                {
                    "message": {"role": "assistant", "content": "CONNECTION_OK"},
                    "done": True,
                    "prompt_eval_count": 18,
                    "eval_count": 4,
                },
            )
        ],
    )
    service = OllamaService(
        base_url="http://localhost:11434",
        model_name="qwen2.5:0.5b",
        http_client=fake_client,
    )
    res = service.check_connection()
    assert res.success is True
    assert res.text == "CONNECTION_OK"
    assert res.model_used == "qwen2.5:0.5b"
    assert res.total_tokens == 22


def test_ollama_service_unavailable_returns_clear_error():
    fake_client = FakeOllamaHTTPClient(
        get_responses=[httpx.ConnectError("Connection refused")]
    )
    service = OllamaService(
        base_url="http://localhost:11434",
        model_name="qwen2.5:0.5b",
        http_client=fake_client,
    )
    res = service.check_connection()
    assert res.success is False
    assert res.error_type == "service_unavailable"
    assert "ollama serve" in (res.error_message or "")


def test_missing_local_model_returns_pull_instruction():
    fake_client = FakeOllamaHTTPClient(
        get_responses=[
            FakeHTTPResponse(200, {"models": [{"name": "llama3:8b"}]})
        ]
    )
    service = OllamaService(
        base_url="http://localhost:11434",
        model_name="qwen2.5:0.5b",
        http_client=fake_client,
    )
    res = service.check_connection()
    assert res.success is False
    assert res.error_type == "model_not_found"
    assert "ollama pull qwen2.5:0.5b" in (res.error_message or "")


def test_structured_outputs_across_all_modes():
    job_json = JobAnalysisOutput(
        role_summary="Python Backend Engineer",
        explicit_requirements=["Python", "SQLAlchemy"],
        ai_inferences=["REST API design"],
        skill_breakdown=[],
        unknowns_and_gaps=["Team size unknown"],
        proposed_tasks=[],
    ).model_dump_json()

    quiz_json = QuizGenerationOutput(
        topic_summary="SQLAlchemy Basics",
        questions=[
            {
                "question_text": "What does selectinload avoid?",
                "options": ["Cartesian products", "Indexes", "Transactions", "Foreign keys"],
                "correct_option_index": 0,
                "explanation": "It uses a second SELECT with IN.",
                "source_citation": None,
                "suggested_revisit_topic": "ORM Relationship Loading",
            }
        ],
    ).model_dump_json()

    plan_json = StudyPlanOutput(
        plan_title="2-Week Python Plan",
        rationale="Focused on upcoming interview",
        milestones=[
            {
                "day_or_week_label": "Week 1",
                "focus_topic": "SQLAlchemy 2.0",
                "activities": ["Build sample schema"],
                "estimated_minutes": 90,
            }
        ],
        proposed_tasks=[],
    ).model_dump_json()

    coach_json = AnswerCoachOutput(
        critique_strengths=["Clear situation"],
        critique_gaps=["Missing latency metric"],
        improved_draft="I profiled the SQL queries and added an index.",
        unverified_placeholders_needed=["By what percentage did latency drop?"],
    ).model_dump_json()

    fake_client = FakeOllamaHTTPClient(
        post_responses=[
            FakeHTTPResponse(200, {"message": {"content": job_json}, "done": True}),
            FakeHTTPResponse(200, {"message": {"content": quiz_json}, "done": True}),
            FakeHTTPResponse(200, {"message": {"content": plan_json}, "done": True}),
            FakeHTTPResponse(200, {"message": {"content": coach_json}, "done": True}),
        ]
    )
    service = OllamaService(http_client=fake_client)

    r_job = service.generate_structured("Analyze job", JobAnalysisOutput)
    assert r_job.success and isinstance(r_job.structured_data, JobAnalysisOutput)

    r_quiz = service.generate_structured("Make quiz", QuizGenerationOutput)
    assert r_quiz.success and isinstance(r_quiz.structured_data, QuizGenerationOutput)

    r_plan = service.generate_structured("Make plan", StudyPlanOutput)
    assert r_plan.success and isinstance(r_plan.structured_data, StudyPlanOutput)

    r_coach = service.generate_structured("Coach answer", AnswerCoachOutput)
    assert r_coach.success and isinstance(r_coach.structured_data, AnswerCoachOutput)


def test_invalid_structured_output_fails_gracefully():
    fake_client = FakeOllamaHTTPClient(
        post_responses=[
            FakeHTTPResponse(200, {"message": {"content": '{"wrong_shape": true}'}, "done": True}),
            FakeHTTPResponse(200, {"message": {"content": '{"still_wrong": true}'}, "done": True}),
        ]
    )
    service = OllamaService(http_client=fake_client)
    res = service.generate_structured("Analyze", JobAnalysisOutput, max_retries=1)
    assert res.success is False
    assert res.error_type == "invalid_structured_output"
    assert res.structured_data is None


def test_streaming_chat_and_timeout_handling():
    lines = [
        json.dumps({"message": {"content": "Hello "}, "done": False}),
        json.dumps({"message": {"content": "from Qwen!"}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True, "prompt_eval_count": 10, "eval_count": 5}),
    ]
    fake_client = FakeOllamaHTTPClient(
        stream_responses=[FakeHTTPResponse(200, lines=lines)]
    )
    service = OllamaService(http_client=fake_client)
    stream_call = service.generate_text_stream("Greet me", max_retries=0)
    text = "".join(stream_call)
    assert text == "Hello from Qwen!"
    assert stream_call.result.success is True
    assert stream_call.result.total_tokens == 15

    # Timeout case
    timeout_client = FakeOllamaHTTPClient(
        post_responses=[httpx.ReadTimeout("Read timed out")]
    )
    timeout_service = OllamaService(http_client=timeout_client)
    timeout_res = timeout_service.generate_text("Slow prompt", max_retries=0)
    assert timeout_res.success is False
    assert timeout_res.error_type == "inference_timeout"

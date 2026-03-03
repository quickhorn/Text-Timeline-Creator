"""
Tests for the timeline builder module.
"""

from datetime import datetime
from src.timeline_builder import build_timeline
from src.models import Message, Timeline


class TestBuildTimeline:
    """Tests for build_timeline function."""

    def test_sorts_by_date(self):
        """Messages should be sorted earliest-first."""
        m1 = Message(text="Later", source_file="b.jpg", date=datetime(2024, 3, 15))
        m2 = Message(text="Earlier", source_file="a.jpg", date=datetime(2024, 3, 10))
        timeline = build_timeline([m1, m2])
        assert timeline.messages[0].text == "Earlier"
        assert timeline.messages[1].text == "Later"

    def test_undated_placed_at_end(self):
        """Undated messages should appear after all dated messages."""
        dated = Message(text="Dated", source_file="a.jpg", date=datetime(2024, 1, 1))
        undated = Message(text="Undated", source_file="b.jpg")
        timeline = build_timeline([undated, dated])
        assert timeline.messages[0].text == "Dated"
        assert timeline.messages[1].text == "Undated"

    def test_returns_timeline_object(self):
        msgs = [Message(text="Hi", source_file="a.jpg", date=datetime(2024, 1, 1))]
        result = build_timeline(msgs)
        assert isinstance(result, Timeline)

    def test_empty_list(self):
        """Empty input should produce an empty timeline."""
        timeline = build_timeline([])
        assert len(timeline.messages) == 0

    def test_all_undated(self):
        """All undated messages should still be included."""
        m1 = Message(text="A", source_file="a.jpg")
        m2 = Message(text="B", source_file="b.jpg")
        timeline = build_timeline([m1, m2])
        assert len(timeline.messages) == 2

    def test_single_message(self):
        msg = Message(text="Only one", source_file="a.jpg", date=datetime(2024, 6, 1))
        timeline = build_timeline([msg])
        assert len(timeline.messages) == 1
        assert timeline.messages[0].text == "Only one"

    def test_preserves_all_messages(self):
        """No messages should be lost during sorting."""
        msgs = [
            Message(text="C", source_file="c.jpg", date=datetime(2024, 3, 1)),
            Message(text="A", source_file="a.jpg", date=datetime(2024, 1, 1)),
            Message(text="U", source_file="u.jpg"),
            Message(text="B", source_file="b.jpg", date=datetime(2024, 2, 1)),
        ]
        timeline = build_timeline(msgs)
        assert len(timeline.messages) == 4

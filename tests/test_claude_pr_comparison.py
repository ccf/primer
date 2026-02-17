class TestClaudePRComparison:
    def test_comparison_no_prs(self, client, admin_headers):
        """Returns zeros when no PR tracking exists (feature not yet implemented)."""
        r = client.get(
            "/api/v1/analytics/claude-pr-comparison",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["total_prs_analyzed"] == 0
        assert data["claude_assisted"]["pr_count"] == 0
        assert data["non_claude"]["pr_count"] == 0
        assert data["delta_review_comments"] is None
        assert data["delta_merge_time_hours"] is None
        assert data["delta_merge_rate"] is None

    def test_comparison_returns_empty_metrics(self, client, admin_headers):
        """Verify the response structure is correct with all expected fields."""
        r = client.get(
            "/api/v1/analytics/claude-pr-comparison",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        # Verify top-level keys
        assert "claude_assisted" in data
        assert "non_claude" in data
        assert "delta_review_comments" in data
        assert "delta_merge_time_hours" in data
        assert "delta_merge_rate" in data
        assert "total_prs_analyzed" in data

        # Verify PRGroupMetrics structure for both groups
        for group_key in ("claude_assisted", "non_claude"):
            group = data[group_key]
            assert "pr_count" in group
            assert "merge_rate" in group
            assert "avg_review_comments" in group
            assert "avg_time_to_merge_hours" in group
            assert "avg_additions" in group
            assert "avg_deletions" in group

            # All metrics should be None/zero since no PR data exists
            assert group["pr_count"] == 0
            assert group["merge_rate"] is None
            assert group["avg_review_comments"] is None
            assert group["avg_time_to_merge_hours"] is None
            assert group["avg_additions"] is None
            assert group["avg_deletions"] is None

"""Tests for the glob matcher and auto-detect module."""

from __future__ import annotations

from repomix_attribution.matcher import (
    AUTO_DETECT_RULES,
    MONOREPO_PREFIXES,
    auto_detect_category,
    compile_patterns,
    match_category,
    pattern_to_regex,
)


# ---------------------------------------------------------------------------
# pattern_to_regex
# ---------------------------------------------------------------------------


class TestPatternToRegex:
    def test_exact_path(self):
        regex = pattern_to_regex("README.md")
        assert regex.match("README.md")
        assert not regex.match("src/README.md")

    def test_single_star(self):
        regex = pattern_to_regex("src/*.ts")
        assert regex.match("src/main.ts")
        assert regex.match("src/utils/helper.ts") is None

    def test_double_star(self):
        regex = pattern_to_regex("src/**")
        assert regex.match("src/main.ts")
        assert regex.match("src/utils/helper.ts")
        assert regex.match("src/a/b/c/d.ts")

    def test_double_star_with_extension(self):
        regex = pattern_to_regex("docs/**/*.md")
        assert regex.match("docs/guide.md")
        assert regex.match("docs/api/v2/guide.md")
        assert not regex.match("src/guide.md")

    def test_question_mark(self):
        regex = pattern_to_regex("src/file?.ts")
        assert regex.match("src/file1.ts")
        assert regex.match("src/fileA.ts")
        assert not regex.match("src/file12.ts")

    def test_literal_dot(self):
        regex = pattern_to_regex("src/test.spec.ts")
        assert regex.match("src/test.spec.ts")
        assert not regex.match("src/testXspec.ts")

    def test_escaped_special_chars(self):
        regex = pattern_to_regex("path/to/file(1).ts")
        assert regex.match("path/to/file(1).ts")
        assert not regex.match("path/to/fileABC.ts")

    def test_dotstar_in_pattern(self):
        regex = pattern_to_regex("**/*.js")
        assert regex.match("main.js")
        assert regex.match("src/utils/helper.js")
        assert not regex.match("src/main.ts")


# ---------------------------------------------------------------------------
# compile_patterns / match_category
# ---------------------------------------------------------------------------


class TestCompileAndMatch:
    def test_compiles_and_matches(self):
        compiled = compile_patterns(["src/**", "test/**"])
        assert match_category("src/main.ts", compiled) == "src/**"
        assert match_category("test/unit.spec.ts", compiled) == "test/**"

    def test_returns_none_for_no_match(self):
        compiled = compile_patterns(["src/**"])
        assert match_category("docs/readme.md", compiled) is None

    def test_first_match_wins(self):
        compiled = compile_patterns(["src/**", "src/**/*.test.ts"])
        assert match_category("src/app.test.ts", compiled) == "src/**"

    def test_normalized_to_posix(self):
        compiled = compile_patterns(["src/**"])
        # Windows-style paths should still match
        assert match_category("src\\main.ts", compiled) == "src/**"


# ---------------------------------------------------------------------------
# Auto-detect
# ---------------------------------------------------------------------------


class TestAutoDetect:
    def test_src(self):
        assert auto_detect_category("src/main.ts") == "src"

    def test_test(self):
        assert auto_detect_category("test/unit.spec.ts") == "test"

    def test_tests(self):
        assert auto_detect_category("tests/integration.py") == "tests"

    def test_docs(self):
        assert auto_detect_category("docs/api.md") == "docs"

    def test_packages_monorepo(self):
        assert auto_detect_category("packages/foo/src/bar.ts") == "packages/foo"

    def test_apps_monorepo(self):
        assert auto_detect_category("apps/web/index.html") == "apps/web"

    def test_packages_without_subdir(self):
        assert auto_detect_category("packages/shared/lib.ts") == "packages/shared"

    def test_unknown_top_level(self):
        assert auto_detect_category("custom/dir/file.ts") == "custom/**"

    def test_root_file(self):
        assert auto_detect_category("README.md") == "README.md"

    def test_empty_path(self):
        assert auto_detect_category("") == "root"

    def test_github_actions(self):
        assert auto_detect_category(".github/workflows/ci.yml") == ".github"

    def test_config_dir(self):
        assert auto_detect_category("config/db.yaml") == "config"

    def test_infra_dir(self):
        assert auto_detect_category("infra/terraform/main.tf") == "infra"

    def test_deploy_dir(self):
        assert auto_detect_category("deploy/k8s/deployment.yaml") == "deploy"

    def test_ci_dir(self):
        assert auto_detect_category("ci/scripts/lint.sh") == "ci"

    def test_tools_dir(self):
        assert auto_detect_category("tools/codegen/main.py") == "tools"

    def test_examples_dir(self):
        assert auto_detect_category("examples/basic.ts") == "examples"

    def test_fixtures_dir(self):
        assert auto_detect_category("fixtures/sample.json") == "fixtures"

    def test_assets_dir(self):
        assert auto_detect_category("assets/logo.svg") == "assets"

    def test_scripts_dir(self):
        assert auto_detect_category("scripts/deploy.sh") == "scripts"

    def test_lib_dir(self):
        assert auto_detect_category("lib/utils.ts") == "lib"

    # Verify rule ordering: monorepo takes precedence
    def test_monorepo_precedence_over_test(self):
        # packages/foo/test/unit.ts -> packages/foo (monorepo wins)
        assert auto_detect_category("packages/foo/test/unit.ts") == "packages/foo"

    def test_test_precedence_over_src(self):
        # test/unit.ts -> test (test rule comes before src in AUTO_DETECT_RULES)
        assert auto_detect_category("test/unit.ts") == "test"

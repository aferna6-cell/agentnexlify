import argparse
import html
import re
import urllib.parse
import urllib.request

from .skill_creator import SkillCreator


class SkillSearch:
    SEARCH_ENDPOINT = "https://duckduckgo.com/html/?q={query}"

    def search_external_workflows(self, query: str, max_results: int = 5) -> list[dict]:
        encoded = urllib.parse.quote_plus(f"{query} deterministic workflow")
        url = self.SEARCH_ENDPOINT.format(query=encoded)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AgentNexLiFySkillSearch/1.0 (+https://agentnexlify.com)"
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = response.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            return [
                {
                    "title": "external-search-unavailable",
                    "url": "",
                    "snippet": str(exc),
                    "error": True,
                    "source": "duckduckgo",
                }
            ]

        links = re.findall(
            r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            payload,
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippets = re.findall(
            r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>|<div[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</div>',
            payload,
            flags=re.IGNORECASE | re.DOTALL,
        )

        results = []
        for index, (url_match, title_html) in enumerate(links[:max_results]):
            snippet_html = ""
            if index < len(snippets):
                snippet_html = snippets[index][0] or snippets[index][1]
            results.append(
                {
                    "title": self._clean_html(title_html),
                    "url": html.unescape(url_match),
                    "snippet": self._clean_html(snippet_html),
                    "source": "duckduckgo",
                }
            )
        return results

    def fetch_external_workflow(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AgentNexLiFySkillSearch/1.0 (+https://agentnexlify.com)"
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return self._clean_html(response.read().decode("utf-8", errors="ignore"))

    def normalize_external_workflow(self, query: str, result: dict) -> dict:
        raw_text = ""
        if result.get("url"):
            try:
                raw_text = self.fetch_external_workflow(result["url"])
            except Exception:
                raw_text = result.get("snippet", "")
        else:
            raw_text = result.get("snippet", "")

        steps = self._extract_steps(raw_text)
        if not steps:
            steps = [
                "Inspect the referenced workflow source and confirm it applies to the repository context.",
                "Adapt the workflow to current repository constraints before automation.",
                "Store the normalized workflow as a generated skill for future reuse.",
            ]

        return {
            "name": result.get("title") or f"external-workflow-{query}",
            "purpose": (
                f"Normalized external workflow for: {query}. "
                f"Source: {result.get('url') or result.get('source', 'external')}"
            ),
            "when_to_use": [
                f"Use when local skills do not cover the task: {query}",
                "Use when the external workflow has been reviewed and matches repository constraints.",
            ],
            "inputs": ["task_description", "repository context", "external source material"],
            "workflow_steps": steps[:7],
            "constraints": [
                "Review the external workflow before applying it to production code.",
                "Never copy secrets, credentials, or schema changes without a migration.",
                "Normalize the workflow to repository conventions before reuse.",
            ],
            "examples": [
                query,
                result.get("url") or result.get("snippet", "external-source"),
            ],
        }

    def convert_external_workflow(self, query: str, result: dict, creator: SkillCreator | None = None):
        creator = creator or SkillCreator()
        normalized = self.normalize_external_workflow(query, result)
        return creator.create_skill(
            name=normalized["name"],
            purpose=normalized["purpose"],
            when_to_use=normalized["when_to_use"],
            inputs=normalized["inputs"],
            workflow_steps=normalized["workflow_steps"],
            constraints=normalized["constraints"],
            examples=normalized["examples"],
            created_by="external-search",
        )

    def _extract_steps(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        steps = []
        for line in lines:
            if re.match(r"^(\d+[\.\)]|[-*])\s+", line):
                cleaned = re.sub(r"^(\d+[\.\)]|[-*])\s+", "", line).strip()
                if cleaned and cleaned not in steps:
                    steps.append(cleaned)
            if len(steps) >= 7:
                break
        return steps

    def _clean_html(self, text: str) -> str:
        stripped = re.sub(r"<[^>]+>", " ", text or "")
        stripped = html.unescape(stripped)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        return stripped


def main() -> None:
    parser = argparse.ArgumentParser(description="Search for external workflow patterns.")
    parser.add_argument("query", help="Workflow query.")
    parser.add_argument("--convert", action="store_true", help="Convert the best result into a generated skill.")
    args = parser.parse_args()

    search = SkillSearch()
    results = search.search_external_workflows(args.query)
    if args.convert and results:
        print({"skill_path": str(search.convert_external_workflow(args.query, results[0]))})
    else:
        print(results)


if __name__ == "__main__":
    main()

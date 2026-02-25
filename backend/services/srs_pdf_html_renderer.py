"""
HTML-to-PDF renderer for SRS exports using Playwright (Node.js).
Falls back to legacy FPDF path when Playwright runtime is unavailable.
"""
from __future__ import annotations

import html
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def render_srs_pdf_html(draft: Any) -> bytes:
    project_root = Path(__file__).resolve().parents[2]
    renderer_script = project_root / "backend" / "tools" / "render_html_to_pdf.cjs"

    if not renderer_script.exists():
        raise RuntimeError(f"Renderer script not found: {renderer_script}")

    html_content = _build_srs_html(draft)

    with tempfile.TemporaryDirectory(prefix="srs-html-export-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        html_path = tmp_path / "srs.html"
        pdf_path = tmp_path / "srs.pdf"

        html_path.write_text(html_content, encoding="utf-8")

        process = subprocess.run(
            [
                "node",
                str(renderer_script),
                str(html_path),
                str(pdf_path),
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )

        if process.returncode != 0:
            stderr = (process.stderr or process.stdout or "unknown renderer error").strip()
            raise RuntimeError(f"HTML-to-PDF renderer failed: {stderr}")

        if not pdf_path.exists():
            raise RuntimeError("HTML-to-PDF renderer did not produce output file")

        return pdf_path.read_bytes()


def _safe(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _li_items(items: Any) -> str:
    if not isinstance(items, list):
        items = [items]
    cleaned = [html.escape(_safe(item).strip()) for item in items if _safe(item).strip()]
    if not cleaned:
        return "<p class=\"muted\">No items provided.</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in cleaned) + "</ul>"


def _normalize_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _build_metrics_rows(metrics: list[Any], is_ar: bool) -> str:
    rows = []
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        label = html.escape(_safe(metric.get("label", "")))
        value = html.escape(_safe(metric.get("value", "")))
        rows.append(f"<tr><td>{label}</td><td>{value}</td></tr>")

    if rows:
        return "".join(rows)

    empty = "لا توجد مقاييس" if is_ar else "No metrics"
    return f"<tr><td colspan=\"2\" class=\"muted\">{empty}</td></tr>"


def _build_sections_html(sections: list[Any]) -> str:
    blocks: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = html.escape(_safe(section.get("title", "Section")))
        confidence = html.escape(_safe(section.get("confidence", "")))
        heading = f"{title} <span class=\"confidence\">[{confidence}]</span>" if confidence else title
        body = _li_items(section.get("items", []))
        blocks.append(f"<section class=\"block\"><h3>{heading}</h3>{body}</section>")

    return "".join(blocks)


def _build_activity_diagrams_html(activity_diagrams: list[Any], labels: dict[str, str], is_ar: bool) -> str:
    if not activity_diagrams:
        empty = "لا توجد عناصر" if is_ar else "No items provided."
        return f"<p class=\"muted\">{empty}</p>"

    blocks: list[str] = []
    for idx, diagram in enumerate(activity_diagrams, 1):
        if not isinstance(diagram, dict):
            continue
        title = html.escape(_safe(diagram.get("title") or f"{labels['activity']} {idx}"))
        body = ""
        mermaid_code = _safe(diagram.get("activity_diagram_mermaid") or "").strip()
        if mermaid_code:
            body += f"<pre class=\"mermaid\">\n{html.escape(mermaid_code)}\n</pre>\n<br>\n"
            
        flow_lines = _normalize_list(diagram.get("activity_diagram"))
        if flow_lines:
            body += _li_items(flow_lines)

        blocks.append(f"<section class=\"block\"><h3>{title}</h3>{body}</section>")

    if not blocks:
        empty = "لا توجد عناصر" if is_ar else "No items provided."
        return f"<p class=\"muted\">{empty}</p>"
    return "".join(blocks)


def _localized_labels(is_ar: bool) -> dict[str, str]:
    if is_ar:
        return {
        "title": "مواصفات متطلبات البرمجيات",
        "subtitle": "توليد ذكي عبر Tawasul AI",
        "lang_label": "العربية",
        "project_id": "رقم المشروع",
        "version": "الإصدار",
        "language": "اللغة",
        "status": "الحالة",
        "summary": "الملخص التنفيذي",
        "summary_empty": "لا يوجد ملخص",
        "metrics": "المقاييس الرئيسية",
        "metric_col": "المقياس",
        "value_col": "القيمة",
        "activity": "مخطط النشاط",
        "questions": "أسئلة مفتوحة",
        "next_steps": "الخطوات التالية",
        "user_stories": "قصص المستخدمين ومعايير القبول",
        "user_roles": "أدوار المستخدمين",
        "role_col": "الدور",
        "desc_col": "الوصف",
        "perm_col": "الصلاحيات",
        "as_a": "بوصفي",
        "i_want": "أريد",
        "so_that": "حتى أتمكن من",
        "ac_label": "معايير القبول",
        }

    return {
        "title": "Software Requirements Specification",
        "subtitle": "Generated by Tawasul AI",
        "lang_label": "English",
        "project_id": "Project ID",
        "version": "Version",
        "language": "Language",
        "status": "Status",
        "summary": "Executive Summary",
        "summary_empty": "No summary",
        "metrics": "Key Metrics",
        "metric_col": "Metric",
        "value_col": "Value",
        "activity": "Activity Diagram",
        "questions": "Open Questions",
        "next_steps": "Next Steps",
        "user_stories": "User Stories & Acceptance Criteria",
        "user_roles": "User Roles",
        "role_col": "Role",
        "desc_col": "Description",
        "perm_col": "Permissions",
        "as_a": "As a",
        "i_want": "I want to",
        "so_that": "so that",
        "ac_label": "Acceptance Criteria",
    }


def _build_user_stories_html(user_stories: list[Any], labels: dict[str, str]) -> str:
    if not user_stories:
        return ""
    rows: list[str] = []
    for story in user_stories:
        if not isinstance(story, dict):
            continue
        role = html.escape(_safe(story.get("role", "")))
        action = html.escape(_safe(story.get("action", "")))
        goal = html.escape(_safe(story.get("goal", "")))
        ac_items = story.get("acceptance_criteria")
        ac_html = ""
        if isinstance(ac_items, list) and ac_items:
            items_html = "".join(
                f"<li>✓ {html.escape(_safe(ac))}</li>"
                for ac in ac_items
                if _safe(ac).strip()
            )
            if items_html:
                ac_html = (
                    f"<details class=\"ac-details\">"
                    f"<summary>{labels['ac_label']} ({len(ac_items)})</summary>"
                    f"<ul>{items_html}</ul></details>"
                )
        statement = (
            f"<strong>{labels['as_a']}</strong> {role}, "
            f"<strong>{labels['i_want']}</strong> {action}, "
            f"<strong>{labels['so_that']}</strong> {goal}"
        )
        rows.append(
            f"<div class=\"story-card\"><p class=\"story-statement\">{statement}</p>{ac_html}</div>"
        )
    if not rows:
        return ""
    return (
        f"<section class=\"block\"><h3>{labels['user_stories']}</h3>"
        + "".join(rows)
        + "</section>"
    )


def _build_user_roles_html(user_roles: list[Any], labels: dict[str, str]) -> str:
    if not user_roles:
        return ""
    rows: list[str] = []
    for ur in user_roles:
        if not isinstance(ur, dict):
            continue
        role = html.escape(_safe(ur.get("role", "")))
        desc = html.escape(_safe(ur.get("description", "")))
        perms = ur.get("permissions")
        perms_html = ""
        if isinstance(perms, list) and perms:
            perms_html = ", ".join(html.escape(_safe(p)) for p in perms if _safe(p).strip())
        rows.append(f"<tr><td><strong>{role}</strong></td><td>{desc}</td><td>{perms_html}</td></tr>")
    if not rows:
        return ""
    return (
        f"<section class=\"block\"><h3>{labels['user_roles']}</h3>"
        f"<table><thead><tr>"
        f"<th>{labels['role_col']}</th><th>{labels['desc_col']}</th><th>{labels['perm_col']}</th>"
        f"</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></section>"
    )


def _build_srs_html(draft: Any) -> str:
    content = getattr(draft, "content", {}) or {}
    language = getattr(draft, "language", "en")
    is_ar = language == "ar"
    direction = "rtl" if is_ar else "ltr"
    labels = _localized_labels(is_ar)

    summary = html.escape(_safe(content.get("summary", "")))
    metrics = _normalize_list(content.get("metrics"))
    sections = _normalize_list(content.get("sections"))
    questions = _normalize_list(content.get("questions"))
    next_steps = _normalize_list(content.get("next_steps"))
    activity_diagram = _normalize_list(content.get("activity_diagram"))
    activity_diagrams = _normalize_list(content.get("activity_diagrams"))

    if activity_diagrams:
      normalized_multi = []
      for item in activity_diagrams:
        if isinstance(item, dict):
          normalized_multi.append(item)
      activity_diagrams = normalized_multi

    if not activity_diagrams and activity_diagram:
      activity_diagrams = [{
        "title": labels["activity"],
        "activity_diagram": activity_diagram,
      }]

    metrics_rows = _build_metrics_rows(metrics=metrics, is_ar=is_ar)
    sections_html = _build_sections_html(sections)

    activity_html = _build_activity_diagrams_html(activity_diagrams, labels, is_ar)
    questions_html = _li_items(questions)
    next_steps_html = _li_items(next_steps)

    user_stories = _normalize_list(content.get("user_stories"))
    user_roles = _normalize_list(content.get("user_roles"))
    user_stories_html = _build_user_stories_html(user_stories, labels)
    user_roles_html = _build_user_roles_html(user_roles, labels)

    return f"""
<!doctype html>
<html lang=\"{'ar' if is_ar else 'en'}\" dir=\"{direction}\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    @page {{ size: A4; margin: 18mm 14mm; }}
    body {{ font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif; color: #212529; font-size: 12px; line-height: 1.55; }}
    .cover {{ border-bottom: 2px solid #e85d2a; padding-bottom: 12px; margin-bottom: 18px; }}
    h1 {{ margin: 0; font-size: 24px; color: #e85d2a; }}
    h2 {{ margin: 4px 0 0 0; font-size: 13px; color: #6c757d; font-weight: 500; }}
    h3 {{ font-size: 15px; margin: 0 0 8px 0; color: #e85d2a; }}
    .meta {{ margin-top: 10px; font-size: 11px; color: #495057; display: grid; grid-template-columns: 1fr 1fr; gap: 3px 12px; }}
    .block {{ margin: 0 0 14px 0; page-break-inside: avoid; }}
    .summary {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 10px; white-space: pre-wrap; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #dee2e6; padding: 7px; text-align: start; vertical-align: top; }}
    th {{ background: #e85d2a; color: #fff; }}
    ul {{ margin: 0; padding-inline-start: 18px; }}
    li {{ margin-bottom: 4px; }}
    .confidence {{ font-size: 11px; color: #6c757d; }}
    .muted {{ color: #6c757d; margin: 0; }}
    .section-title {{ margin-top: 16px; }}
    .story-card {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 8px 10px; margin-bottom: 8px; }}
    .story-statement {{ margin: 0 0 4px 0; }}
    .ac-details {{ margin-top: 4px; font-size: 11px; }}
    .ac-details summary {{ cursor: pointer; color: #6c757d; }}
  </style>
</head>
<body>
  <section class=\"cover\">
    <h1>{labels['title']}</h1>
    <h2>{labels['subtitle']}</h2>
    <div class=\"meta\">
      <div><strong>{labels['project_id']}:</strong> {html.escape(str(getattr(draft, 'project_id', '')))}</div>
      <div><strong>{labels['version']}:</strong> v{html.escape(str(getattr(draft, 'version', '')))}</div>
      <div><strong>{labels['language']}:</strong> {labels['lang_label']}</div>
      <div><strong>{labels['status']}:</strong> {html.escape(_safe(getattr(draft, 'status', 'draft')))}</div>
    </div>
  </section>

  <section class=\"block\">
    <h3>{labels['summary']}</h3>
    <div class=\"summary\">{summary or labels['summary_empty']}</div>
  </section>

  <section class=\"block\">
    <h3>{labels['metrics']}</h3>
    <table>
      <thead>
        <tr>
          <th>{labels['metric_col']}</th>
          <th>{labels['value_col']}</th>
        </tr>
      </thead>
      <tbody>
        {metrics_rows}
      </tbody>
    </table>
  </section>

  {sections_html}

  {user_stories_html}

  {user_roles_html}

  <section class=\"block section-title\">
    <h3>{labels['activity']}</h3>
    {activity_html}
  </section>

  <section class=\"block\">
    <h3>{labels['questions']}</h3>
    {questions_html}
  </section>

  <section class="block">
    <h3>{labels['next_steps']}</h3>
    {next_steps_html}
  </section>

  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
  </script>
</body>
</html>
"""

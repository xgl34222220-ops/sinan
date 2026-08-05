from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL_PATH = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppShellV2.kt"
APP_PATH = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt"
CHAT_PATH = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AiChatDialog.kt"
ARCHIVE_PATH = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedArchive.kt"


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def transform_function(text: str, start: str, end: str, transform) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    block = text[start_index:end_index]
    updated = transform(block)
    return text[:start_index] + updated + text[end_index:]


def apply_cloud_source_grouping() -> None:
    helper_branch = "origin/hotfix/v5.9.6-chat-and-cloud-sources"
    tools = ROOT / "tools"
    tools.mkdir(exist_ok=True)
    for name in (
        "apply_v596_chat_cloud_sources.py",
        "run_v596_chat_cloud_sources.py",
    ):
        content = run("git", "show", f"{helper_branch}:tools/{name}", capture=True)
        (tools / name).write_text(content, encoding="utf-8")

    run("python3", "tools/run_v596_chat_cloud_sources.py")

    # The user clarified that the reported clipping is the five-item bottom bar,
    # not the full-screen AI conversation. Restore those two files exactly.
    run(
        "git",
        "checkout",
        "origin/main",
        "--",
        str(APP_PATH.relative_to(ROOT)),
        str(CHAT_PATH.relative_to(ROOT)),
    )


def apply_bottom_navigation_fix() -> None:
    text = SHELL_PATH.read_text(encoding="utf-8")

    def update_bar(block: str) -> str:
        block = replace_once(
            block,
            ".heightIn(min = 64.dp, max = 72.dp)",
            ".heightIn(min = 72.dp)",
            "bottom bar adaptive height",
        )
        return replace_once(
            block,
            ".padding(horizontal = 4.dp, vertical = 4.dp)",
            ".padding(horizontal = 4.dp, vertical = 5.dp)",
            "bottom bar vertical padding",
        )

    text = transform_function(
        text,
        "@Composable\nfun MainBottomBar(",
        "@Composable\nprivate fun StandardNavItem(",
        update_bar,
    )

    def update_standard(block: str) -> str:
        block = replace_once(
            block,
            ".height(56.dp)",
            ".heightIn(min = 58.dp)",
            "standard nav adaptive height",
        )
        return replace_once(
            block,
            """            fontSize = 10.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
        )""",
            """            fontSize = 10.sp,
            lineHeight = 14.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
            maxLines = 1,
        )""",
            "standard nav label line height",
        )

    text = transform_function(
        text,
        "@Composable\nprivate fun StandardNavItem(",
        "@Composable\nprivate fun ChatNavItem(",
        update_standard,
    )

    def update_chat(block: str) -> str:
        block = replace_once(
            block,
            ".height(56.dp)",
            ".heightIn(min = 60.dp)",
            "AI nav adaptive height",
        )
        block = replace_once(
            block,
            ".clip(RoundedCornerShape(16.dp))\n            .clickable(",
            ".clip(RoundedCornerShape(16.dp))\n            .padding(vertical = 2.dp)\n            .clickable(",
            "AI nav inner padding",
        )
        if block.count("Modifier.size(42.dp)") != 2:
            raise RuntimeError("AI nav: expected two 42dp size declarations")
        block = block.replace("Modifier.size(42.dp)", "Modifier.size(38.dp)")
        block = replace_once(block, ".size(35.dp)", ".size(33.dp)", "AI center size")
        block = replace_once(
            block,
            "modifier = Modifier.size(18.dp),",
            "modifier = Modifier.size(17.dp),",
            "AI icon size",
        )
        block = replace_once(
            block,
            """            }
        }
        Text(
            if (isRunning) "运行中" else "AI",""",
            """            }
        }
        Spacer(Modifier.height(1.dp))
        Text(
            if (isRunning) "运行中" else "AI",""",
            "AI label spacing",
        )
        return replace_once(
            block,
            """            color = colors.accent,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
        )""",
            """            color = colors.accent,
            fontSize = 10.sp,
            lineHeight = 14.sp,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
        )""",
            "AI label line height",
        )

    text = transform_function(
        text,
        "@Composable\nprivate fun ChatNavItem(",
        "@Composable\nfun CompactLotterySwitcher(",
        update_chat,
    )

    SHELL_PATH.write_text(text, encoding="utf-8")


def assert_scope() -> None:
    shell = SHELL_PATH.read_text(encoding="utf-8")
    app = APP_PATH.read_text(encoding="utf-8")
    chat = CHAT_PATH.read_text(encoding="utf-8")
    archive = ARCHIVE_PATH.read_text(encoding="utf-8")

    assert ".heightIn(min = 72.dp)" in shell
    assert ".heightIn(min = 60.dp)" in shell
    assert "Spacer(Modifier.height(1.dp))" in shell
    assert "if (!showChat) {" not in app
    assert "WindowInsets.safeDrawing" not in chat
    for label in (
        "手机独立 AI",
        "天机云端 AI",
        "天机云端本地",
        "手机本地模型",
    ):
        assert label in archive


if __name__ == "__main__":
    apply_cloud_source_grouping()
    apply_bottom_navigation_fix()
    assert_scope()
    print("Applied focused Tianji v5.9.6 bottom navigation and source grouping fix.")

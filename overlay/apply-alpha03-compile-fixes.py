from pathlib import Path

root = Path('.')

main_activity = root / 'app/src/main/java/io/github/xgl34222220/sinan/MainActivity.kt'
text = main_activity.read_text(encoding='utf-8')
needle = '''                SinanApp(model)\n            }\n        }\n    }\n}\n'''
replacement = '''                SinanApp(model)\n            }\n        }\n    }\n\n    // Legacy XML fragments are no longer used by the Compose shell, but these\n    // compatibility hooks keep their old source files compilable.\n    @Deprecated("Compose navigation is used")\n    fun openPage(fragment: androidx.fragment.app.Fragment) = Unit\n\n    @Deprecated("Compose navigation is used")\n    fun selectSection(itemId: Int) = Unit\n}\n'''
if needle not in text:
    raise SystemExit('MainActivity patch target not found')
main_activity.write_text(text.replace(needle, replacement, 1), encoding='utf-8')

detail = root / 'app/src/main/java/io/github/xgl34222220/sinan/ui/screens/DetailScreens.kt'
text = detail.read_text(encoding='utf-8')
text = text.replace('import androidx.compose.foundation.layout.weight\n', '')
detail.write_text(text, encoding='utf-8')

home = root / 'app/src/main/java/io/github/xgl34222220/sinan/ui/screens/HomeScreen.kt'
text = home.read_text(encoding='utf-8')
needle = '''    val title = if (running) "透明代理已开启" else "透明代理未启动"\n    Box(\n'''
replacement = '''    val title = if (running) "透明代理已开启" else "透明代理未启动"\n    val heroCircleColor = MaterialTheme.colorScheme.primary.copy(alpha = .08f)\n    Box(\n'''
if needle not in text:
    raise SystemExit('HomeScreen color declaration target not found')
text = text.replace(needle, replacement, 1)
needle = '''                drawCircle(\n                    color = MaterialTheme.colorScheme.primary.copy(alpha = .08f),\n                    radius = size.minDimension * .48f,\n'''
replacement = '''                drawCircle(\n                    color = heroCircleColor,\n                    radius = size.minDimension * .48f,\n'''
if needle not in text:
    raise SystemExit('HomeScreen drawCircle target not found')
text = text.replace(needle, replacement, 1)
home.write_text(text, encoding='utf-8')

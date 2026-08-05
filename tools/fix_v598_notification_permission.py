from pathlib import Path

path = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/MainActivity.kt")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "import androidx.activity.result.contract.ActivityResultContracts\n",
    "import androidx.core.app.ActivityCompat\n",
)
text = text.replace(
    '''class MainActivity : ComponentActivity() {
    private val notificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { }

''',
    '''class MainActivity : ComponentActivity() {
''',
)
text = text.replace(
    '''            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
''',
    '''            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                NOTIFICATION_PERMISSION_REQUEST,
            )
''',
)
text = text.replace(
    '''    }
}
''',
    '''    }

    companion object {
        private const val NOTIFICATION_PERMISSION_REQUEST = 5098
    }
}
''',
    1,
)
path.write_text(text, encoding="utf-8")
print("notification permission lint fix applied")

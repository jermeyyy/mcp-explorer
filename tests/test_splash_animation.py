"""Test splash screen animation in isolation."""

import asyncio
from mcp_explorer.ui.screens import SplashScreen
from textual.app import App


class AnimationTestApp(App):
    """Test app to verify splash animation works."""

    def compose(self):
        return [SplashScreen()]

    def on_mount(self) -> None:
        """Auto-exit after a few seconds."""
        self.set_timer(5.0, self.exit)


if __name__ == "__main__":
    app = AnimationTestApp()
    print("Starting animation test - watch for color wave in logo...")
    print("App will auto-close after 5 seconds")
    app.run()
